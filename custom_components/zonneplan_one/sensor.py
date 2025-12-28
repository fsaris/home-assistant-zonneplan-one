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

from .coordinators.account_data_coordinator import ZonneplanConfigEntry
from .coordinators.battery_charts_data_coordinator import BatteryChartsDataUpdateCoordinator
from .coordinators.battery_data_coordinator import BatteryDataUpdateCoordinator
from .coordinators.battery_control_data_coordinator import BatteryControlDataUpdateCoordinator
from .coordinators.charge_point_data_coordinator import ChargePointDataUpdateCoordinator
from .coordinators.electricity_data_coordinator import ElectricityDataUpdateCoordinator
from .coordinators.electricity_home_consumption_data_coordinator import ElectricityHomeConsumptionDataUpdateCoordinator
from .coordinators.gas_data_coordinator import GasDataUpdateCoordinator
from .coordinators.pv_data_coordinator import PvDataUpdateCoordinator
from .coordinators.summary_data_coordinator import SummaryDataUpdateCoordinator
from .coordinators.zonneplan_data_update_coordinator import ZonneplanDataUpdateCoordinator
from .const import (
    DOMAIN,
    P1_ELECTRICITY,
    P1_GAS,
    PV_INSTALL,
    NONE_IS_ZERO,
    NONE_USE_PREVIOUS,
    SENSOR_TYPES,
    ELECTRICITY,
    GAS,
    CHARGE_POINT,
    BATTERY,
    BATTERY_CHARTS,
    BATTERY_CONTROL,
    ELECTRICITY_HOME_CONSUMPTION,
    ZonneplanSensorEntityDescription,
)
from .entity import BatteryEntity, ChargePointEntity, P1Entity, PvEntity, base_device_info

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ZonneplanConfigEntry, async_add_entities):
    entities = []
    for uuid, connection in entry.runtime_data.coordinators.items():

        _LOGGER.debug("Setup sensors for connection %s", uuid)

        if connection.electricity:
            for sensor_key in SENSOR_TYPES[ELECTRICITY]:
                entities.append(
                    ZonneplanElectricitySensor(
                        uuid,
                        sensor_key,
                        connection.electricity,
                        -1,
                        SENSOR_TYPES[ELECTRICITY][sensor_key],
                    )
                )

        if connection.gas:
            for sensor_key in SENSOR_TYPES[GAS]:
                entities.append(
                    ZonneplanGasSensor(
                        uuid,
                        sensor_key,
                        connection.gas,
                        -1,
                        SENSOR_TYPES[GAS][sensor_key],
                    )
                )

        if connection.pv_installation:
            for sensor_key in SENSOR_TYPES[PV_INSTALL]["totals"]:
                entities.append(
                    ZonneplanPvSensor(
                        uuid,
                        sensor_key,
                        connection.pv_installation,
                        -1,
                        SENSOR_TYPES[PV_INSTALL]["totals"][sensor_key],
                    )
                )
            for install_index in range(len(connection.pv_installation.contracts)):
                for sensor_key in SENSOR_TYPES[PV_INSTALL]["install"]:
                    entities.append(
                        ZonneplanPvSensor(
                            uuid,
                            sensor_key,
                            connection.pv_installation,
                            install_index,
                            SENSOR_TYPES[PV_INSTALL]["install"][sensor_key],
                        )
                    )

        if connection.p1_electricity:
            for sensor_key in SENSOR_TYPES[P1_ELECTRICITY]["totals"]:
                entities.append(
                    ZonneplanP1Sensor(
                        uuid,
                        sensor_key,
                        connection.p1_electricity,
                        -1,
                        SENSOR_TYPES[P1_ELECTRICITY]["totals"][sensor_key],
                    )
                )
            for install_index in range(len(connection.p1_electricity.contracts)):
                for sensor_key in SENSOR_TYPES[P1_ELECTRICITY]["install"]:
                    entities.append(
                        ZonneplanP1Sensor(
                            uuid,
                            sensor_key,
                            connection.p1_electricity,
                            install_index,
                            SENSOR_TYPES[P1_ELECTRICITY]["install"][sensor_key],
                        )
                    )

        if connection.p1_gas:
            for sensor_key in SENSOR_TYPES[P1_GAS]["totals"]:
                entities.append(
                    ZonneplanP1Sensor(
                        uuid,
                        sensor_key,
                        connection.p1_gas,
                        -1,
                        SENSOR_TYPES[P1_GAS]["totals"][sensor_key],
                    )
                )
            for install_index in range(len(connection.p1_gas.contracts)):
                for sensor_key in SENSOR_TYPES[P1_GAS]["install"]:
                    entities.append(
                        ZonneplanP1Sensor(
                            uuid,
                            sensor_key,
                            connection.p1_gas,
                            install_index,
                            SENSOR_TYPES[P1_GAS]["install"][sensor_key],
                        )
                    )

        if connection.charge_point_installation:
            for sensor_key in SENSOR_TYPES[CHARGE_POINT]:
                entities.append(
                    ZonneplanChargePointSensor(
                        uuid,
                        sensor_key,
                        connection.charge_point_installation,
                        0,
                        SENSOR_TYPES[CHARGE_POINT][sensor_key],
                    )
                )

        if connection.home_battery_installation:
            for sensor_key in SENSOR_TYPES[BATTERY]:
                entities.append(
                    ZonneplanBatterySensor(
                        uuid,
                        sensor_key,
                        connection.home_battery_installation,
                        0,
                        SENSOR_TYPES[BATTERY][sensor_key],
                    )
                )

        if connection.battery_control:
            for sensor_key in SENSOR_TYPES[BATTERY_CONTROL]:
                entities.append(
                    ZonneplanBatterySensor(
                        uuid,
                        sensor_key,
                        connection.battery_control,
                        -1,
                        SENSOR_TYPES[BATTERY_CONTROL][sensor_key],
                    )
                )

        if connection.battery_charts:
            for sensor_key in SENSOR_TYPES[BATTERY_CHARTS]:
                entities.append(
                    ZonneplanBatterySensor(
                        uuid,
                        sensor_key,
                        connection.battery_charts,
                        -1,
                        SENSOR_TYPES[BATTERY_CHARTS][sensor_key],
                    )
                )

        if connection.electricity_home_consumption:
            for sensor_key in SENSOR_TYPES[ELECTRICITY_HOME_CONSUMPTION]:
                entities.append(
                    ZonneplanElectricityHomeConsumptionSensor(
                        uuid,
                        sensor_key,
                        connection.electricity_home_consumption,
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
        if not state.last_updated or not self.native_value:
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


class ZonneplanElectricitySensor(ZonneplanSensor):
    coordinator: SummaryDataUpdateCoordinator

    def __init__(
            self,
            connection_uuid,
            sensor_key: str,
            coordinator: ZonneplanDataUpdateCoordinator,
            install_index: int,
            description: ZonneplanSensorEntityDescription,
    ):
        """Initialize the sensor."""
        super().__init__(connection_uuid, sensor_key, coordinator, install_index, description)

        self.entity_id = f"sensor.zonneplan_{sensor_key}"

    @property
    def install_uuid(self) -> str:
        """Return install ID."""
        return self._connection_uuid

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device information."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.contract["uuid"])},
            "via_device": (DOMAIN, self.coordinator.address_uuid),
            "manufacturer": "Zonneplan",
            "name": self.coordinator.contract["label"],
        }


class ZonneplanGasSensor(ZonneplanSensor):
    coordinator: SummaryDataUpdateCoordinator

    def __init__(
            self,
            connection_uuid,
            sensor_key: str,
            coordinator: ZonneplanDataUpdateCoordinator,
            install_index: int,
            description: ZonneplanSensorEntityDescription,
    ):
        """Initialize the sensor."""
        super().__init__(connection_uuid, sensor_key, coordinator, install_index, description)

        self.entity_id = f"sensor.zonneplan_{sensor_key}"

    @property
    def install_uuid(self) -> str:
        """Return install ID."""
        return self._connection_uuid

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device information."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.contract["uuid"])},
            "via_device": (DOMAIN, self.coordinator.address_uuid),
            "manufacturer": "Zonneplan",
            "name": self.coordinator.contract["label"],
        }


