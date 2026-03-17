import logging
from datetime import datetime, timedelta
from http import HTTPStatus

from aiohttp.client_exceptions import ClientResponseError
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.debounce import Debouncer

from ..api import AsyncConfigEntryAuth
from ..const import DOMAIN
from ..zonneplan_api.types import ZonneplanContract
from .statistics import PvStatisticsService
from .zonneplan_data_update_coordinator import ZonneplanDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class PvDataUpdateCoordinator(ZonneplanDataUpdateCoordinator):
    """Zonneplan pv install data update coordinator."""

    hass: HomeAssistant
    api: AsyncConfigEntryAuth
    connection_uuid: str
    address_uuid: str
    contracts: list[ZonneplanContract]
    _statistics_service: PvStatisticsService

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

        self._statistics_service = PvStatisticsService(
            hass=hass,
            api=self.api,
            connection_uuid=self.connection_uuid,
            gas_id=self.statistics_id,
        )

    async def _async_update_data(self) -> dict:
        """Fetch the latest status."""
        try:
            pv_data = await self.api.async_get(self.connection_uuid, "/pv-installation")

        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e

            raise
        else:
            _LOGGER.debug("PV data: %s", pv_data)
            if pv_data:
                await self._statistics_service.process_payload(pv_data)

            return pv_data or self.data

    @property
    def statistics_id(self) -> str:
        return f"{DOMAIN}:pv_{self.connection_uuid.replace('-', '_')}"

    async def async_backfill_statistics(self, start_date: datetime) -> None:
        """Backfill statistics from start_date until now."""
        await self._statistics_service.async_backfill_from(start_date)
