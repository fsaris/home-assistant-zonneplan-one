"""Zonneplan Sensor"""
from typing import Optional
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
import logging
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.components.sensor import (
    SensorEntity,
)
from homeassistant.const import (
    ENERGY_KILO_WATT_HOUR,
    VOLUME_CUBIC_METERS,
)
import homeassistant.util.dt as dt_util
import pytz

from .coordinator import ZonneplanUpdateCoordinator
from .const import (
    DOMAIN,
    P1_INSTALL,
    PV_INSTALL,
    SENSOR_TYPES,
    ZonneplanSensorEntityDescription,
)

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

        if pv_installation:
            for sensor_key in SENSOR_TYPES[PV_INSTALL]:
                entities.append(
                    ZonneplanPvSensor(
                        uuid,
                        sensor_key,
                        coordinator,
                        SENSOR_TYPES[PV_INSTALL][sensor_key],
                    )
                )

        if p1_installation:
            for sensor_key in SENSOR_TYPES[P1_INSTALL]:
                entities.append(
                    ZonneplanP1Sensor(
                        uuid,
                        sensor_key,
                        coordinator,
                        SENSOR_TYPES[P1_INSTALL][sensor_key],
                    )
                )

    async_add_entities(entities)


class ZonneplanSensor(CoordinatorEntity, SensorEntity):
    """Abstract class for a zonneplan sensor."""

    def __init__(
        self,
        connection_uuid,
        sensor_key: str,
        coordinator: ZonneplanUpdateCoordinator,
        description: ZonneplanSensorEntityDescription,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._connection_uuid = connection_uuid
        self._sensor_key = sensor_key
        self.entity_description = description

    @property
    def unique_id(self) -> Optional[str]:
        """Return a unique ID."""
        return self._connection_uuid + "_" + self._sensor_key

    @property
    def state(self):
        value = self.coordinator.getConnectionValue(
            self._connection_uuid, self.entity_description.key
        )
        # No value or 0 then we don't need to convert the value
        if not value:
            return value

        if self.unit_of_measurement == ENERGY_KILO_WATT_HOUR:
            value = value / 1000
        if self.unit_of_measurement == VOLUME_CUBIC_METERS:
            value = value / 1000

        return value

    @property
    def last_reset(self):
        if self.entity_description.last_reset_key:
            value = self.coordinator.getConnectionValue(
                self._connection_uuid, self.entity_description.last_reset_key
            )
            if value:
                return dt_util.parse_datetime(value)

        elif self.entity_description.last_reset_today_key:
            value = self.coordinator.getConnectionValue(
                self._connection_uuid, self.entity_description.last_reset_today_key
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


class ZonneplanPvSensor(ZonneplanSensor):
    @property
    def device_info(self):
        """Return the device information."""
        return {
            "identifiers": {(DOMAIN, self._connection_uuid, PV_INSTALL)},
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
    def device_info(self):
        """Return the device information."""
        return {
            "identifiers": {(DOMAIN, self._connection_uuid, P1_INSTALL)},
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
