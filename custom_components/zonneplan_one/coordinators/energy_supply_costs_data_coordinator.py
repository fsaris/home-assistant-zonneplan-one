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
from .statistics import EnergySupplyCostsStatisticsService
from .zonneplan_data_update_coordinator import ZonneplanDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class EnergySupplyCostsDataUpdateCoordinator(ZonneplanDataUpdateCoordinator):
    """
    Zonneplan energy supply costs data update coordinator.

    Unlike the other coordinators this one is address scoped instead of connection
    scoped, and it asks for a single explicit day (today in the Zonneplan API time
    zone). These are the battery-filtered costs the app shows on its daily overview;
    the `/electricity-home-consumption` payload only carries them per month/year.

    The sensors only show the running value of today. The last update of a day comes
    in after midnight, so the history of these costs is kept as external statistics.
    """

    hass: HomeAssistant
    api: AsyncConfigEntryAuth
    contract: ZonneplanContract
    address_id: str
    address_uuid: str
    organization_uuid: str
    _statistics_service: EnergySupplyCostsStatisticsService

    def __init__(
        self,
        hass: HomeAssistant,
        api: AsyncConfigEntryAuth,
        address_id: str,
        address_uud: str,
        connection_uuid: str,
        organization_uuid: str,
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
        self.address_id = address_id
        self.address_uuid = address_uud
        self.connection_uuid = connection_uuid
        self.organization_uuid = organization_uuid
        self._statistics_service = EnergySupplyCostsStatisticsService(
            hass=self.hass,
            api=self.api,
            organization_uuid=self.organization_uuid,
            address_id=self.address_id,
            connection_uuid=self.connection_uuid,
        )

    async def _async_update_data(self) -> dict:
        """Fetch the latest status."""
        try:
            costs = await self._statistics_service.async_fetch_today()

        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise
        else:
            _LOGGER.debug("Energy supply costs data: %s", costs)

            if costs:
                await self._statistics_service.process_payload(costs)

            return costs or self.data

    async def async_backfill_statistics(self, start_date: datetime) -> None:
        """Backfill statistics from start_date until now."""
        await self._statistics_service.async_backfill_from(start_date)
