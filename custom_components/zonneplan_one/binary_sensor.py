"""Zonneplan binary sensor"""
from typing import Optional, Any
from voluptuous.validators import Number

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
import logging
from homeassistant.core import callback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
)

from .coordinator import ZonneplanUpdateCoordinator
from .const import (
    DOMAIN,
    BINARY_SENSORS_TYPES,
    CHARGE_POINT,
    BATTERY,
    ZonneplanBinarySensorEntityDescription,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistantType, config_entry, async_add_entities):

    coordinator: ZonneplanUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    entities = []
    for uuid, connection in coordinator.connections.items():
        charge_point = coordinator.getConnectionValue(uuid, CHARGE_POINT)
        battery = coordinator.getConnectionValue(uuid, BATTERY)

        _LOGGER.debug("Setup binary sensors for connnection %s", uuid)

        if charge_point:
            for install_index in range(len(charge_point)):
                for sensor_key in BINARY_SENSORS_TYPES[CHARGE_POINT]:
                    entities.append(
                        ZonneplanChargePointBinarySensor(
                            uuid,
                            sensor_key,
                            coordinator,
                            install_index,
                            BINARY_SENSORS_TYPES[CHARGE_POINT][sensor_key],
                        )
                    )

        if battery:
            for install_index in range(len(battery)):
                for sensor_key in BINARY_SENSORS_TYPES[BATTERY]:
                    entities.append(
                        ZonneplanBatteryBinarySensor(
                            uuid,
                            sensor_key,
                            coordinator,
                            install_index,
                            BINARY_SENSORS_TYPES[BATTERY][sensor_key],
                        )
                    )

    async_add_entities(entities)


class ZonneplanBinarySensor(CoordinatorEntity, RestoreEntity, BinarySensorEntity):
    """Abstract class for a zonneplan sensor."""

    coordinator: ZonneplanUpdateCoordinator

    def __init__(
        self,
        connection_uuid,
        sensor_key: str,
        coordinator: ZonneplanUpdateCoordinator,
        install_index: Number,
        description: ZonneplanBinarySensorEntityDescription,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._connection_uuid = connection_uuid
        self._sensor_key = sensor_key
        self._install_index = install_index
        self.entity_description = description

        self._attr_is_on = self._value_from_coordinator()

    @property
    def install_uuid(self) -> str:
        """Return install ID."""
        return self._connection_uuid

    @property
    def unique_id(self) -> Optional[str]:
        """Return a unique ID."""
        return self.install_uuid + "_" + self._sensor_key

    @property
    def name(self) -> str:
        """Return the name of the entity."""

        name = self.entity_description.name
        if self._install_index and self._install_index > 0:
            name += " (" + str(self._install_index + 1) + ")"

        return name

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        self._attr_is_on = self._value_from_coordinator()

        super()._handle_coordinator_update()

    def _value_from_coordinator(self) -> bool:
        is_on = self.coordinator.getConnectionValue(
            self._connection_uuid,
            self.entity_description.key.format(install_index=self._install_index),
        )

        _LOGGER.debug("update binary sensor %s [%s]", self.name, is_on)
        return bool(is_on)

    @property
    def extra_state_attributes(self):

        if not self.entity_description.attributes:
            return

        attrs = {}
        for attribute in self.entity_description.attributes:
            value = self.coordinator.getConnectionValue(
                self._connection_uuid,
                attribute.key.format(install_index=self._install_index),
            )
            _LOGGER.debug(f'Update {self.name}.attribute[{attribute.label}]: {value}')
            attrs[attribute.label] = value

        return attrs

class ZonneplanChargePointBinarySensor(ZonneplanBinarySensor):
    @property
    def install_uuid(self) -> str:
        """Return install ID."""
        if self._install_index < 0:
            return self._connection_uuid
        else:
            return self.coordinator.getConnectionValue(
                self._connection_uuid,
                "charge_point_installation.{install_index}.uuid".format(
                    install_index=self._install_index
                ),
            )

    @property
    def device_info(self):
        """Return the device information."""
        device_info = {
            "identifiers": {(DOMAIN, self._connection_uuid, CHARGE_POINT)},
            "manufacturer": "Zonneplan",
            "name": self.coordinator.getConnectionValue(
                self._connection_uuid,
                "charge_point_installation.0.label",
            ),
        }

        if self._install_index >= 0:
            device_info["identifiers"].add((DOMAIN, self.install_uuid))
            device_info["name"] = self.coordinator.getConnectionValue(
                self._connection_uuid,
                "charge_point_installation.{install_index}.label".format(
                    install_index=self._install_index
                ),
            )
            device_info["model"] = self.coordinator.getConnectionValue(
                self._connection_uuid,
                "charge_point_installation.{install_index}.meta.serial_number".format(
                    install_index=self._install_index
                ),
            )

        return device_info

class ZonneplanBatteryBinarySensor(ZonneplanBinarySensor):
    @property
    def install_uuid(self) -> str:
        """Return install ID."""
        if self._install_index < 0:
            return self._connection_uuid
        else:
            return self.coordinator.getConnectionValue(
                self._connection_uuid,
                "home_battery_installation.{install_index}.uuid".format(
                    install_index=self._install_index
                ),
            )

    @property
    def device_info(self):
        """Return the device information."""
        device_info = {
            "identifiers": {(DOMAIN, self._connection_uuid, BATTERY)},
            "manufacturer": "Zonneplan",
            "name": self.coordinator.getConnectionValue(
                self._connection_uuid,
                "home_battery_installation.0.label",
            ),
        }

        if self._install_index >= 0:
            device_info["identifiers"].add((DOMAIN, self.install_uuid))
            device_info["name"] = self.coordinator.getConnectionValue(
                self._connection_uuid,
                "home_battery_installation.{install_index}.label".format(
                    install_index=self._install_index
                ),
            )
            device_info["model"] = self.coordinator.getConnectionValue(
                self._connection_uuid,
                "home_battery_installation.{install_index}.label".format(
                    install_index=self._install_index
                ),
            )
            device_info["serial_number"] = self.coordinator.getConnectionValue(
                self._connection_uuid,
                "home_battery_installation.{install_index}.meta.identifier".format(
                    install_index=self._install_index
                ),
            )

        return device_info
