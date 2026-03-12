import logging
import zoneinfo
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Any

import homeassistant.util.dt as dt_util
from aiohttp.client_exceptions import ClientResponseError
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMeanType,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    StatisticsRow,
    async_add_external_statistics,
    get_last_statistics,
    statistics_during_period,
)
from homeassistant.const import (
    UnitOfEnergy,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.debounce import Debouncer
from homeassistant.util.unit_conversion import EnergyConverter

from ..api import AsyncConfigEntryAuth
from ..const import DOMAIN
from ..zonneplan_api.types import ZonneplanContract
from .zonneplan_data_update_coordinator import ZonneplanDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class ElectricityDataUpdateCoordinator(ZonneplanDataUpdateCoordinator):
    """Zonneplan p1 electricity data update coordinator."""

    hass: HomeAssistant
    api: AsyncConfigEntryAuth
    address_uuid: str
    connection_uuid: str
    contracts: list[ZonneplanContract]
    refetched_statistics_yesterday: datetime | None
    _zonneplan_api_time_zone: zoneinfo.ZoneInfo

    def __init__(
        self,
        hass: HomeAssistant,
        api: AsyncConfigEntryAuth,
        address_uuid: str,
        connection_uuid: str,
        contracts: list[ZonneplanContract],
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=300),
            request_refresh_debouncer=Debouncer(hass, _LOGGER, cooldown=60, immediate=False),
        )

        self.api: AsyncConfigEntryAuth = api
        self.address_uuid = address_uuid
        self.connection_uuid = connection_uuid
        self.contracts = contracts
        self.refetched_statistics_yesterday = None
        self._zonneplan_api_time_zone = dt_util.get_time_zone("Europe/Amsterdam")

    async def _async_update_data(self) -> dict:
        """Fetch the latest status."""
        try:
            electricity = await self.api.async_get(self.connection_uuid, "/electricity-delivered")

        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise
        else:
            _LOGGER.debug("Update electricity data: %s", electricity)
            if electricity:
                await self._update_statistics(electricity)

            zonneplan_now = dt_util.now(self._zonneplan_api_time_zone)
            zonneplan_now_midnight = zonneplan_now.replace(hour=0, minute=0, second=0, microsecond=0)
            if zonneplan_now.time() >= zonneplan_now.replace(hour=0, minute=20, second=0, microsecond=0).time() and (
                not self.refetched_statistics_yesterday or self.refetched_statistics_yesterday < zonneplan_now_midnight
            ):
                _LOGGER.info("Refetching yesterday's statistics to ensure data is up to date")
                # @todo: today should also be updated after this to assure the `sum` is correct
                if await self._fetch_and_update_stats_day(zonneplan_now_midnight - timedelta(days=1)):
                    self.refetched_statistics_yesterday = zonneplan_now_midnight

            return electricity or self.data

    @property
    def electricity_delivered_id(self) -> str:
        return f"{DOMAIN}:electricity_delivered_{self.connection_uuid.replace('-', '_')}"

    @property
    def electricity_produced_id(self) -> str:
        return f"{DOMAIN}:electricity_produced_{self.connection_uuid.replace('-', '_')}"

    async def _update_statistics(self, data: dict) -> None:
        """Log external stats."""
        _LOGGER.debug("Process stats for %s", [self.electricity_delivered_id, self.electricity_produced_id])
        last_stats_delivered = await self._get_last_statistic(self.electricity_delivered_id)
        last_stats_produced = await self._get_last_statistic(self.electricity_produced_id)

        sum_delivered = 0
        sum_produced = 0
        last_time_delivery = last_time_production = (
            dt_util.parse_datetime(data.get("contracts")[0].get("meta").get("electricity_first_measured_at"))
            if data.get("contracts")[0].get("meta").get("electricity_first_measured_at")
            else datetime(datetime.now().year - 1, 1, 1, tzinfo=self._zonneplan_api_time_zone)
        )
        start_of_today = dt_util.now(self._zonneplan_api_time_zone).replace(hour=0, minute=0, second=0, microsecond=0)

        if last_stats_delivered:
            last_time_delivery = datetime.fromtimestamp(last_stats_delivered["start"], tz=dt_util.UTC).astimezone(
                self._zonneplan_api_time_zone
            )
            sum_delivered = last_stats_delivered["sum"]
            _LOGGER.debug("Last stat for %s (%s): %s", self.electricity_delivered_id, last_time_delivery, last_stats_delivered)

        if last_stats_produced:
            last_time_production = datetime.fromtimestamp(last_stats_produced["start"], tz=dt_util.UTC).astimezone(
                self._zonneplan_api_time_zone
            )
            sum_produced = last_stats_produced["sum"]
            _LOGGER.debug("Last stat for %s (%s): %s", self.electricity_produced_id, last_time_production, last_stats_produced)

        _LOGGER.debug("Import older stats? %s < %s or %s < %s", last_time_delivery, start_of_today, last_time_production, start_of_today)
        if last_time_delivery < start_of_today or last_time_production < start_of_today:
            # When not equal we start counting from 0 to prevent incorrect sums, when equal we can continue counting from the last sum
            if last_time_delivery != last_time_production:
                sum_delivered = sum_produced = 0
            try:
                sum_delivered, sum_produced, last_time = await self.import_older_stats(
                    start_of_today,
                    min(last_time_delivery, last_time_production),
                    last_stats_delivered,
                    sum_delivered,
                    last_stats_produced,
                    sum_produced,
                )
                last_time_delivery = last_time_production = last_time
            except ClientResponseError as e:
                _LOGGER.warning("Failed to fetch historical data: %s", e)
                _LOGGER.debug("Proceed next interval")
                return

        measurements = data.get("measurement_groups", [])[1].get("measurements", [])
        await self._update_stats(
            measurements,
            last_stats_delivered,
            sum_delivered,
            last_time_delivery,
            last_stats_produced,
            sum_produced,
            last_time_production,
        )

    async def import_older_stats(
        self,
        start_of_today: datetime,
        last_time: datetime,
        last_stats_delivered: StatisticData | None,
        sum_delivered: float,
        last_stats_produced: StatisticData | None,
        sum_produced: float,
    ) -> tuple[float, float, datetime]:
        _LOGGER.info(
            "Last stat for %s is outdated, fetching historical data since %s",
            [self.electricity_delivered_id, self.electricity_produced_id],
            last_time,
        )
        while last_time < start_of_today:
            sum_delivered, sum_produced = await self._update_stats_for_day(
                last_stats_delivered,
                last_stats_produced,
                last_time,
                sum_delivered,
                sum_produced,
            )

            last_time += timedelta(days=1)
        return sum_delivered, sum_produced, last_time

    async def _update_stats_for_day(
        self,
        last_stats_delivered: StatisticsRow | None,
        last_stats_produced: StatisticsRow | None,
        last_time: datetime,
        sum_delivered: float,
        sum_produced: float,
    ) -> Any:
        # The API expects the date in local time, so we need to adjust for the timezone offset
        date_str = (last_time + last_time.utcoffset()).strftime("%Y-%m-%d")

        electricity = await self.api.async_get(self.connection_uuid, f"/electricity-delivered/charts/hours?date={date_str}")
        if electricity:
            measurements = electricity.get("measurement_groups", [])[0].get("measurements", [])
            _LOGGER.info(
                "Found %s measurements for %s (%s), current sums: %s/%s",
                len(measurements),
                date_str,
                last_time,
                sum_delivered,
                sum_produced,
            )
            sum_delivered, sum_produced = await self._update_stats(
                measurements,
                last_stats_delivered,
                sum_delivered,
                last_time,
                last_stats_produced,
                sum_produced,
                last_time,
            )
        return sum_delivered, sum_produced

    async def _update_stats(
        self,
        measurements: dict,
        last_stats_delivered: StatisticsRow | None,
        sum_delivered: float,
        last_time_delivered: datetime,
        last_stat_production: StatisticsRow | None,
        sum_produced: float,
        last_time_production: datetime,
    ) -> tuple[float, float]:
        statistics_delivery = []
        statistics_production = []
        entry_time = None
        for entry in measurements:
            entry_time = dt_util.parse_datetime(entry["date"])
            value_delivered = entry["values"]["d"] * 0.001
            value_produced = entry["values"]["p"] * -0.001

            if not last_stats_delivered or entry_time > last_time_delivered:
                sum_delivered += value_delivered
                _LOGGER.debug(
                    "Processing entry for %s: time=%s, last_time=%s, state=%s, sum=%s",
                    self.electricity_delivered_id,
                    entry_time,
                    last_time_delivered,
                    value_delivered,
                    sum_delivered,
                )
                statistics_delivery.append(StatisticData(start=entry_time, state=value_delivered, sum=sum_delivered))
            elif entry_time == last_time_delivered:
                sum_delivered += value_delivered - last_stats_delivered["state"]
                _LOGGER.debug(
                    "Updating last stat for %s: time=%s, state=%s, sum=%s, last_stat=%s",
                    self.electricity_delivered_id,
                    entry_time,
                    value_delivered,
                    sum_delivered,
                    last_stats_delivered,
                )
                statistics_delivery.append(StatisticData(start=entry_time, state=value_delivered, sum=sum_delivered))

            if not last_stat_production or entry_time > last_time_production:
                sum_produced += value_produced
                _LOGGER.debug(
                    "Processing entry for %s: time=%s, last_time=%s, state=%s, sum=%s",
                    self.electricity_produced_id,
                    entry_time,
                    last_time_production,
                    value_produced,
                    sum_produced,
                )
                statistics_production.append(StatisticData(start=entry_time, state=value_produced, sum=sum_produced))
            elif entry_time == last_time_production:
                sum_produced += value_produced - last_stat_production["state"]
                _LOGGER.debug(
                    "Updating last stat for %s: time=%s, state=%s, sum=%s, last_stat=%s",
                    self.electricity_produced_id,
                    entry_time,
                    value_produced,
                    sum_produced,
                    last_stat_production,
                )
                statistics_production.append(StatisticData(start=entry_time, state=value_produced, sum=sum_produced))

        if statistics_delivery:
            metadata = StatisticMetaData(
                mean_type=StatisticMeanType.NONE,
                has_sum=True,
                name="Stroom opgenomen uit het net",
                source=DOMAIN,
                statistic_id=self.electricity_delivered_id,
                unit_class=EnergyConverter.UNIT_CLASS,
                unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            )
            async_add_external_statistics(self.hass, metadata, statistics_delivery)

        if statistics_production:
            metadata = StatisticMetaData(
                mean_type=StatisticMeanType.NONE,
                has_sum=True,
                name="Stroom teruggeleverd aan het net",
                source=DOMAIN,
                statistic_id=self.electricity_produced_id,
                unit_class=EnergyConverter.UNIT_CLASS,
                unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            )
            async_add_external_statistics(self.hass, metadata, statistics_production)

        _LOGGER.info("Finished processing stats, sum delivered: %s, sum produced: %s, at: %s", sum_delivered, sum_produced, entry_time)
        return sum_delivered, sum_produced

    async def _fetch_and_update_stats_day(self, start_of_day: datetime) -> bool:

        stat = await get_instance(self.hass).async_add_executor_job(
            statistics_during_period,
            self.hass,
            start_of_day,
            None,
            {self.electricity_delivered_id, self.electricity_produced_id},
            "hour",
            None,
            {"sum", "state"},
        )

        _LOGGER.debug("Fetched stats for %s: %s", start_of_day, stat)

        if self.electricity_produced_id not in stat or self.electricity_delivered_id not in stat:
            _LOGGER.warning("No stats found for %s, cannot update yet", start_of_day)
            return False

        stat_delivered = stat[self.electricity_delivered_id][0] or None
        stat_produced = stat[self.electricity_produced_id][0] or None

        try:
            await self._update_stats_for_day(
                stat_delivered,
                stat_produced,
                start_of_day,
                stat_delivered.get("sum", 0),
                stat_produced.get("sum", 0),
            )
        except ClientResponseError as e:
            _LOGGER.warning("Failed to fetch historical data for %s (retry next run): %s", start_of_day, e)
            return False
        else:
            return True

    async def _get_last_statistic(self, statistic_id: str) -> StatisticsRow | None:
        """Get the last imported statistic."""
        last_stats = await get_instance(self.hass).async_add_executor_job(
            get_last_statistics, self.hass, 1, statistic_id, True, {"sum", "state"}
        )

        if last_stats and statistic_id in last_stats:
            return last_stats[statistic_id][0]
        return None
