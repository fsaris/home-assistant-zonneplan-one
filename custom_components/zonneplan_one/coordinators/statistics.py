import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, tzinfo
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
from homeassistant.const import UnitOfEnergy, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.util.unit_conversion import EnergyConverter, VolumeConverter

from ..api import AsyncConfigEntryAuth, ZonneplanRateLimitError
from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

_BACKFILL_MAX_RETRIES = 3


@dataclass(frozen=True)
class StatisticChannelConfig:
    key: str
    statistic_id: str
    name: str
    date_key: str
    value_key: str | None
    value_factor: float
    unit_class: str
    unit_of_measurement: str


@dataclass
class StatisticChannelState:
    config: StatisticChannelConfig
    last_time: datetime
    total_sum: float
    last_state_value: float | None
    pending: list[StatisticData] = field(default_factory=list)


class BaseZonneplanStatisticsService(ABC):
    """Base class for statistics services, providing common utilities."""

    hass: HomeAssistant
    zonneplan_api_time_zone: tzinfo
    channel_configs: tuple[StatisticChannelConfig, ...]

    def __init__(
        self,
        hass: HomeAssistant,
    ) -> None:
        self.hass = hass
        self.zonneplan_api_time_zone = dt_util.get_time_zone("Europe/Amsterdam")
        self._refetched_statistics_yesterday: datetime | None = None

    @abstractmethod
    async def _fetch_day_payload(self, day: datetime) -> dict[str, Any] | None:
        """Fetch day statistics payload."""

    def refetch_yesterday_cutoff_time(self) -> time:
        """Return local-time cutoff after which yesterday may be refetched."""
        return time(hour=0, minute=20)

    async def process_payload(self, data: dict[str, Any]) -> None:
        """Import historical gaps and process latest measurements."""
        if await self._refetch_and_process_yesterday(data):
            return

        states = await self._load_current_states()
        start_of_today = dt_util.now(self.zonneplan_api_time_zone).replace(hour=0, minute=0, second=0, microsecond=0)
        backfill_failed = False
        if any(state.last_time < start_of_today for state in states.values()):
            try:
                await self._backfill_history(states, start_of_today, retry_on_max_connections=False)
            except ClientResponseError as err:
                backfill_failed = True
                _LOGGER.warning(
                    "Backfill failed before %s for %s, continuing next run. Error: %s",
                    start_of_today,
                    [config.statistic_id for config in self.channel_configs],
                    err,
                )

        if not backfill_failed:
            measurements = self._extract_measurements(data, "current-day")
            self._ingest_measurements(measurements, states)
        self._flush_pending(states)

    async def _refetch_and_process_yesterday(self, data_today: dict[str, Any]) -> bool:
        """Refetch yesterday once per day when the configured cutoff has passed."""
        zonneplan_now = dt_util.now(self.zonneplan_api_time_zone)
        start_of_today = zonneplan_now.replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_time = self.refetch_yesterday_cutoff_time()
        if zonneplan_now.time() < cutoff_time:
            return False

        if self._refetched_statistics_yesterday and self._refetched_statistics_yesterday >= start_of_today:
            return False

        _LOGGER.info(
            "Refetching yesterday's for %s statistics to ensure data is up to date", [config.key for config in self.channel_configs]
        )
        try:
            if await self._refetch_yesterday(start_of_today - timedelta(days=1), data_today):
                self._refetched_statistics_yesterday = start_of_today
                return True
        except ClientResponseError as err:
            _LOGGER.warning(
                "Refetch of yesterday failed for %s, continuing with regular processing. Error: %s",
                [config.statistic_id for config in self.channel_configs],
                err,
            )

        return False

    async def _refetch_yesterday(self, start_of_day: datetime, data_today: dict[str, Any]) -> bool:
        """Refetch one day from API and re-apply values using recorder baseline stats."""
        stats = await get_instance(self.hass).async_add_executor_job(
            statistics_during_period,
            self.hass,
            start_of_day,
            None,
            {config.statistic_id for config in self.channel_configs},
            "hour",
            None,
            {"sum", "state"},
        )

        states: dict[str, StatisticChannelState] = {}
        for config in self.channel_configs:
            rows = stats.get(config.statistic_id)
            if not rows:
                _LOGGER.warning("No stats found for %s on %s", config.statistic_id, start_of_day)
                return False

            baseline = rows[0]
            if baseline is None:
                _LOGGER.warning("Empty baseline stat for %s on %s", config.statistic_id, start_of_day)
                return False

            baseline_start = baseline.get("start")
            last_time = (
                datetime.fromtimestamp(baseline_start, tz=dt_util.UTC).astimezone(self.zonneplan_api_time_zone)
                if baseline_start is not None
                else start_of_day.astimezone(self.zonneplan_api_time_zone)
            )
            states[config.key] = StatisticChannelState(
                config=config,
                last_time=last_time,
                total_sum=float(baseline.get("sum", 0.0)),
                last_state_value=float(baseline.get("state", 0.0)),
            )

        yesterday_payload = await self._fetch_day_payload(start_of_day)
        measurements_yesterday = self._extract_measurements(yesterday_payload or {}, "refetch-yesterday")
        measurements_today = self._extract_measurements(data_today or {}, "current-day")
        self._ingest_measurements(measurements_yesterday, states)
        self._ingest_measurements(measurements_today, states)

        self._flush_pending(states)
        return True

    async def _load_current_states(self) -> dict[str, StatisticChannelState]:
        states: dict[str, StatisticChannelState] = {}

        for config in self.channel_configs:
            last_stat = await self._get_last_statistic(config.statistic_id)
            if last_stat:
                last_time = datetime.fromtimestamp(last_stat["start"], tz=dt_util.UTC).astimezone(self.zonneplan_api_time_zone)
                total_sum = float(last_stat.get("sum", 0.0))
                last_state_value = float(last_stat.get("state", 0.0))
                _LOGGER.debug("Last stat for %s (%s): %s", config.statistic_id, last_time, last_stat)
            else:
                last_time = self._fallback_last_stats_datetime()
                total_sum = 0.0
                last_state_value = None

            states[config.key] = StatisticChannelState(
                config=config,
                last_time=last_time,
                total_sum=total_sum,
                last_state_value=last_state_value,
            )

        return states

    def _fallback_last_stats_datetime(self) -> datetime:
        """Fallback datetime for last statistic to 1ste of the month."""
        now = dt_util.now(self.zonneplan_api_time_zone)
        return datetime(now.year, now.month, 1, tzinfo=self.zonneplan_api_time_zone)

    async def _backfill_history(
        self, states: dict[str, StatisticChannelState], start_of_today: datetime, *, retry_on_max_connections: bool
    ) -> None:
        current_day = min(state.last_time for state in states.values())
        _LOGGER.info(
            "Last stat for %s is outdated, fetching historical data since %s",
            [config.statistic_id for config in self.channel_configs],
            current_day,
        )

        consecutive_failures = 0
        while current_day < start_of_today:
            try:
                day_payload = await self._fetch_day_payload(current_day)
            except ZonneplanRateLimitError as err:
                consecutive_failures += 1
                if not retry_on_max_connections:
                    raise
                if consecutive_failures >= _BACKFILL_MAX_RETRIES:
                    _LOGGER.warning(
                        "Rate limit hit %s consecutive times at %s, giving up backfill",
                        consecutive_failures,
                        current_day,
                    )
                    raise
                wait_seconds = (err.retry_after + 20) if err.retry_after is not None else 60
                wait_seconds *= consecutive_failures
                _LOGGER.warning(
                    "Rate limited during backfill at %s (attempt %s/%s), persisted current stats and waiting %s seconds before resume",
                    current_day,
                    consecutive_failures,
                    _BACKFILL_MAX_RETRIES,
                    wait_seconds,
                )
                await asyncio.sleep(wait_seconds)
                continue

            consecutive_failures = 0
            if day_payload:
                measurements = self._extract_measurements(day_payload, "backfill")
                self._ingest_measurements(measurements, states)
                self._flush_pending(states)
            current_day += timedelta(days=1)

    def _extract_measurements(self, payload: dict[str, Any], context: str) -> list[dict[str, Any]]:
        if not payload:
            return []

        groups = payload.get("measurement_groups", [])

        measurements = None
        for group in groups:
            if group.get("type", "") == "hours":
                measurements = group.get("measurements")

        if not measurements:
            for group in groups:
                if group.get("type", "") == "minutes":
                    measurements = group.get("measurements")

        _LOGGER.debug("Measurements for %s: %s", context, measurements)
        if not isinstance(measurements, list):
            _LOGGER.warning("No hourly measurements found for %s", context)
            return []

        return measurements

    def _ingest_measurements(
        self,
        measurements: list[dict[str, Any]],
        states: dict[str, StatisticChannelState],
    ) -> None:

        measurements_per_hour = self.measurement_by_hour(measurements)

        for entry_time, values in measurements_per_hour.items():
            for config in self.channel_configs:
                if config.key not in values:
                    continue

                value = values[config.key]

                state = states[config.key]

                if entry_time > state.last_time:
                    state.total_sum += value
                    state.pending.append(StatisticData(start=entry_time, state=value, sum=state.total_sum))
                    state.last_time = entry_time
                    state.last_state_value = value
                elif entry_time == state.last_time and state.last_state_value is not None:
                    state.total_sum += value - state.last_state_value
                    state.pending.append(StatisticData(start=entry_time, state=value, sum=state.total_sum))
                    state.last_state_value = value

    def measurement_by_hour(self, measurements: list[dict[str, Any]]) -> dict[datetime, dict[str, float]]:
        measurements_per_hour: dict[datetime, dict[str, float]] = {}
        last_entry_time = None
        for entry in measurements:
            for config in self.channel_configs:
                entry_time = dt_util.parse_datetime(entry.get(config.date_key)).replace(minute=0, second=0, microsecond=0)
                if (last_entry_time and entry_time < last_entry_time) or entry_time > datetime.now(tz=self.zonneplan_api_time_zone):
                    _LOGGER.debug(
                        "Skipping %s entry for %s",
                        config.key,
                        entry_time.astimezone(self.zonneplan_api_time_zone).strftime("%Y-%m-%d %H:%M"),
                    )
                    continue
                last_entry_time = entry_time

                if config.value_key:
                    raw_value = entry.get("values").get(config.value_key)
                    if not isinstance(raw_value, (float, int)):
                        _LOGGER.warning("Skipping %s value for entry %s", config.value_key, entry)
                        continue
                else:
                    raw_value = entry.get("value")
                    if not isinstance(raw_value, (float, int)):
                        _LOGGER.warning("Skipping value for entry %s", entry)
                        continue

                if entry_time not in measurements_per_hour:
                    measurements_per_hour[entry_time] = {}
                if config.key not in measurements_per_hour[entry_time]:
                    measurements_per_hour[entry_time][config.key] = 0

                measurements_per_hour[entry_time][config.key] += float(raw_value) * config.value_factor
        return measurements_per_hour

    def _flush_pending(self, states: dict[str, StatisticChannelState]) -> None:
        for state in states.values():
            if not state.pending:
                continue

            metadata = StatisticMetaData(
                mean_type=StatisticMeanType.NONE,
                has_sum=True,
                name=state.config.name,
                source=DOMAIN,
                statistic_id=state.config.statistic_id,
                unit_class=state.config.unit_class,
                unit_of_measurement=state.config.unit_of_measurement,
            )
            async_add_external_statistics(self.hass, metadata, state.pending)
            state.pending = []

        _LOGGER.info(
            "Finished processing stats until for %s",
            {
                key: {"value": state.total_sum, "time": state.last_time.astimezone(self.zonneplan_api_time_zone).strftime("%Y-%m-%d %H:%M")}
                for key, state in states.items()
            },
        )

    async def _get_last_statistic(self, statistic_id: str) -> StatisticsRow | None:
        last_stats = await get_instance(self.hass).async_add_executor_job(
            get_last_statistics,
            self.hass,
            1,
            statistic_id,
            True,
            {"sum", "state"},
        )
        if last_stats and statistic_id in last_stats and last_stats[statistic_id]:
            return last_stats[statistic_id][0]
        return None

    async def async_backfill_from(self, start_date: datetime) -> None:
        """
        Backfill statistics from start_date up to and including today.

        Queries the recorder for the cumulative sum baseline just before start_date,
        then re-fetches and re-ingests all hourly data from start_date until now.
        """
        # Normalize to midnight of the requested date in the API timezone
        start_of_day = start_date.astimezone(self.zonneplan_api_time_zone).replace(hour=0, minute=0, second=0, microsecond=0)
        start_of_today = dt_util.now(self.zonneplan_api_time_zone).replace(hour=0, minute=0, second=0, microsecond=0)

        _LOGGER.info(
            "Starting manual backfill for %s from %s to %s",
            [config.statistic_id for config in self.channel_configs],
            start_of_day,
            start_of_today,
        )

        baseline_window_start = start_of_day - timedelta(days=1)
        recorder_stats = await get_instance(self.hass).async_add_executor_job(
            statistics_during_period,
            self.hass,
            baseline_window_start,
            start_of_day,
            {config.statistic_id for config in self.channel_configs},
            "hour",
            None,
            {"sum", "state"},
        )

        states: dict[str, StatisticChannelState] = {}
        for config in self.channel_configs:
            rows = recorder_stats.get(config.statistic_id)
            if rows:
                baseline = rows[-1]  # most recent row before start_of_day
                total_sum = float(baseline.get("sum") or 0.0)
                raw_state = baseline.get("state")
                last_state_value: float | None = float(raw_state) if raw_state is not None else None
            else:
                _LOGGER.info(
                    "No baseline stat found for %s before %s, starting from zero",
                    config.statistic_id,
                    start_of_day,
                )
                total_sum = 0.0
                last_state_value = None

            # Set last_time to one hour before start_of_day so that the 00:00 entry
            # of start_of_day qualifies as entry_time > last_time in _ingest_measurements.
            states[config.key] = StatisticChannelState(
                config=config,
                last_time=start_of_day - timedelta(hours=1),
                total_sum=total_sum,
                last_state_value=last_state_value,
            )

        await self._backfill_history(states, start_of_today, retry_on_max_connections=True)

        today_payload = await self._fetch_day_payload(start_of_today)
        if today_payload:
            measurements = self._extract_measurements(today_payload, "backfill-today")
            self._ingest_measurements(measurements, states)
            self._flush_pending(states)

        _LOGGER.info(
            "Manual backfill completed for %s",
            [config.statistic_id for config in self.channel_configs],
        )

    def _zonneplan_api_date_param(self, day: datetime) -> str:
        return day.astimezone(self.zonneplan_api_time_zone).strftime("%Y-%m-%d")


