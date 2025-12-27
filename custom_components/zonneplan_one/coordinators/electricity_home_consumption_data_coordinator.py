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


class ElectricityHomeConsumptionDataUpdateCoordinator(ZonneplanDataUpdateCoordinator):
    """Zonneplan electricity (for install with battery) data update coordinator"""

    hass: HomeAssistant
    api: AsyncConfigEntryAuth
    address_uuid: str
    connection_uuid: str
    contract: ZonneplanContract

    def __init__(
            self,
            hass: HomeAssistant,
            api: AsyncConfigEntryAuth,
            address_uuid: str,
            connection_uuid: str,
            contract: ZonneplanContract,
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
        self.address_uuid = address_uuid
        self.connection_uuid = connection_uuid
        self.contract = contract


    async def _async_update_data(self) -> dict:
        """Fetch the latest status."""
        try:
            electricity_home_consumption = await self.api.async_get(self.connection_uuid, "/electricity-home-consumption")
            if not electricity_home_consumption:
                raise UpdateFailed(retry_after=60)

            return electricity_home_consumption

        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise e
