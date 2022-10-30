"""Zonneplan Sensor"""
from typing import Optional

from voluptuous.validators import Number
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
import logging
from homeassistant.core import callback
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)

import homeassistant.util.dt as dt_util

from .coordinator import ZonneplanUpdateCoordinator
from .const import (
    DOMAIN,
    P1_INSTALL,
    PV_INSTALL,
    NONE_IS_ZERO,
    NONE_USE_PREVIOUS,
    SENSOR_TYPES,
    SUMMARY,
    ZonneplanSensorEntityDescription,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistantType, config_entry, async_add_entities):

    coordinator: ZonneplanUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    entities = []
    for uuid, connection in coordinator.connections.items():
        pv_installations = coordinator.getConnectionValue(uuid, PV_INSTALL)
        p1_installations = coordinator.getConnectionValue(uuid, P1_INSTALL)
        summary = coordinator.getConnectionValue(uuid, SUMMARY)

        _LOGGER.debug("Setup sensors for connnection %s", uuid)

        if summary:
            for sensor_key in SENSOR_TYPES[SUMMARY]:
                entities.append(
                    ZonneplanSensor(
                        uuid,
                        sensor_key,
                        coordinator,
                        None,
                        SENSOR_TYPES[SUMMARY][sensor_key],
                    )
                )

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

    coordinator: ZonneplanUpdateCoordinator

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

        self._attr_native_value = self._value_from_coordinator()

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

    @property
    def device_info(self):
        """Return the device information."""
        return {
            "identifiers": {(DOMAIN, self._connection_uuid, SUMMARY)},
            "manufacturer": "Zonneplan",
            "name": "Usage",
        }

    @callback
    def _handle_coordinator_update(self) -> None:
        value = self._value_from_coordinator()

        if value is None and self.entity_description.none_value_behaviour == NONE_USE_PREVIOUS:
            return

        self._attr_native_value = value
        self.async_write_ha_state()

    def _value_from_coordinator(self):
        value = self.coordinator.getConnectionValue(
            self._connection_uuid,
            self.entity_description.key.format(install_index=self._install_index),
        )
        if value is None and self.entity_description.none_value_behaviour == NONE_IS_ZERO:
            value = 0

        # Converting value is only needed when value isn't None or 0
        if value:
            if self.entity_description.device_class == SensorDeviceClass.TIMESTAMP:
                value = dt_util.parse_datetime(value)

            if self.entity_description.value_factor:
                value = value * self.entity_description.value_factor

        return value

class ZonneplanPvSensor(ZonneplanSensor):
    @property
    def install_uuid(self) -> str:
        """Return install ID."""
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
                str(
                    self.coordinator.getConnectionValue(
                        self._connection_uuid,
                        "pv_installation.{install_index}.meta.module_firmware_version".format(
                            install_index=self._install_index
                        ),
                    )
                    or "unknown"
                )
                + " - "
                + str(
                    self.coordinator.getConnectionValue(
                        self._connection_uuid,
                        "pv_installation.{install_index}.meta.inverter_firmware_version".format(
                            install_index=self._install_index
                        ),
                    )
                    or "unknown"
                )
            )

        return device_info


class ZonneplanP1Sensor(ZonneplanSensor):
    @property
    def install_uuid(self) -> str:
        """Return install ID."""
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
