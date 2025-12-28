"""Zonneplan number"""
from typing import Optional

from homeassistant.components.number import NumberEntity
import logging
from homeassistant.core import (
    HomeAssistant
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinators.account_data_coordinator import ZonneplanConfigEntry
from .coordinators.battery_control_data_coordinator import BatteryControlDataUpdateCoordinator
from .const import (
    BATTERY_CONTROL,
    NUMBER_TYPES,
    ZonneplanNumberEntityDescription,
)
from .entity import BatteryEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ZonneplanConfigEntry, async_add_entities):
    entities = []
    for uuid, connection in entry.runtime_data.coordinators.items():

        if connection.battery_control:
            _LOGGER.debug("Setup battery control number entities for connection %s", uuid)

            for sensor_key in NUMBER_TYPES[BATTERY_CONTROL]:
                entities.append(
                    ZonneplanBatteryNumber(
                        uuid,
                        sensor_key,
                        connection.battery_control,
                        0,
                        NUMBER_TYPES[BATTERY_CONTROL][sensor_key],
                    )
                )

    async_add_entities(entities)


class ZonneplanBatteryNumber(BatteryEntity, CoordinatorEntity, NumberEntity):
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
        """Return if entity is available."""
        if not self.coordinator.data or not self.coordinator.last_update_success:
            return False

        control_mode = self.coordinator.get_data_value("battery_control_mode.control_mode")

        return True if control_mode == "home_optimization" else False

    @property
    def native_min_value(self) -> float:
        return self.coordinator.get_data_value(
            self.entity_description.key.format(install_index=self._install_index).replace("_watts", "_limits.min_watts"),
        ) or 0

    @property
    def native_max_value(self) -> float:
        return self.coordinator.get_data_value(
            self.entity_description.key.format(install_index=self._install_index).replace("_watts", "_limits.max_watts"),
        ) or 2000

    @property
    def native_value(self) -> float:
        return self.coordinator.get_data_value(
            self.entity_description.key.format(install_index=self._install_index),
        )

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.set_data_value(self.entity_description.key.format(install_index=self._install_index), int(value))

        await self.coordinator.async_enable_home_optimization()
