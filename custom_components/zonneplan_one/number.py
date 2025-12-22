"""Zonneplan number"""
from typing import Optional

from homeassistant.components.number import NumberEntity
import logging
from homeassistant.core import (
    HomeAssistant
)

from .entity import ZonneplanBatteryEntity
from .coordinator import ZonneplanUpdateCoordinator
from .const import (
    BATTERY,
    DOMAIN,
    NUMBER_TYPES,
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
                for sensor_key in NUMBER_TYPES[BATTERY]:
                    entities.append(
                        ZonneplanBatteryNumber(
                            uuid,
                            sensor_key,
                            coordinator,
                            install_index,
                            NUMBER_TYPES[BATTERY][sensor_key],
                        )
                    )

    async_add_entities(entities)


class ZonneplanBatteryNumber(ZonneplanBatteryEntity, NumberEntity):
    coordinator: ZonneplanUpdateCoordinator
    entity_description: ZonneplanNumberEntityDescription

    def __init__(
            self,
            connection_uuid,
            number_key: str,
            coordinator: ZonneplanUpdateCoordinator,
            install_index: int,
            description: ZonneplanNumberEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator, connection_uuid, install_index, number_key)
        self.entity_description = description

        self._attr_native_min_value = self.coordinator.get_connection_value(
            self._connection_uuid,
            self.entity_description.key.format(install_index=self._install_index).replace("_watts", "_limits.min_watts"),
        ) or 0
        self._attr_native_max_value = self.coordinator.get_connection_value(
            self._connection_uuid,
            self.entity_description.key.format(install_index=self._install_index).replace("_watts", "_limits.max_watts"),
        ) or 2000

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False

        control_mode = self.coordinator.get_connection_value(self._connection_uuid, "battery_control_mode.control_mode")

        return True if control_mode == "home_optimization" else False

    @property
    def native_value(self) -> float:
        return self.coordinator.get_connection_value(
            self._connection_uuid,
            self.entity_description.key.format(install_index=self._install_index),
        )

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.set_connection_value(self._connection_uuid, self.entity_description.key.format(install_index=self._install_index), int(value))

        await self.coordinator.async_enable_home_optimization(self._connection_uuid, self._install_index, self._battery_uuid)
