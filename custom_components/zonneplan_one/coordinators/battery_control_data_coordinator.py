from datetime import timedelta
from http import HTTPStatus

import logging
from aiohttp.client_exceptions import ClientResponseError

from homeassistant.core import (
    HomeAssistant
)
from homeassistant.helpers.debounce import Debouncer
from homeassistant.exceptions import ConfigEntryAuthFailed

from ..api import AsyncConfigEntryAuth
from ..const import DOMAIN
from .zonneplan_data_update_coordinator import ZonneplanDataUpdateCoordinator
from ..zonneplan_api.types import ZonneplanContract

_LOGGER = logging.getLogger(__name__)


class BatteryControlDataUpdateCoordinator(ZonneplanDataUpdateCoordinator):
    """Zonneplan battery control data update coordinator"""

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

    async def _async_update_data(self) -> dict:
        """Fetch the latest status."""
        try:

            data = self.data or {}

            battery_control_mode = await self.api.async_get_battery_control_mode(self.contract["uuid"])
            if battery_control_mode:
                data["battery_control_mode"] = battery_control_mode

            battery_home_optimization = await self.api.async_get_battery_home_optimization(self.contract["uuid"])
            if battery_home_optimization:
                data["battery_home_optimization"] = battery_home_optimization

            _LOGGER.debug("Update battery control data: %s", data)

            return data

        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise e

    async def async_enable_self_consumption(self) -> None:
        await self.api.async_post(
            self.connection_uuid,
            "/home-battery-installation/" + self.contract["uuid"] + "/actions/enable_self_consumption",
        )

        if self.is_mode_enabled("home_optimization"):
            await self.api.async_post(
                self.connection_uuid,
                "/home-battery-installation/" + self.contract["uuid"] + "/actions/disable_home_optimization",
            )

        self.data["battery_control_mode"]["processing"] = True

        self.async_update_listeners()

        await self.async_fetch_battery_control_mode()

    async def async_enable_dynamic_charging(self) -> None:

        if self.is_mode_enabled("home_optimization"):
            await self.api.async_post(
                self.connection_uuid,
                "/home-battery-installation/" + self.contract["uuid"] + "/actions/disable_home_optimization",
            )

        if self.is_mode_enabled("self_consumption"):
            await self.api.async_post(
                self.connection_uuid,
                "/home-battery-installation/" + self.contract["uuid"] + "/actions/disable_self_consumption",
            )

        self.data["battery_control_mode"]["processing"] = True

        self.async_update_listeners()

        await self.async_fetch_battery_control_mode()

    async def async_enable_home_optimization(self) -> None:
        charge_power = self.data.get("battery_home_optimization", {}).get("max_desired_charge_power_watts")
        discharge_power = self.data.get("battery_home_optimization", {}).get("max_desired_discharge_power_watts")

        if (charge_power is None) ^ (discharge_power is None):
            _LOGGER.info(
                "skipped async_enable_home_optimization as only 1 param is set (need both or none): charge=%s, discharge=%s",
                charge_power,
                discharge_power,
            )
            return

        params = {}
        if charge_power is not None:
            params = {
                "max_desired_charge_power_w": charge_power,
                "max_desired_discharge_power_w": discharge_power,
            }

        _LOGGER.info("async_enable_home_optimization: params %s", params)
        response = await self.api.async_post(
            self.connection_uuid,
            f"/home-battery-installation/{self.contract["uuid"]}/actions/enable_home_optimization",
            params
        )

        _LOGGER.debug("enable_home_optimization response: %s", response)

        if "max_desired_discharge_power_w" in response:
            self.data["battery_home_optimization"]["max_desired_discharge_power_watts"] = response["max_desired_discharge_power_w"]
        if "max_desired_charge_power_w" in response:
            self.data["battery_home_optimization"]["max_desired_charge_power_watts"] = response["max_desired_charge_power_w"]

        if self.is_mode_enabled("self_consumption"):
            await self.api.async_post(
                self.connection_uuid,
                f"/home-battery-installation/{self.contract["uuid"]}/actions/disable_self_consumption",
            )

        self.data["battery_control_mode"]["processing"] = True

        await self.async_fetch_battery_control_mode()

    async def async_fetch_battery_control_mode(self):

        battery_control_mode = await self.api.async_get_battery_control_mode(self.contract["uuid"])
        if battery_control_mode:
            self.data["battery_control_mode"] = battery_control_mode
            _LOGGER.info("battery_control_mode %s", battery_control_mode)
        else:
            self.data["battery_control_mode"]["processing"] = False

        battery_home_optimization = await self.api.async_get_battery_home_optimization(self.contract["uuid"])
        if battery_home_optimization:
            self.data["battery_home_optimization"] = battery_home_optimization

        self.async_update_listeners()

    def is_mode_enabled(self, mode: str) -> bool:
        return True if self.data.get("battery_control_mode", {}).get("modes", {}).get(mode, {}).get("enabled", False) else False
