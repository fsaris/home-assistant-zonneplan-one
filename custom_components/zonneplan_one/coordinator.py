"""Zonneplan DataUpdateCoordinator"""
from datetime import timedelta
from http import HTTPStatus
import logging

from aiohttp.client_exceptions import ClientResponseError

from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import AsyncConfigEntryAuth
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ZonneplanUpdateCoordinator(DataUpdateCoordinator):
    """Zonneplan status update coordinator"""

    def __init__(
        self,
        hass: HomeAssistantType,
        api: AsyncConfigEntryAuth,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=120),
        )
        self.data: dict = {}
        self.api: AsyncConfigEntryAuth = api

    async def _async_update_data(self) -> dict:
        """Fetch the latest status."""
        try:
            return await self._fetch_data()
        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise e

    async def _fetch_data(self) -> dict:
        result = {}
        _LOGGER.info("_async_update_data: start")
        # Get all info of all connections (part of your account info)
        accounts = await self.api.async_get_user_accounts()
        if not accounts:
            return result
        _LOGGER.info("_async_update_data: parse addresses")
        # Flatten all found connections
        for address_group in accounts["address_groups"]:
            for connection in address_group["connections"]:
                if not connection["uuid"] in result:
                    result[connection["uuid"]] = {
                        "uuid": connection["uuid"],
                        "live_data": {},
                        "electricity_data": {},
                        "gas_data": {},
                        "summary_data": {},
                    }
                for contract in connection["contracts"]:
                    if not contract["type"] in result[connection["uuid"]]:
                        result[connection["uuid"]][contract["type"]] = []
                    result[connection["uuid"]][contract["type"]].append(contract)

        _LOGGER.info("_async_update_data: fetch live data")

        # Update last live data for each connection
        for uuid, connection in result.items():
            if "pv_installation" in connection:
                live_data = await self.api.async_get(
                    uuid, "/pv_installation/charts/live"
                )
                if live_data:
                    result[uuid]["live_data"] = live_data[0]
            if "p1_installation" in connection:
                electricity = await self.api.async_get(uuid, "/electricity-delivered")
                if electricity:
                    result[uuid]["electricity_data"] = electricity
                gas = await self.api.async_get(uuid, "/gas")
                if gas:
                    result[uuid]["gas_data"] = gas

            summary = await self.api.async_get(uuid, "/summary")
            if summary:
                result[uuid]["summary_data"] = summary

        _LOGGER.info("_async_update_data: done")
        _LOGGER.debug("Result %s", result)

        return result

    @property
    def connections(self) -> dict:
        return self.data

    def getConnectionValue(self, connection_uuid: str, value_path: str):
        if not connection_uuid in self.data:
            return None

        keys = value_path.split(".")
        rv = self.data[connection_uuid]
        for key in keys:
            if key.isdigit():
                key = int(key)
                if not type(rv) is list or len(rv) < key:
                    _LOGGER.warning(
                        "Could not find %d of %s",
                        key,
                        value_path,
                    )
                    _LOGGER.debug(" in %s %s", rv, type(rv))
                    return None

            elif not key in rv:
                _LOGGER.warning("Could not find %s of %s", key, value_path)
                _LOGGER.debug("in %s", rv)
                return None
            rv = rv[key]

        return rv
