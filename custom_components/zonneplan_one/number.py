"""Zonneplan number."""

import logging

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BATTERY,
    BATTERY_CONTROL,
    CHARGE_POINT,
    NUMBER_TYPES,
    ZonneplanNumberEntityDescription,
)
from .coordinators.account_data_coordinator import ZonneplanConfigEntry
from .coordinators.battery_control_data_coordinator import BatteryControlDataUpdateCoordinator
from .coordinators.battery_data_coordinator import BatteryDataUpdateCoordinator
from .coordinators.charge_point_data_coordinator import ChargePointDataUpdateCoordinator
from .entity import BatteryEntity, ChargePointEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: ZonneplanConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    entities = []
    for uuid, connection in entry.runtime_data.coordinators.items():
        if connection.battery_control:
            _LOGGER.debug("Setup battery control number entities for connection %s", uuid)

            entities.extend(
                ZonneplanBatteryControlNumber(
                    uuid,
                    sensor_key,
                    connection.battery_control,
                    0,
                    NUMBER_TYPES[BATTERY_CONTROL][sensor_key],
                )
                for sensor_key in NUMBER_TYPES[BATTERY_CONTROL]
            )

        if connection.home_battery_installation:
            _LOGGER.debug("Setup battery number entities for connection %s", uuid)

            entities.extend(
                ZonneplanReserveDischargeNumber(
                    uuid,
                    sensor_key,
                    connection.home_battery_installation,
                    0,
                    NUMBER_TYPES[BATTERY][sensor_key],
                )
                for sensor_key in NUMBER_TYPES[BATTERY]
            )

        if connection.charge_point_installation:
            _LOGGER.debug("Setup charge point number entities for connection %s", uuid)

            entities.extend(
                ZonneplanDynamicChargeDesiredPercentageNumber(
                    uuid,
                    sensor_key,
                    connection.charge_point_installation,
                    0,
                    NUMBER_TYPES[CHARGE_POINT][sensor_key],
                )
                for sensor_key in NUMBER_TYPES[CHARGE_POINT]
            )

    async_add_entities(entities)


