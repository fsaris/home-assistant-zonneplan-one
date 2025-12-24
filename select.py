"""Zonneplan select"""

from homeassistant.components.select import SelectEntity
import logging
from homeassistant.core import (
    HomeAssistant
)

from .entity import ZonneplanBatteryEntity
from .coordinator import ZonneplanUpdateCoordinator
from .const import (
    BATTERY,
    DOMAIN,
    SELECT_TYPES,
    ZonneplanNumberEntityDescription,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    coordinator: ZonneplanUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]

    entities = []
    for uuid, connection in coordinator.connections.items():

        battery = coordinator.get_connection_value(uuid, BATTERY)
        if battery:
            _LOGGER.debug("Setup battery number entities for connection %s", uuid)

            for install_index in range(len(battery)):
                for _key in SELECT_TYPES[BATTERY]:
                    entities.append(
                        ZonneplanBatteryControlModeSelect(
                            uuid,
                            _key,
                            coordinator,
                            install_index,
                            SELECT_TYPES[BATTERY][_key],
                        )
                    )

    async_add_entities(entities)


class ZonneplanBatteryControlModeSelect(ZonneplanBatteryEntity, SelectEntity):
    coordinator: ZonneplanUpdateCoordinator
    entity_description: ZonneplanNumberEntityDescription

    def __init__(
            self,
            connection_uuid,
            _key: str,
            coordinator: ZonneplanUpdateCoordinator,
            install_index: int,
            description: ZonneplanNumberEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, connection_uuid, install_index, _key)
        self.entity_description = description

    @property
    def options(self) -> list[str]:
        modes = self.coordinator.get_connection_value(self._connection_uuid, "battery_control_mode.modes") or {}
        return [key for key, value in modes.items() if value.get("available")]

    @property
    def current_option(self) -> str:
        return self.coordinator.get_connection_value(self._connection_uuid, self.entity_description.key)

    async def async_select_option(self, option: str) -> None:

        if option == "self_consumption":
            await self.coordinator.async_enable_self_consumption(
                self._connection_uuid, self._install_index, self._battery_uuid
            )
        elif option == "dynamic_charging":
            await self.coordinator.async_enable_dynamic_charging(
                self._connection_uuid, self._install_index, self._battery_uuid
            )
        elif option == "home_optimization":
            await self.coordinator.async_enable_home_optimization(
                self._connection_uuid, self._install_index, self._battery_uuid
            )
        else:
            _LOGGER.warning("Unknown action for %s", option)
