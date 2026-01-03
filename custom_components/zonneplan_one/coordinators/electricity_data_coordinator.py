import logging
from datetime import timedelta
from http import HTTPStatus

from aiohttp.client_exceptions import ClientResponseError
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.debounce import Debouncer

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

            return electricity if electricity else self.data