class ZonneplanBatteryControlNumber(BatteryEntity, CoordinatorEntity, NumberEntity):
    coordinator: BatteryControlDataUpdateCoordinator
    _connection_uuid: str
    _install_index: int
    _key: str
    entity_description: ZonneplanNumberEntityDescription

    def __init__(
        self,
        connection_uuid: str,
        _key: str,
        coordinator: BatteryControlDataUpdateCoordinator,
        install_index: int,
        description: ZonneplanNumberEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._connection_uuid = connection_uuid
        self._install_index = install_index
        self._key = _key
        self.entity_description = description

    @property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return self.install_uuid + "_" + self._key

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.data or not self.coordinator.last_update_success:
            return False

        control_mode = self.coordinator.get_data_value("battery_control_mode.control_mode")

        return control_mode == "home_optimization"

    @property
    def native_min_value(self) -> float:
        return (
            self.coordinator.get_data_value(
                self.entity_description.key.format(install_index=self._install_index).replace("_watts", "_limits.min_watts"),
            )
            or 0
        )

    @property
    def native_max_value(self) -> float:
        return (
            self.coordinator.get_data_value(
                self.entity_description.key.format(install_index=self._install_index).replace("_watts", "_limits.max_watts"),
            )
            or 2000
        )

    @property
    def native_value(self) -> float:
        return self.coordinator.get_data_value(
            self.entity_description.key.format(install_index=self._install_index),
        )

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.set_data_value(
            self.entity_description.key.format(install_index=self._install_index),
            int(value),
        )

        await self.coordinator.async_enable_home_optimization()


class ZonneplanReserveDischargeNumber(BatteryEntity, CoordinatorEntity, NumberEntity):
    coordinator: BatteryDataUpdateCoordinator
    _connection_uuid: str
    _install_index: int
    _key: str
    entity_description: ZonneplanNumberEntityDescription

    def __init__(
        self,
        connection_uuid: str,
        _key: str,
        coordinator: BatteryDataUpdateCoordinator,
        install_index: int,
        description: ZonneplanNumberEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._connection_uuid = connection_uuid
        self._install_index = install_index
        self._key = _key
        self.entity_description = description

    @property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return self.install_uuid + "_" + self._key

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.data or not self.coordinator.last_update_success:
            return False

        backup_power_capable_key = "contracts.{install_index}.meta.backup_power_capable"

        return bool(self.coordinator.get_data_value(backup_power_capable_key.format(install_index=self._install_index)))

    @property
    def native_min_value(self) -> float:
        return 0

    @property
    def native_max_value(self) -> float:
        return float(
            self.coordinator.get_data_value(
                f"contracts.{self._install_index}.meta.backup_power_usable_capacity_wh",
            )
            or 3000
        )

    @property
    def native_value(self) -> float:
        return self.coordinator.get_data_value(
            self.entity_description.key.format(install_index=self._install_index),
        )

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.set_data_value(
            self.entity_description.key.format(install_index=self._install_index),
            int(value),
        )

        await self.coordinator.async_set_reserve_discharge(int(value))


class ZonneplanDynamicChargeDesiredPercentageNumber(ChargePointEntity, CoordinatorEntity, NumberEntity):
    coordinator: ChargePointDataUpdateCoordinator
    _connection_uuid: str
    _install_index: int
    _key: str
    entity_description: ZonneplanNumberEntityDescription

    def __init__(
        self,
        connection_uuid: str,
        _key: str,
        coordinator: ChargePointDataUpdateCoordinator,
        install_index: int,
        description: ZonneplanNumberEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._connection_uuid = connection_uuid
        self._install_index = install_index
        self._key = _key
        self.entity_description = description

    @property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return self.install_uuid + "_" + self._key

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.data or not self.coordinator.last_update_success:
            return False

        state = self.coordinator.get_data_value("state")

        if not state or not state["connectivity_state"]:
            return False

        if "processing" in state:
            return False

        return True

    @property
    def native_value(self) -> float:
        value = self.coordinator.get_data_value(
            self.entity_description.key.format(install_index=self._install_index),
        )
        if not value or not isinstance(value, int):
            value = 0

        return value * (self.entity_description.value_factor or 1)

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.set_data_value(
            self.entity_description.key.format(install_index=self._install_index),
            int(value / (self.entity_description.value_factor or 1)),
        )

        await self.coordinator.async_dynamic_charge()


class ZonneplanDynamicChargeDesiredKilometers(ChargePointEntity, CoordinatorEntity, NumberEntity):
    coordinator: ChargePointDataUpdateCoordinator
    _connection_uuid: str
    _install_index: int
    _key: str
    entity_description: ZonneplanNumberEntityDescription

    def __init__(
        self,
        connection_uuid: str,
        _key: str,
        coordinator: ChargePointDataUpdateCoordinator,
        install_index: int,
        description: ZonneplanNumberEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._connection_uuid = connection_uuid
        self._install_index = install_index
        self._key = _key
        self.entity_description = description

    @property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return self.install_uuid + "_" + self._key

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.data or not self.coordinator.last_update_success:
            return False

        state = self.coordinator.get_data_value("state")

        if not state or not state["connectivity_state"]:
            return False

        if "processing" in state:
            return False

        return True

    @property
    def native_value(self) -> float:
        value = self.coordinator.get_data_value(
            self.entity_description.key.format(install_index=self._install_index),
        )
        if not value or not isinstance(value, int):
            value = 0

        return value * (self.entity_description.value_factor or 1)

    async def async_set_native_value(self, value: float) -> None:
        self.coordinator.set_data_value(
            self.entity_description.key.format(install_index=self._install_index),
            int(value / (self.entity_description.value_factor or 1)),
        )

        await self.coordinator.async_dynamic_charge()
