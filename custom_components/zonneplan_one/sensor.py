"""Zonneplan Sensor"""
from datetime import datetime, tzinfo
from typing import Optional
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
import logging
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.components.sensor import (
    STATE_CLASS_MEASUREMENT,
    SensorEntity,
)
from homeassistant.const import (
    DEVICE_CLASS_TIMESTAMP,
    ENERGY_KILO_WATT_HOUR,
    VOLUME_CUBIC_METERS,
)
import homeassistant.util.dt as dt_util
import pytz

from .coordinator import ZonneplanUpdateCoordinator
from .const import DOMAIN, SENSOR_TYPES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistantType, config_entry, async_add_entities):

    coordinator: ZonneplanUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    entities = []
    for uuid, connection in coordinator.connections.items():
        pv_installation = coordinator.getConnectionValue(uuid, "pv_installation")
        p1_installation = coordinator.getConnectionValue(uuid, "p1_installation")
        _LOGGER.debug("Setup sensors for connnection %s", uuid)
        for sensor_key in SENSOR_TYPES:

            if (
                SENSOR_TYPES[sensor_key].get("type") == "pv_installation"
                and pv_installation
            ):
                entities.append(ZonneplanPvSensor(uuid, sensor_key, coordinator))
            if (
                SENSOR_TYPES[sensor_key].get("type") == "p1_installation"
                and p1_installation
            ):
                entities.append(ZonneplanP1Sensor(uuid, sensor_key, coordinator))

    async_add_entities(entities)


class ZonneplanSensor(CoordinatorEntity, SensorEntity):
    """Abstract class for a zonneplan sensor."""

    def __init__(
        self, connection_uuid, sensor_key: str, coordinator: ZonneplanUpdateCoordinator
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._connection_uuid = connection_uuid
        self._sensor_key = sensor_key
        self._type = SENSOR_TYPES[sensor_key].get("type")
        self._data_key = SENSOR_TYPES[self._sensor_key].get("key")
        self._label = SENSOR_TYPES[self._sensor_key].get("label")
        self._unit_of_measurement = SENSOR_TYPES[self._sensor_key].get("unit")
        self._icon = SENSOR_TYPES[self._sensor_key].get("icon")
        self._device_class = SENSOR_TYPES[self._sensor_key].get("device_class")
        self._state_class = SENSOR_TYPES[self._sensor_key].get("state_class")
        self._last_reset_today_data_key = SENSOR_TYPES[self._sensor_key].get(
            "last_reset_today_key"
        )
        self._last_reset_data_key = SENSOR_TYPES[self._sensor_key].get("last_reset_key")
        self._enabled_by_default = False
        if SENSOR_TYPES[self._sensor_key].get("default_enabled"):
            self._enabled_by_default = True

    @property
    def unique_id(self) -> Optional[str]:
        """Return a unique ID."""
        return self._connection_uuid + "_" + self._sensor_key

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def name(self):
        """Return the name."""
        return "Zonneplan " + self._label

    @property
    def state(self):
        value = self.coordinator.getConnectionValue(
            self._connection_uuid, self._data_key
        )
        # No value or 0 then we don't need to convert the value
        if not value:
            return value

        if self._unit_of_measurement == ENERGY_KILO_WATT_HOUR:
            value = value / 1000
        if self._unit_of_measurement == VOLUME_CUBIC_METERS:
            value = value / 1000

        return value

    @property
    def icon(self):
        """Return the sensor icon."""
        return self._icon

    @property
    def device_class(self):
        """Return the sensor device_class."""
        return self._device_class

    @property
    def state_class(self) -> any:
        return self._state_class

    @property
    def last_reset(self):
        if self._last_reset_data_key:
            value = self.coordinator.getConnectionValue(
                self._connection_uuid, self._last_reset_data_key
            )
            if value:
                return dt_util.parse_datetime(value)

        elif self._last_reset_today_data_key:
            value = self.coordinator.getConnectionValue(
                self._connection_uuid, self._last_reset_today_data_key
            )
            if value:
                return (
                    dt_util.parse_datetime(value)
                    # Dates are received in UTC timezone but are to be treadted as "Europe/Amsterdam"
                    # else we are talking about the wrong midnight
                    # '2021-08-05T22:00:00.000000Z' would be 2021-08-05 but is 2021-08-06
                    .astimezone(pytz.timezone("Europe/Amsterdam")).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                )

        return None

    @property
    def entity_registry_enabled_default(self) -> bool:
        """Return if the entity should be enabled when first added to the entity registry."""
        return self._enabled_by_default


class ZonneplanPvSensor(ZonneplanSensor):
    @property
    def device_info(self):
        """Return the device information."""
        return {
            "identifiers": {(DOMAIN, self._connection_uuid, self._type)},
            "name": self.coordinator.getConnectionValue(
                self._connection_uuid, "pv_installation.meta.name"
            ),
            "model": self.coordinator.getConnectionValue(
                self._connection_uuid, "pv_installation.meta.name"
            ),
            "manufacturer": "Zonneplan",
            "sw_version": self.coordinator.getConnectionValue(
                self._connection_uuid,
                "pv_installation.meta.module_firmware_version",
            )
            + " - "
            + self.coordinator.getConnectionValue(
                self._connection_uuid,
                "pv_installation.meta.inverter_firmware_version",
            ),
        }


class ZonneplanP1Sensor(ZonneplanSensor):
    @property
    def name(self):
        """Return the name."""
        return "Zonneplan P1 " + self._label

    @property
    def device_info(self):
        """Return the device information."""
        return {
            "identifiers": {(DOMAIN, self._connection_uuid, self._type)},
            "name": self.coordinator.getConnectionValue(
                self._connection_uuid, "p1_installation.label"
            ),
            "model": self.coordinator.getConnectionValue(
                self._connection_uuid, "p1_installation.meta.sgn_serial_number"
            ),
            "manufacturer": "Zonneplan",
            "sw_version": self.coordinator.getConnectionValue(
                self._connection_uuid,
                "p1_installation.meta.sgn_firmware",
            ),
            "via_device": (DOMAIN, self._connection_uuid, "pv_installation"),
        }
