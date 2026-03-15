import logging
import zoneinfo
from datetime import datetime, timedelta
from http import HTTPStatus

import homeassistant.util.dt as dt_util
from aiohttp.client_exceptions import ClientResponseError
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.debounce import Debouncer

from ..api import AsyncConfigEntryAuth
from ..const import DOMAIN
from ..zonneplan_api.types import ZonneplanContract
from .statistics import ElectricityStatisticsService
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
    _statistics_service: ElectricityStatisticsService

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
        self._statistics_service = ElectricityStatisticsService(
            hass=self.hass,
            api=self.api,
            connection_uuid=self.connection_uuid,
            zonneplan_api_time_zone=self._zonneplan_api_time_zone,
            delivered_id=self.electricity_delivered_id,
            produced_id=self.electricity_produced_id,
            first_measured_at=self.first_measured_at,
        )

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
                zonneplan_now = dt_util.now(self._zonneplan_api_time_zone)
                zonneplan_now_midnight = zonneplan_now.replace(hour=0, minute=0, second=0, microsecond=0)
                processed_today = False
                if zonneplan_now.time() >= zonneplan_now.replace(hour=0, minute=20, second=0, microsecond=0).time() and (
                    not self.refetched_statistics_yesterday or self.refetched_statistics_yesterday < zonneplan_now_midnight
                ):
                    _LOGGER.info("Refetching yesterday's statistics to ensure data is up to date")
                    if await self._statistics_service.refetch_yesterday(zonneplan_now_midnight - timedelta(days=1), electricity):
                        processed_today = True
                        self.refetched_statistics_yesterday = zonneplan_now_midnight

                if not processed_today:
                    _LOGGER.debug("Process stats for %s", [self.electricity_delivered_id, self.electricity_produced_id])
                    await self._statistics_service.process_payload(electricity)

            return electricity or self.data

    @property
    def electricity_delivered_id(self) -> str:
        return f"{DOMAIN}:electricity_delivered_{self.connection_uuid.replace('-', '_')}"

    @property
    def electricity_produced_id(self) -> str:
        return f"{DOMAIN}:electricity_produced_{self.connection_uuid.replace('-', '_')}"

    @property
    def first_measured_at(self) -> datetime | None:
        first_contract = self.contracts[0] if self.contracts else {}
        first_measured_at = (first_contract.get("meta") or {}).get("electricity_first_measured_at")
        parsed = dt_util.parse_datetime(first_measured_at) if first_measured_at else None
        if parsed:
            parsed_with_tz = parsed if parsed.tzinfo else parsed.replace(tzinfo=self._zonneplan_api_time_zone)
            return parsed_with_tz.astimezone(self._zonneplan_api_time_zone)

        return None
