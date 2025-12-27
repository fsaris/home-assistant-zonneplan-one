"""Zonneplan Sensor"""
from abc import ABC, abstractmethod
from typing import Optional, Any
from datetime import datetime
from pytz import timezone

from collections.abc import Mapping

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
import logging
from homeassistant.core import (
    callback,
    HomeAssistant
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)

import homeassistant.util.dt as dt_util
from .entity import BatteryEntity, ChargePointEntity, P1Entity, PvEntity

from .coordinators.battery_charts_data_coordinator import BatteryChartsDataUpdateCoordinator
from .coordinators.battery_data_coordinator import BatteryDataUpdateCoordinator
from .coordinators.battery_control_data_coordinator import BatteryControlDataUpdateCoordinator
from .coordinators.charge_point_data_coordinator import ChargePointDataUpdateCoordinator
from .coordinators.electricity_data_coordinator import ElectricityDataUpdateCoordinator
from .coordinators.gas_data_coordinator import GasDataUpdateCoordinator
from .coordinators.pv_data_coordinator import PvDataUpdateCoordinator
from .coordinators.zonneplan_data_update_coordinator import ZonneplanDataUpdateCoordinator

from .const import (
    DOMAIN,
    P1_ELECTRICITY,
    P1_GAS,
    PV_INSTALL,
    NONE_IS_ZERO,
    NONE_USE_PREVIOUS,
    SENSOR_TYPES,
    SUMMARY,
    CHARGE_POINT,
    BATTERY,
    BATTERY_CHARTS,
    BATTERY_CONTROL,
    ELECTRICITY_HOME_CONSUMPTION,
    ZonneplanSensorEntityDescription,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    connections: dict = hass.data[DOMAIN][config_entry.entry_id]["connections"]

    entities = []
    for uuid, connection in connections.items():

        _LOGGER.debug("Setup sensors for connnection %s", uuid)

        if SUMMARY in connection:
            for sensor_key in SENSOR_TYPES[SUMMARY]:
                entities.append(
                    ZonneplanSummarySensor(
                        uuid,
                        sensor_key,
                        connection[SUMMARY],
                        -1,
                        SENSOR_TYPES[SUMMARY][sensor_key],
                    )
                )

        if PV_INSTALL in connection:
            for sensor_key in SENSOR_TYPES[PV_INSTALL]["totals"]:
                entities.append(
                    ZonneplanPvSensor(
                        uuid,
                        sensor_key,
                        connection[PV_INSTALL],
                        -1,
                        SENSOR_TYPES[PV_INSTALL]["totals"][sensor_key],
                    )
                )
            for install_index in range(len(connection[PV_INSTALL].contracts)):
                for sensor_key in SENSOR_TYPES[PV_INSTALL]["install"]:
                    entities.append(
                        ZonneplanPvSensor(
                            uuid,
                            sensor_key,
                            connection[PV_INSTALL],
                            install_index,
                            SENSOR_TYPES[PV_INSTALL]["install"][sensor_key],
                        )
                    )

        if P1_ELECTRICITY in connection:
            for sensor_key in SENSOR_TYPES[P1_ELECTRICITY]["totals"]:
                entities.append(
                    ZonneplanP1Sensor(
                        uuid,
                        sensor_key,
                        connection[P1_ELECTRICITY],
                        -1,
                        SENSOR_TYPES[P1_ELECTRICITY]["totals"][sensor_key],
                    )
                )
            for install_index in range(len(connection[P1_ELECTRICITY].contracts)):
                for sensor_key in SENSOR_TYPES[P1_ELECTRICITY]["install"]:
                    entities.append(
                        ZonneplanP1Sensor(
                            uuid,
                            sensor_key,
                            connection[P1_ELECTRICITY],
                            install_index,
                            SENSOR_TYPES[P1_ELECTRICITY]["install"][sensor_key],
                        )
                    )

        if P1_GAS in connection:
            for sensor_key in SENSOR_TYPES[P1_GAS]["totals"]:
                entities.append(
                    ZonneplanP1Sensor(
                        uuid,
                        sensor_key,
                        connection[P1_GAS],
                        -1,
                        SENSOR_TYPES[P1_GAS]["totals"][sensor_key],
                    )
                )
            for install_index in range(len(connection[P1_GAS].contracts)):
                for sensor_key in SENSOR_TYPES[P1_GAS]["install"]:
                    entities.append(
                        ZonneplanP1Sensor(
                            uuid,
                            sensor_key,
                            connection[P1_GAS],
                            install_index,
                            SENSOR_TYPES[P1_GAS]["install"][sensor_key],
                        )
                    )

        if CHARGE_POINT in connection:
            for sensor_key in SENSOR_TYPES[CHARGE_POINT]:
                entities.append(
                    ZonneplanChargePointSensor(
                        uuid,
                        sensor_key,
                        connection[CHARGE_POINT],
                        0,
                        SENSOR_TYPES[CHARGE_POINT][sensor_key],
                    )
                )

        if BATTERY in connection:
            for sensor_key in SENSOR_TYPES[BATTERY]:
                entities.append(
                    ZonneplanBatterySensor(
                        uuid,
                        sensor_key,
                        connection[BATTERY],
                        0,
                        SENSOR_TYPES[BATTERY][sensor_key],
                    )
                )

        if BATTERY_CONTROL in connection:
            for sensor_key in SENSOR_TYPES[BATTERY_CONTROL]:
                entities.append(
                    ZonneplanBatterySensor(
                        uuid,
                        sensor_key,
                        connection[BATTERY_CONTROL],
                        -1,
                        SENSOR_TYPES[BATTERY_CONTROL][sensor_key],
                    )
                )

        if BATTERY_CHARTS in connection:
            for sensor_key in SENSOR_TYPES[BATTERY_CHARTS]:
                entities.append(
                    ZonneplanBatterySensor(
                        uuid,
                        sensor_key,
                        connection[BATTERY_CHARTS],
                        -1,
                        SENSOR_TYPES[BATTERY_CHARTS][sensor_key],
                    )
                )

        if ELECTRICITY_HOME_CONSUMPTION in connection:
            for sensor_key in SENSOR_TYPES[ELECTRICITY_HOME_CONSUMPTION]:
                entities.append(
                    ZonneplanBatterySensor(
                        uuid,
                        sensor_key,
                        connection[ELECTRICITY_HOME_CONSUMPTION],
                        -1,
                        SENSOR_TYPES[ELECTRICITY_HOME_CONSUMPTION][sensor_key],
                    )
                )

    async_add_entities(entities)


class ZonneplanSensor(CoordinatorEntity, RestoreEntity, SensorEntity, ABC):
    """Abstract class for a zonneplan sensor."""

    coordinator: ZonneplanDataUpdateCoordinator
    entity_description: ZonneplanSensorEntityDescription
    _install_index: int

    def __init__(
            self,
            connection_uuid,
            sensor_key: str,
            coordinator: ZonneplanDataUpdateCoordinator,
            install_index: int,
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
    @abstractmethod
    def install_uuid(self) -> str:
        pass

    @property
    def unique_id(self) -> Optional[str]:
        """Return a unique ID."""
        return self.install_uuid + "_" + self._sensor_key

    @property
    def available(self) -> bool:
        """Return True if entity and coordinator.data is available."""
        return (
                super().available
                and self.coordinator.data is not None
        )

    @property
    def last_reset(self) -> datetime | None:

        if not self.entity_description.last_reset_key:
            return None

        value = self.coordinator.get_data_value(
            self.entity_description.last_reset_key.format(install_index=self._install_index),
        )

        if value:
            value = dt_util.parse_datetime(value)

        _LOGGER.debug(f"Last update {self.unique_id}: {value}")

        return value

    @callback
    def _handle_coordinator_update(self) -> None:
        value = self._value_from_coordinator()

        if (
                value is None
                and self.entity_description.none_value_behaviour == NONE_USE_PREVIOUS
        ):
            return

        if self.skip_update_based_on_daily_update_hour():
            _LOGGER.info(
                f"Skip update {self.unique_id} until {self.entity_description.daily_update_hour}h"
            )
            return

        _LOGGER.debug(f"Update {self.unique_id}: {value}")

        self._attr_native_value = value
        self.async_write_ha_state()

    def skip_update_based_on_daily_update_hour(self) -> bool:
        if self.entity_description.daily_update_hour is None:
            return False

        # No state? then we update
        if not (state := self.hass.states.get(self.entity_id)):
            return False

        # No last update value? then we update
        if not state.last_updated:
            return False

        update_today = dt_util.now().replace(
            hour=self.entity_description.daily_update_hour,
            minute=0,
            second=0,
            microsecond=0,
        )

        # Is it time already to update the value today? No then we skip
        if update_today > dt_util.now():
            _LOGGER.debug(
                f"Skipped update {self.unique_id}: {update_today} (update today) > {dt_util.now()} (now)"
            )
            return True

        # Already updated today after daily_update_hour? Then skip
        if dt_util.as_local(state.last_updated) >= update_today:
            _LOGGER.debug(
                f"Skipped update {self.unique_id}: {dt_util.as_local(state.last_updated)} (last update) >= {update_today} (update today)"
            )
            return True

        return False

    @property
    def extra_state_attributes(self) -> Mapping[str, Any] | None:

        if not self.entity_description.attributes:
            return None

        attrs = {}
        for attribute in self.entity_description.attributes:
            value = self.coordinator.get_data_value(
                attribute.key.format(install_index=self._install_index),
            )
            _LOGGER.debug(f'Update {self.unique_id}.attribute[{attribute.label}]: {value}')
            attrs[attribute.label] = value

        return attrs

    def _value_from_coordinator(self):
        raw_value = value = self.coordinator.get_data_value(
            self.entity_description.key.format(install_index=self._install_index),
        )

        if (
                value is None
                and self.entity_description.none_value_behaviour == NONE_IS_ZERO
        ):
            value = 0

        # Converting value is only needed when value isn't None or 0
        if value:
            if self.entity_description.device_class == SensorDeviceClass.TIMESTAMP:
                if isinstance(value, str):
                    value = dt_util.parse_datetime(value)
                elif value > 100000000000000:
                    value = datetime.fromtimestamp(value / 1000000, timezone('Europe/Amsterdam'))
                else:
                    value = datetime.fromtimestamp(value / 1000, timezone('Europe/Amsterdam'))

            if self.entity_description.value_factor:
                value = value * self.entity_description.value_factor

        _LOGGER.debug(f"Value {self.unique_id}: {value} [{raw_value}]")

        return value


class ZonneplanSummarySensor(ZonneplanSensor):
    @property
    def install_uuid(self) -> str:
        """Return install ID."""
        return self._connection_uuid

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device information."""
        return {
            "identifiers": {(DOMAIN, self._connection_uuid)},
            "manufacturer": "Zonneplan",
            "name": "Zonneplan",
        }


class ZonneplanPvSensor(PvEntity, ZonneplanSensor):
    coordinator: PvDataUpdateCoordinator


class ZonneplanP1Sensor(P1Entity, ZonneplanSensor):
    coordinator: ElectricityDataUpdateCoordinator | GasDataUpdateCoordinator


class ZonneplanChargePointSensor(ChargePointEntity, ZonneplanSensor):
    coordinator: ChargePointDataUpdateCoordinator


class ZonneplanBatterySensor(BatteryEntity, ZonneplanSensor):
    coordinator: BatteryDataUpdateCoordinator | BatteryChartsDataUpdateCoordinator | BatteryControlDataUpdateCoordinator