class ZonneplanElectricityHomeConsumptionSensor(ZonneplanSensor):
    coordinator: ElectricityHomeConsumptionDataUpdateCoordinator

    def __init__(
            self,
            connection_uuid,
            sensor_key: str,
            coordinator: ElectricityHomeConsumptionDataUpdateCoordinator,
            install_index: int,
            description: ZonneplanSensorEntityDescription,
    ):
        """Initialize the sensor."""
        super().__init__(connection_uuid, sensor_key, coordinator, install_index, description)

        self.entity_id = f"sensor.zonneplan_{sensor_key}"

    @property
    def install_uuid(self) -> str:
        """Return install ID."""
        return self._connection_uuid

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device information."""
        return base_device_info(self.coordinator.address_uuid)


class ZonneplanPvSensor(PvEntity, ZonneplanSensor):
    coordinator: PvDataUpdateCoordinator


class ZonneplanP1Sensor(P1Entity, ZonneplanSensor):
    coordinator: ElectricityDataUpdateCoordinator | GasDataUpdateCoordinator


class ZonneplanChargePointSensor(ChargePointEntity, ZonneplanSensor):
    coordinator: ChargePointDataUpdateCoordinator


class ZonneplanBatterySensor(BatteryEntity, ZonneplanSensor):
    coordinator: BatteryDataUpdateCoordinator | BatteryChartsDataUpdateCoordinator | BatteryControlDataUpdateCoordinator
