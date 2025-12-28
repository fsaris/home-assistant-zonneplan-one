"""Zonneplan account DataUpdateCoordinator"""

from datetime import timedelta
from http import HTTPStatus
from dataclasses import dataclass

import logging
from aiohttp.client_exceptions import ClientResponseError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    HomeAssistant
)
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from .zonneplan_data_update_coordinator import ZonneplanDataUpdateCoordinator
from .summary_data_coordinator import SummaryDataUpdateCoordinator
from .pv_data_coordinator import PvDataUpdateCoordinator
from .electricity_data_coordinator import ElectricityDataUpdateCoordinator
from .gas_data_coordinator import GasDataUpdateCoordinator
from .charge_point_data_coordinator import ChargePointDataUpdateCoordinator
from .battery_data_coordinator import BatteryDataUpdateCoordinator
from .battery_charts_data_coordinator import BatteryChartsDataUpdateCoordinator
from .battery_control_data_coordinator import BatteryControlDataUpdateCoordinator
from .electricity_home_consumption_data_coordinator import ElectricityHomeConsumptionDataUpdateCoordinator

from ..api import AsyncConfigEntryAuth
from ..const import DOMAIN
from ..zonneplan_api.types import ZonneplanAddressGroup

_LOGGER = logging.getLogger(__name__)

type ZonneplanConfigEntry = ConfigEntry[AccountDataUpdateCoordinator]


@dataclass
class ConnectionCoordinators:
    gas: SummaryDataUpdateCoordinator | None = None
    electricity: SummaryDataUpdateCoordinator | None = None
    pv_installation: PvDataUpdateCoordinator | None = None
    p1_electricity: ElectricityDataUpdateCoordinator | None = None
    p1_gas: GasDataUpdateCoordinator | None = None
    electricity_home_consumption: ElectricityHomeConsumptionDataUpdateCoordinator | None = None
    charge_point_installation: ChargePointDataUpdateCoordinator | None = None
    home_battery_installation: BatteryDataUpdateCoordinator | None = None
    battery_control: BatteryControlDataUpdateCoordinator | None = None
    battery_charts: BatteryChartsDataUpdateCoordinator | None = None


class AccountDataUpdateCoordinator(ZonneplanDataUpdateCoordinator):
    data: list[ZonneplanAddressGroup] | None
    coordinators: dict[str, ConnectionCoordinators] = {}

    def __init__(
            self,
            hass: HomeAssistant,
            api: AsyncConfigEntryAuth,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            request_refresh_debouncer=Debouncer(
                hass,
                _LOGGER,
                cooldown=60,
                immediate=False
            )
        )
        self.update_interval = timedelta(minutes=60)
        self.api: AsyncConfigEntryAuth = api

    async def _async_update_data(self) -> list[ZonneplanAddressGroup]:
        """Fetch the latest account status."""
        try:
            accounts = await self.api.async_get_user_accounts()
            if not accounts:
                raise UpdateFailed(retry_after=60)

            _LOGGER.debug("Accounts: %s", accounts)

            # todo: trigger integration reload on account changes
            return accounts.get("address_groups")

        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise e

    @property
    def address_groups(self) -> list[ZonneplanAddressGroup]:

        return self.data

    def add_coordinator(self, uuid: str, coordinator_type: str, coordinator: ZonneplanDataUpdateCoordinator):
        if uuid not in self.coordinators:
            self.coordinators[uuid] = ConnectionCoordinators()

        if hasattr(self.coordinators[uuid], coordinator_type):
            setattr(self.coordinators[uuid], coordinator_type, coordinator)
        else:
            _LOGGER.exception("Unknown coordinator type %s", coordinator_type)