class ElectricityStatisticsService(BaseZonneplanStatisticsService):
    """Handles external statistics ingestion for electricity (P1)."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: AsyncConfigEntryAuth,
        connection_uuid: str,
        delivered_id: str,
        produced_id: str,
    ) -> None:
        super().__init__(
            hass=hass,
        )

        self.api = api
        self.connection_uuid = connection_uuid
        self.channel_configs: tuple[StatisticChannelConfig, ...] = (
            StatisticChannelConfig(
                key="delivered",
                statistic_id=delivered_id,
                name="Stroom opgenomen uit het net",
                date_key="date",
                value_key="d",
                value_factor=0.001,
                unit_class=EnergyConverter.UNIT_CLASS,
                unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            ),
            StatisticChannelConfig(
                key="produced",
                statistic_id=produced_id,
                name="Stroom teruggeleverd aan het net",
                date_key="date",
                value_key="p",
                value_factor=-0.001,
                unit_class=EnergyConverter.UNIT_CLASS,
                unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            ),
        )

    async def _fetch_day_payload(self, day: datetime) -> dict[str, Any] | None:
        date_str = self._zonneplan_api_date_param(day)
        day_payload = await self.api.async_get(self.connection_uuid, f"/electricity-delivered/charts/hours?date={date_str}")
        _LOGGER.debug("Fetched Electricity day payload for %s: has_data=%s", date_str, bool(day_payload))
        return day_payload


class GasStatisticsService(BaseZonneplanStatisticsService):
    """Handles external statistics ingestion for Gas (P1)."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: AsyncConfigEntryAuth,
        connection_uuid: str,
        gas_id: str,
    ) -> None:
        super().__init__(
            hass=hass,
        )

        self.api = api
        self.connection_uuid = connection_uuid
        self.channel_configs: tuple[StatisticChannelConfig, ...] = (
            StatisticChannelConfig(
                key="gas",
                statistic_id=gas_id,
                name="Gas verbruik",
                value_key=None,
                date_key="measured_at",
                value_factor=0.001,
                unit_class=VolumeConverter.UNIT_CLASS,
                unit_of_measurement=UnitOfVolume.CUBIC_METERS,
            ),
        )

    async def _fetch_day_payload(self, day: datetime) -> dict[str, Any] | None:
        date_str = self._zonneplan_api_date_param(day)
        day_payload = await self.api.async_get(self.connection_uuid, f"/gas/charts/hours?date={date_str}")
        _LOGGER.debug("Fetched Gas day payload for %s: has_data=%s", date_str, bool(day_payload))
        return day_payload


class PvStatisticsService(BaseZonneplanStatisticsService):
    """Handles external statistics ingestion for PV."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: AsyncConfigEntryAuth,
        connection_uuid: str,
        gas_id: str,
    ) -> None:
        super().__init__(
            hass=hass,
        )

        self.api = api
        self.connection_uuid = connection_uuid
        self.channel_configs: tuple[StatisticChannelConfig, ...] = (
            StatisticChannelConfig(
                key="pv",
                statistic_id=gas_id,
                name="Zonne-energieproductie",
                value_key=None,
                date_key="measured_at",
                value_factor=0.001,
                unit_class=EnergyConverter.UNIT_CLASS,
                unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            ),
        )

    async def _fetch_day_payload(self, day: datetime) -> dict[str, Any] | None:
        date_str = self._zonneplan_api_date_param(day)
        day_payload = await self.api.async_get(self.connection_uuid, f"/pv_installation/charts/minutes?date={date_str}")
        _LOGGER.debug("Fetched PV day payload for %s: has_data=%s", date_str, bool(day_payload))
        return day_payload
