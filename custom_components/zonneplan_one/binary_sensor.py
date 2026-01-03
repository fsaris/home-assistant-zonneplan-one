"""Zonneplan binary sensor."""

import logging
from collections.abc import Mapping
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import (
    BATTERY,
    BINARY_SENSORS_TYPES,
    CHARGE_POINT,
    PV_INSTALL,
    ZonneplanBinarySensorEntityDescription,
)
from .coordinators.account_data_coordinator import ZonneplanConfigEntry
from .coordinators.battery_data_coordinator import BatteryDataUpdateCoordinator
from .coordinators.charge_point_data_coordinator import ChargePointDataUpdateCoordinator
from .coordinators.pv_data_coordinator import PvDataUpdateCoordinator
from .coordinators.zonneplan_data_update_coordinator import (
    ZonneplanDataUpdateCoordinator,
)
from .entity import BatteryEntity, ChargePointEntity, PvEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: ZonneplanConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    entities = []
    for uuid, connection in entry.runtime_data.coordinators.items():
        _LOGGER.debug("Setup binary sensors for connection %s", uuid)

        if connection.pv_installation:
            for install_index in range(len(connection.pv_installation.contracts)):
                entities.extend(
                    ZonneplanPvBinarySensor(
                        uuid,
                        sensor_key,
                        connection.pv_installation,
                        install_index,
                        BINARY_SENSORS_TYPES[PV_INSTALL][sensor_key],
                    )
                    for sensor_key in BINARY_SENSORS_TYPES[PV_INSTALL]
                )

        if connection.charge_point_installation:
            entities.extend(
                ZonneplanChargePointBinarySensor(
                    uuid,
                    sensor_key,
                    connection.charge_point_installation,
                    0,
                    BINARY_SENSORS_TYPES[CHARGE_POINT][sensor_key],
                )
                for sensor_key in BINARY_SENSORS_TYPES[CHARGE_POINT]
            )

        if connection.home_battery_installation:
            entities.extend(
                ZonneplanBatteryBinarySensor(
                    uuid,
                    sensor_key,
                    connection.home_battery_installation,
                    0,
                    BINARY_SENSORS_TYPES[BATTERY][sensor_key],
                )
                for sensor_key in BINARY_SENSORS_TYPES[BATTERY]
            )

    async_add_entities(entities)


class ZonneplanBinarySensor(CoordinatorEntity, RestoreEntity, BinarySensorEntity):
    """Abstract class for a Zonneplan Binary Sensor."""

    coordinator: ZonneplanDataUpdateCoordinator
    entity_description: ZonneplanBinarySensorEntityDescription
    _install_index: int

    def __init__(
        self,
        connection_uuid: str,
        sensor_key: str,
        coordinator: ZonneplanDataUpdateCoordinator,
        install_index: int,
        description: ZonneplanBinarySensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._connection_uuid = connection_uuid
        self._sensor_key = sensor_key
        self._install_index = install_index
        self.entity_description = description

    @property
    def install_uuid(self) -> str:
        """Return install ID."""
        return self._connection_uuid

    @property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return self.install_uuid + "_" + self._sensor_key

    @property
    def available(self) -> bool:
        """Return True if entity and coordinator.data is available."""
        return super().available and self.coordinator.data is not None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_is_on = self._value_from_coordinator()

        super()._handle_coordinator_update()

    def _value_from_coordinator(self) -> bool:
        is_on = self.coordinator.get_data_value(
            self.entity_description.key.format(install_index=self._install_index),
        )

        _LOGGER.debug("update binary sensor %s [%s]", self.unique_id, is_on)
        return bool(is_on)

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:
        if not self.entity_description.attributes:
            return None

        attrs = {}
        for attribute in self.entity_description.attributes:
            value = self.coordinator.get_data_value(
                attribute.key.format(install_index=self._install_index),
            )
            _LOGGER.debug("Update %s.attribute[%s]: %s", self.unique_id, attribute.label, value)
            attrs[attribute.label] = value

        return attrs


class ZonneplanPvBinarySensor(PvEntity, ZonneplanBinarySensor):
    coordinator: PvDataUpdateCoordinator


class ZonneplanChargePointBinarySensor(ChargePointEntity, ZonneplanBinarySensor):
    coordinator: ChargePointDataUpdateCoordinator


class ZonneplanBatteryBinarySensor(BatteryEntity, ZonneplanBinarySensor):
    coordinator: BatteryDataUpdateCoordinator
