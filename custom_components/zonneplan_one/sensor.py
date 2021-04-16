"""Zonneplan Sensor"""
import dateutil.parser
import dateutil.tz
from typing import Optional
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
import logging
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.const import ENERGY_KILO_WATT_HOUR

from .coordinator import ZonneplanUpdateCoordinator
from .const import DOMAIN, SENSOR_TYPES

_LOGGER = logging.getLogger(__name__)


def convert_date(timestamp: str, format: str) -> str:
    to_zone = dateutil.tz.gettz("Europe/Amsterdam")
    return dateutil.parser.parse(timestamp).astimezone(to_zone).strftime(format)


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

            if SENSOR_TYPES[sensor_key][0] == "pv_installation" and pv_installation:
                entities.append(ZonneplanPvSensor(uuid, sensor_key, coordinator))
            if SENSOR_TYPES[sensor_key][0] == "p1_installation" and p1_installation:
                entities.append(ZonneplanP1Sensor(uuid, sensor_key, coordinator))

    async_add_entities(entities)


class ZonneplanSensor(CoordinatorEntity, Entity):
    """Abstract class for a zonneplan sensor."""

    def __init__(
        self, connection_uuid, sensor_key: str, coordinator: ZonneplanUpdateCoordinator
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._connection_uuid = connection_uuid
        self._sensor_key = sensor_key
        self._type = SENSOR_TYPES[sensor_key][0]
        self._data_key = SENSOR_TYPES[self._sensor_key][1]
        self._label = SENSOR_TYPES[self._sensor_key][2]
        self._unit_of_measurement = SENSOR_TYPES[self._sensor_key][3]
        self._icon = SENSOR_TYPES[self._sensor_key][4]
        self._enabled_by_default = False
        if (
            len(SENSOR_TYPES[self._sensor_key]) > 5
            and SENSOR_TYPES[self._sensor_key][5]
        ):
            self._enabled_by_default = True

    @property
    def unique_id(self) -> Optional[str]:
        """Return a unique ID."""
        return self._connection_uuid + "_" + self._sensor_key

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        if (
            self._unit_of_measurement == "date_time"
            or self._unit_of_measurement == "date"
        ):
            return None
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
        if self._unit_of_measurement == ENERGY_KILO_WATT_HOUR:
            value = value / 1000
        if self._unit_of_measurement == "date_time":
            value = convert_date(value, "%Y-%m-%d %H:%M:%S")
        if self._unit_of_measurement == "date":
            value = convert_date(value, "%Y-%m-%d")
        return value

    @property
    def icon(self):
        """Return the sensor icon."""
        return self._icon

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
