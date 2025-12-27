"""Zonneplan select"""
from typing import Optional

from homeassistant.components.select import SelectEntity
import logging
from homeassistant.core import (
    HomeAssistant
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .coordinators.battery_control_data_coordinator import BatteryControlDataUpdateCoordinator
from .entity import BatteryEntity

from .const import (
    BATTERY_CONTROL,
    DOMAIN,
    SELECT_TYPES,
    ZonneplanNumberEntityDescription,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    connections: dict = hass.data[DOMAIN][config_entry.entry_id]["connections"]

    entities = []
    for uuid, connection in connections.items():

        if BATTERY_CONTROL in connection:
            _LOGGER.debug("Setup battery control select entities for connection %s", uuid)

            for _key in SELECT_TYPES[BATTERY_CONTROL]:
                entities.append(
                    ZonneplanBatteryControlModeSelect(
                        uuid,
                        _key,
                        connection[BATTERY_CONTROL],
                        0,
                        SELECT_TYPES[BATTERY_CONTROL][_key],
                    )
                )

    async_add_entities(entities)


class ZonneplanBatteryControlModeSelect(BatteryEntity, CoordinatorEntity, SelectEntity):
    coordinator: BatteryControlDataUpdateCoordinator
    _connection_uuid: str
    _install_index: int
    _key: str
    entity_description: ZonneplanNumberEntityDescription

    def __init__(
            self,
            connection_uuid,
            _key: str,
            coordinator: BatteryControlDataUpdateCoordinator,
            install_index: int,
            description: ZonneplanNumberEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._connection_uuid = connection_uuid
        self._install_index = install_index
        self._key = _key
        self.entity_description = description

    @property
    def unique_id(self) -> Optional[str]:
        """Return a unique ID."""
        return self.install_uuid + "_" + self._key

    @property
    def available(self) -> bool:
        """Return True if entity and coordinator.data is available."""
        return (
                super().available
                and self.coordinator.data is not None
        )

    @property
    def options(self) -> list[str]:
        if not self.available:
            return []

        modes = self.coordinator.get_data_value("battery_control_mode.modes") or {}
        return [key for key, value in modes.items() if value.get("available")]

    @property
    def current_option(self) -> str:
        return self.coordinator.get_data_value(self.entity_description.key)

    async def async_select_option(self, option: str) -> None:

        if option == "self_consumption":
            await self.coordinator.async_enable_self_consumption()
        elif option == "dynamic_charging":
            await self.coordinator.async_enable_dynamic_charging()
        elif option == "home_optimization":
            await self.coordinator.async_enable_home_optimization()
        else:
            _LOGGER.warning("Unknown action for %s", option)
