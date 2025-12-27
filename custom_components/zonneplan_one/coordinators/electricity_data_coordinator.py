from datetime import timedelta
from http import HTTPStatus

import logging
from aiohttp.client_exceptions import ClientResponseError

from homeassistant.core import (
    HomeAssistant
)
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from .zonneplan_data_update_coordinator import ZonneplanDataUpdateCoordinator
from ..api import AsyncConfigEntryAuth
from ..const import DOMAIN
from ..zonneplan_api.types import ZonneplanContract

_LOGGER = logging.getLogger(__name__)


class ElectricityDataUpdateCoordinator(ZonneplanDataUpdateCoordinator):
    """Zonneplan p1 electricity data update coordinator"""

    hass: HomeAssistant
    api: AsyncConfigEntryAuth
    connection_uuid: str
    contracts: list[ZonneplanContract]

    def __init__(
            self,
            hass: HomeAssistant,
            api: AsyncConfigEntryAuth,
            connection_uuid: str,
            contracts: list[ZonneplanContract]
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=300),
            request_refresh_debouncer=Debouncer(
                hass,
                _LOGGER,
                cooldown=60,
                immediate=False
            )
        )

        self.api: AsyncConfigEntryAuth = api
        self.connection_uuid = connection_uuid
        self.contracts = contracts

    async def _async_update_data(self) -> dict:
        """Fetch the latest status."""
        try:

            electricity = await self.api.async_get(self.connection_uuid, "/electricity-delivered")
            if not electricity:
                raise UpdateFailed(retry_after=60)

            return electricity

        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise e
