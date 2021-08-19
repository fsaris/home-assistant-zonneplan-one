"""Zonneplan Sensor"""
from typing import Optional

from voluptuous.validators import Number
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
        pv_installations = coordinator.getConnectionValue(uuid, "pv_installation")
        p1_installations = coordinator.getConnectionValue(uuid, "p1_installation")
        _LOGGER.debug("Setup sensors for connnection %s", uuid)

        if pv_installations:
            for install_index in range(len(pv_installations)):
                for sensor_key in SENSOR_TYPES[PV_INSTALL]["install"]:
                    entities.append(
                        ZonneplanPvSensor(
                            uuid,
                            sensor_key,
                            coordinator,
                            install_index,
                            SENSOR_TYPES[PV_INSTALL]["install"][sensor_key],
                        )
                    )

            for sensor_key in SENSOR_TYPES[PV_INSTALL]["totals"]:
                entities.append(
                    ZonneplanPvSensor(
                        uuid,
                        sensor_key,
                        coordinator,
                        -1,
                        SENSOR_TYPES[PV_INSTALL]["totals"][sensor_key],
                    )
                )

        if p1_installations:
            for install_index in range(len(p1_installations)):
                for sensor_key in SENSOR_TYPES[P1_INSTALL]["install"]:
                    entities.append(
                        ZonneplanP1Sensor(
                            uuid,
                            sensor_key,
                            coordinator,
                            install_index,
                            SENSOR_TYPES[P1_INSTALL]["install"][sensor_key],
                        )
                    )
            for sensor_key in SENSOR_TYPES[P1_INSTALL]["totals"]:
                entities.append(
                    ZonneplanP1Sensor(
                        uuid,
                        sensor_key,
                        coordinator,
                        -1,
                        SENSOR_TYPES[P1_INSTALL]["totals"][sensor_key],
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
        install_index: Number,
        description: ZonneplanSensorEntityDescription,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._connection_uuid = connection_uuid
        self._sensor_key = sensor_key
        self._install_index = install_index
        self.entity_description = description

    @property
    def install_uuid(self) -> str:
        """Return a install ID."""
        return self._connection_uuid

    @property
    def unique_id(self) -> Optional[str]:
        """Return a unique ID."""
        return self.install_uuid + "_" + self._sensor_key

    @property
    def name(self) -> str:
        """Return the name of the entity."""

        name = self.entity_description.name
        if self._install_index > 0:
            name += " (" + str(self._install_index + 1) + ")"

        return name

    @property
    def native_value(self):
        value = self.coordinator.getConnectionValue(
            self._connection_uuid,
            self.entity_description.key.format(install_index=self._install_index),
        )
        # No value or 0 then we don't need to convert the value
        if not value:
            return value

        if self.native_unit_of_measurement == ENERGY_KILO_WATT_HOUR:
            value = value / 1000
        if self.native_unit_of_measurement == VOLUME_CUBIC_METERS:
            value = value / 1000

        return value


class ZonneplanPvSensor(ZonneplanSensor):
    @property
    def install_uuid(self) -> str:
        """Return a install ID."""
        if self._install_index < 0:
            return self._connection_uuid
        else:
            return self.coordinator.getConnectionValue(
                self._connection_uuid,
                "pv_installation.{install_index}.uuid".format(
                    install_index=self._install_index
                ),
            )

    @property
    def device_info(self):
        """Return the device information."""
        device_info = {
            "identifiers": {(DOMAIN, self._connection_uuid, PV_INSTALL)},
            "manufacturer": "Zonneplan",
            "name": self.coordinator.getConnectionValue(
                self._connection_uuid,
                "pv_installation.0.label",
            ),
        }

        if self._install_index >= 0:
            device_info["identifiers"].add((DOMAIN, self.install_uuid))
            device_info["name"] = self.coordinator.getConnectionValue(
                self._connection_uuid,
                "pv_installation.{install_index}.meta.name".format(
                    install_index=self._install_index
                ),
            )
            device_info["model"] = self.coordinator.getConnectionValue(
                self._connection_uuid,
                "pv_installation.{install_index}.meta.name".format(
                    install_index=self._install_index
                ),
            )
            device_info["sw_version"] = (
                self.coordinator.getConnectionValue(
                    self._connection_uuid,
                    "pv_installation.{install_index}.meta.module_firmware_version".format(
                        install_index=self._install_index
                    ),
                )
                + " - "
                + self.coordinator.getConnectionValue(
                    self._connection_uuid,
                    "pv_installation.{install_index}.meta.inverter_firmware_version".format(
                        install_index=self._install_index
                    ),
                )
            )

        return device_info


class ZonneplanP1Sensor(ZonneplanSensor):
    @property
    def install_uuid(self) -> str:
        """Return a install ID."""
        if self._install_index < 0:
            return self._connection_uuid
        else:
            return self.coordinator.getConnectionValue(
                self._connection_uuid,
                "p1_installation.{install_index}.uuid".format(
                    install_index=self._install_index
                ),
            )

    @property
    def device_info(self):
        """Return the device information."""
        device_info = {
            "identifiers": {(DOMAIN, self._connection_uuid, P1_INSTALL)},
            "manufacturer": "Zonneplan",
            "name": self.coordinator.getConnectionValue(
                self._connection_uuid,
                "p1_installation.0.label",
            ),
        }

        if self._install_index >= 0:
            device_info["identifiers"].add((DOMAIN, self.install_uuid))
            device_info["name"] = self.coordinator.getConnectionValue(
                self._connection_uuid,
                "p1_installation.{install_index}.label".format(
                    install_index=self._install_index
                ),
            )
            device_info["model"] = self.coordinator.getConnectionValue(
                self._connection_uuid,
                "p1_installation.{install_index}.meta.sgn_serial_number".format(
                    install_index=self._install_index
                ),
            )
            device_info["sw_version"] = self.coordinator.getConnectionValue(
                self._connection_uuid,
                "p1_installation.{install_index}.meta.sgn_firmware".format(
                    install_index=self._install_index
                ),
            )

        return device_info
