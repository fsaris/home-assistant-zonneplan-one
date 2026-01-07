"""Zonneplan Sensor."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Mapping
from datetime import datetime
from typing import Any

import homeassistant.util.dt as dt_util
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.const import Platform

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers import entity_registry
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from pytz import timezone

from .const import (
    BATTERY,
    BATTERY_CHARTS,
    BATTERY_CONTROL,
    CHARGE_POINT,
    DOMAIN,
    ELECTRICITY,
    ELECTRICITY_HOME_CONSUMPTION,
    GAS,
    NONE_IS_ZERO,
    NONE_USE_PREVIOUS,
    P1_ELECTRICITY,
    P1_GAS,
    PV_INSTALL,
    SENSOR_TYPES,
    ZonneplanSensorEntityDescription,
)
from .coordinators.account_data_coordinator import (
    ConnectionCoordinators,
    ZonneplanConfigEntry,
)
from .coordinators.battery_charts_data_coordinator import (
    BatteryChartsDataUpdateCoordinator,
)
from .coordinators.battery_control_data_coordinator import (
    BatteryControlDataUpdateCoordinator,
)
from .coordinators.battery_data_coordinator import BatteryDataUpdateCoordinator
from .coordinators.charge_point_data_coordinator import ChargePointDataUpdateCoordinator
from .coordinators.electricity_data_coordinator import ElectricityDataUpdateCoordinator
from .coordinators.electricity_home_consumption_data_coordinator import (
    ElectricityHomeConsumptionDataUpdateCoordinator,
)
from .coordinators.gas_data_coordinator import GasDataUpdateCoordinator
from .coordinators.pv_data_coordinator import PvDataUpdateCoordinator
from .coordinators.summary_data_coordinator import SummaryDataUpdateCoordinator
from .coordinators.zonneplan_data_update_coordinator import (
    ZonneplanDataUpdateCoordinator,
)
from .entity import (
    BatteryEntity,
    ChargePointEntity,
    P1Entity,
    PvEntity,
    base_device_info,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: ZonneplanConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    entities = []

    connection_uuids: list[str] = list(entry.runtime_data.coordinators.keys())

    for uuid, connection in entry.runtime_data.coordinators.items():
        _LOGGER.debug("Setup sensors for connection %s", uuid)

        """Other connection uuids for possible migration of unique_ids"""
        other_connection_uuids = [u for u in connection_uuids if u != uuid]
        _LOGGER.debug("Other connections: %s", other_connection_uuids)

        await add_electricity_sensors(entities, connection, uuid, hass, other_connection_uuids)

        await add_gas_sensors(entities, connection, uuid, hass, other_connection_uuids)

        await add_pv_installation_sensors(entities, connection, uuid)

        await add_p1_electricity_sensors(entities, connection, uuid)

        await add_p1_gas_sensors(entities, connection, uuid)

        if connection.charge_point_installation:
            entities.extend(
                ZonneplanChargePointSensor(
                    uuid,
                    sensor_key,
                    connection.charge_point_installation,
                    0,
                    SENSOR_TYPES[CHARGE_POINT][sensor_key],
                )
                for sensor_key in SENSOR_TYPES[CHARGE_POINT]
            )

        if connection.home_battery_installation:
            entities.extend(
                ZonneplanBatterySensor(
                    uuid,
                    sensor_key,
                    connection.home_battery_installation,
                    0,
                    SENSOR_TYPES[BATTERY][sensor_key],
                )
                for sensor_key in SENSOR_TYPES[BATTERY]
            )

        if connection.battery_control:
            entities.extend(
                ZonneplanBatterySensor(
                    uuid,
                    sensor_key,
                    connection.battery_control,
                    -1,
                    SENSOR_TYPES[BATTERY_CONTROL][sensor_key],
                )
                for sensor_key in SENSOR_TYPES[BATTERY_CONTROL]
            )

        if connection.battery_charts:
            entities.extend(
                ZonneplanBatterySensor(
                    uuid,
                    sensor_key,
                    connection.battery_charts,
                    -1,
                    SENSOR_TYPES[BATTERY_CHARTS][sensor_key],
                )
                for sensor_key in SENSOR_TYPES[BATTERY_CHARTS]
            )

        if connection.electricity_home_consumption:
            entities.extend(
                ZonneplanElectricityHomeConsumptionSensor(
                    uuid,
                    sensor_key,
                    connection.electricity_home_consumption,
                    -1,
                    SENSOR_TYPES[ELECTRICITY_HOME_CONSUMPTION][sensor_key],
                )
                for sensor_key in SENSOR_TYPES[ELECTRICITY_HOME_CONSUMPTION]
            )

    async_add_entities(entities)


async def add_electricity_sensors(entities: list[Any], connection: ConnectionCoordinators, uuid: str, hass: HomeAssistant, other_connection_uuids: list[str]):
    if not connection.electricity:
        return

    entities.extend(
        ZonneplanElectricitySensor(
            uuid,
            sensor_key,
            connection.electricity,
            -1,
            SENSOR_TYPES[ELECTRICITY][sensor_key],
        )
        for sensor_key in SENSOR_TYPES[ELECTRICITY]
    )

    """Migrate old unique ids to new unique ids."""
    for other_connection_uud in other_connection_uuids:
        for sensor_key in SENSOR_TYPES[ELECTRICITY]:
            _migrate_to_new_unique_id(hass, f"{uuid}_{sensor_key}", f"{other_connection_uud}_{sensor_key}")


async def add_gas_sensors(entities: list[Any], connection: ConnectionCoordinators, uuid: str, hass: HomeAssistant, other_connection_uuids: list[str]):
    if not connection.gas:
        return

    entities.extend(
        ZonneplanGasSensor(
            uuid,
            sensor_key,
            connection.gas,
            -1,
            SENSOR_TYPES[GAS][sensor_key],
        )
        for sensor_key in SENSOR_TYPES[GAS]
    )

    """Migrate old unique ids to new unique ids."""
    for other_connection_uud in other_connection_uuids:
        for sensor_key in SENSOR_TYPES[GAS]:
            _migrate_to_new_unique_id(hass, f"{uuid}_{sensor_key}", f"{other_connection_uud}_{sensor_key}")


async def add_p1_gas_sensors(entities: list[Any], connection: ConnectionCoordinators, uuid: str) -> None:
    if not connection.p1_gas:
        return

    entities.extend(
        ZonneplanP1Sensor(
            uuid,
            sensor_key,
            connection.p1_gas,
            -1,
            SENSOR_TYPES[P1_GAS]["totals"][sensor_key],
        )
        for sensor_key in SENSOR_TYPES[P1_GAS]["totals"]
    )
    for install_index in range(len(connection.p1_gas.contracts)):
        entities.extend(
            ZonneplanP1Sensor(
                uuid,
                sensor_key,
                connection.p1_gas,
                install_index,
                SENSOR_TYPES[P1_GAS]["install"][sensor_key],
            )
            for sensor_key in SENSOR_TYPES[P1_GAS]["install"]
        )


async def add_p1_electricity_sensors(entities: list[Any], connection: ConnectionCoordinators, uuid: str) -> None:
    if not connection.p1_electricity:
        return
    entities.extend(
        ZonneplanP1Sensor(
            uuid,
            sensor_key,
            connection.p1_electricity,
            -1,
            SENSOR_TYPES[P1_ELECTRICITY]["totals"][sensor_key],
        )
        for sensor_key in SENSOR_TYPES[P1_ELECTRICITY]["totals"]
    )

    for install_index in range(len(connection.p1_electricity.contracts)):
        entities.extend(
            ZonneplanP1Sensor(
                uuid,
                sensor_key,
                connection.p1_electricity,
                install_index,
                SENSOR_TYPES[P1_ELECTRICITY]["install"][sensor_key],
            )
            for sensor_key in SENSOR_TYPES[P1_ELECTRICITY]["install"]
        )


async def add_pv_installation_sensors(entities: list[Any], connection: ConnectionCoordinators, uuid: str) -> None:
    if not connection.pv_installation:
        return
    entities.extend(
        ZonneplanPvSensor(
            uuid,
            sensor_key,
            connection.pv_installation,
            -1,
            SENSOR_TYPES[PV_INSTALL]["totals"][sensor_key],
        )
        for sensor_key in SENSOR_TYPES[PV_INSTALL]["totals"]
    )

    for install_index in range(len(connection.pv_installation.contracts)):
        entities.extend(
            ZonneplanPvSensor(
                uuid,
                sensor_key,
                connection.pv_installation,
                install_index,
                SENSOR_TYPES[PV_INSTALL]["install"][sensor_key],
            )
            for sensor_key in SENSOR_TYPES[PV_INSTALL]["install"]
        )


def _migrate_to_new_unique_id(hass: HomeAssistant, new_unique_id: str, old_unique_id: str) -> None:
    """Migrate old unique ids to new unique ids."""
    ent_reg = entity_registry.async_get(hass)
    entity_id = ent_reg.async_get_entity_id(Platform.SWITCH, DOMAIN, new_unique_id)
    _LOGGER.debug("Check if the old unique_id [%s] needs to be migrated to the new one [%s]", old_unique_id, new_unique_id)
    if entity_id is not None:
        _LOGGER.debug("New entity already exists")
        return

    old_entity_id = ent_reg.async_get_entity_id(Platform.SWITCH, DOMAIN, old_unique_id)

    if old_entity_id is not None:
        try:
            ent_reg.async_update_entity(entity_id, new_unique_id=new_unique_id)
        except ValueError:
            _LOGGER.warning(
                "Skip migration of id [%s] to [%s] because it already exists",
                old_unique_id,
                new_unique_id,
            )
        else:
            _LOGGER.info(
                "Migrating unique_id from [%s] to [%s]",
                old_unique_id,
                new_unique_id,
            )
    else:
        _LOGGER.debug("No old entity found to migrate")

class ZonneplanSensor(CoordinatorEntity, RestoreEntity, SensorEntity, ABC):
    """Abstract class for a zonneplan sensor."""

    coordinator: ZonneplanDataUpdateCoordinator
    entity_description: ZonneplanSensorEntityDescription
    _install_index: int

    def __init__(
        self,
        connection_uuid: str,
        sensor_key: str,
        coordinator: ZonneplanDataUpdateCoordinator,
        install_index: int,
        description: ZonneplanSensorEntityDescription,
    ) -> None:
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
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return self.install_uuid + "_" + self._sensor_key

    @property
    def available(self) -> bool:
        """Return True if entity and coordinator.data is available."""
        return super().available and self.coordinator.data is not None

    @property
    def last_reset(self) -> datetime | None:
        if not self.entity_description.last_reset_key:
            return None

        value = self.coordinator.get_data_value(
            self.entity_description.last_reset_key.format(install_index=self._install_index),
        )

        if value:
            value = dt_util.parse_datetime(value)

        _LOGGER.debug("Last update %s: %s", self.unique_id, value)

        return value

    @callback
    def _handle_coordinator_update(self) -> None:
        value = self._value_from_coordinator()

        if value is None and self.entity_description.none_value_behaviour == NONE_USE_PREVIOUS:
            return

        if self.skip_update_based_on_daily_update_hour():
            _LOGGER.info(
                "Skip update %s until %sh",
                self.unique_id,
                self.entity_description.daily_update_hour,
            )
            return

        # _LOGGER.debug("Update %s: %s", self.unique_id, value)

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
                "Skipped update %s: %s (update today) > %s (now)",
                self.unique_id,
                update_today,
                dt_util.now(),
            )
            return True

        # Already updated today after daily_update_hour? Then skip
        if dt_util.as_local(state.last_updated) >= update_today:
            _LOGGER.debug(
                "Skipped update %s: %s (last update) >= %s (update today)",
                self.unique_id,
                dt_util.as_local(state.last_updated),
                update_today,
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
            # _LOGGER.debug("Update %s.attribute[%s]: %s", self.unique_id, attribute.label, value)
            attrs[attribute.label] = value

        return attrs

    def _value_from_coordinator(self) -> datetime | str | float | int | None:
        key = (
            self.entity_description.key_lambda()
            if self.entity_description.key_lambda
            else self.entity_description.key.format(install_index=self._install_index)
        )
        # _LOGGER.debug("Key %s: %s", self.unique_id, key)
        raw_value = value = self.coordinator.get_data_value(key)

        if value is None and self.entity_description.none_value_behaviour == NONE_IS_ZERO:
            value = 0

        # Converting value is only needed when value isn't None or 0
        if value:
            if self.entity_description.device_class == SensorDeviceClass.TIMESTAMP:
                if isinstance(value, str):
                    value = dt_util.parse_datetime(value)
                elif value > 100000000000000:  # noqa: PLR2004
                    value = datetime.fromtimestamp(value / 1000000, timezone("Europe/Amsterdam"))
                else:
                    value = datetime.fromtimestamp(value / 1000, timezone("Europe/Amsterdam"))

            if self.entity_description.value_factor:
                value = value * self.entity_description.value_factor

        # _LOGGER.debug("Value %s: %s [%s]", self.unique_id, value, raw_value)

        return value


class ZonneplanElectricitySensor(ZonneplanSensor):
    coordinator: SummaryDataUpdateCoordinator

    def __init__(
        self,
        connection_uuid: str,
        sensor_key: str,
        coordinator: ZonneplanDataUpdateCoordinator,
        install_index: int,
        description: ZonneplanSensorEntityDescription,
    ) -> None:
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
        connection_uuid: str,
        sensor_key: str,
        coordinator: ZonneplanDataUpdateCoordinator,
        install_index: int,
        description: ZonneplanSensorEntityDescription,
    ) -> None:
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
        connection_uuid: str,
        sensor_key: str,
        coordinator: ElectricityHomeConsumptionDataUpdateCoordinator,
        install_index: int,
        description: ZonneplanSensorEntityDescription,
    ) -> None:
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
