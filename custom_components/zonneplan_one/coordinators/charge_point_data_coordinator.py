from collections.abc import Callable
from datetime import timedelta
from http import HTTPStatus
from typing import Any

import logging
from aiohttp.client_exceptions import ClientResponseError

from homeassistant.core import (
    HassJob,
    HomeAssistant
)
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.event import async_call_later
from homeassistant.exceptions import ConfigEntryAuthFailed

from .zonneplan_data_update_coordinator import ZonneplanDataUpdateCoordinator
from ..api import AsyncConfigEntryAuth
from ..const import DOMAIN
from ..zonneplan_api.types import ZonneplanContract

_LOGGER = logging.getLogger(__name__)


class ChargePointDataUpdateCoordinator(ZonneplanDataUpdateCoordinator):
    """Zonneplan charge point data update coordinator"""

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
            update_interval=timedelta(seconds=60),
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

        self._delayed_fetch_charge_point: Callable[[], None] | None = None

    async def _async_update_data(self) -> dict:
        """Fetch the latest status."""
        try:
            charge_point = await self._async_get_charge_point_data(self.connection_uuid, self.contract.get("uuid"))

            return charge_point["contracts"][0] if charge_point else self.data

        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise e

    async def _async_get_charge_point_data(self, connection_uuid: str, charge_point_uuid: str) -> dict:
        return await self.api.async_get(connection_uuid, "/charge-points/" + charge_point_uuid)

    async def async_update_charge_point_data(self) -> None:
        charge_point = await self._async_get_charge_point_data(self.connection_uuid, self.contract["uuid"])
        if charge_point:
            self.data = charge_point["contracts"][0]
            self.async_update_listeners()

    async def async_start_charge(self) -> None:
        await self.api.async_post(
            self.connection_uuid,
            "/charge-points/" + self.contract["uuid"] + "/actions/start_boost",
        )

        self.data["state"]["processing"] = True
        self.async_update_listeners()

        await self.async_fetch_charge_point_data()

    async def async_stop_charge(self) -> None:
        await self.api.async_post(
            self.connection_uuid,
            "/charge-points/" + self.contract["uuid"] + "/actions/stop_charging",
        )

        self.data["state"]["processing"] = True

        self.async_update_listeners()

        await self.async_fetch_charge_point_data()

    def _processing_charge_point_update(self) -> bool:

        processing = self.data.get("state", {}).get("processing")

        return True if processing else False

    async def async_fetch_charge_point_data(self, _now: Any = None):

        if self._delayed_fetch_charge_point:
            self._delayed_fetch_charge_point()
        self._delayed_fetch_charge_point = None

        if self._processing_charge_point_update():
            # @todo: change to force refetch of this dataCoordinator
            await self.async_update_charge_point_data()

        if self._processing_charge_point_update():
            # Retry in 10 seconds when api didn't respond with an update
            self._delayed_fetch_charge_point = async_call_later(
                self.hass,
                10,
                HassJob(self.async_fetch_charge_point_data, cancel_on_shutdown=True),
            )
