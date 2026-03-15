import logging
import zoneinfo
from datetime import datetime, timedelta
from http import HTTPStatus

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
        self._statistics_service = ElectricityStatisticsService(
            hass=self.hass,
            api=self.api,
            connection_uuid=self.connection_uuid,
            delivered_id=self.electricity_delivered_id,
            produced_id=self.electricity_produced_id,
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
                _LOGGER.debug("Process stats for %s", [self.electricity_delivered_id, self.electricity_produced_id])
                await self._statistics_service.process_payload(electricity)

            return electricity or self.data

    @property
    def electricity_delivered_id(self) -> str:
        return f"{DOMAIN}:electricity_delivered_{self.connection_uuid.replace('-', '_')}"

    @property
    def electricity_produced_id(self) -> str:
        return f"{DOMAIN}:electricity_produced_{self.connection_uuid.replace('-', '_')}"

    async def async_backfill_statistics(self, start_date: datetime) -> None:
        """Backfill statistics from start_date until now."""
        await self._statistics_service.async_backfill_from(start_date)
