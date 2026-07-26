"""Zonneplan select."""

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BATTERY_CONTROL,
    CHARGE_POINT,
    SELECT_TYPES,
    ZonneplanNumberEntityDescription,
    ZonneplanSelectEntityDescription,
)
from .coordinators.account_data_coordinator import ZonneplanConfigEntry
from .coordinators.battery_control_data_coordinator import (
    BatteryControlDataUpdateCoordinator,
)
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
            _LOGGER.debug("Setup battery control select entities for connection %s", uuid)

            entities.extend(
                ZonneplanBatteryControlModeSelect(
                    uuid,
                    _key,
                    connection.battery_control,
                    0,
                    SELECT_TYPES[BATTERY_CONTROL][_key],
                )
                for _key in SELECT_TYPES[BATTERY_CONTROL]
            )

        if connection.charge_point_installation:
            _LOGGER.debug("Setup charge point select entities for connection %s", uuid)

            entities.extend(
                ZonneplanChargePointVehicleSelect(
                    uuid,
                    _key,
                    connection.charge_point_installation,
                    0,
                    SELECT_TYPES[CHARGE_POINT][_key],
                )
                for _key in SELECT_TYPES[CHARGE_POINT]
            )

    async_add_entities(entities)


class ZonneplanBatteryControlModeSelect(BatteryEntity, CoordinatorEntity, SelectEntity):
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
        """Return True if entity and coordinator.data is available."""
        return super().available and self.coordinator.data is not None

    @property
    def options(self) -> list[str]:
        if not self.available:
            return []

        modes = self.coordinator.get_data_value("battery_control_mode.modes") or {}
        return [key for key, value in modes.items() if value.get("available")]

    @property
    def current_option(self) -> str:
        return self.coordinator.get_data_value(self.entity_description.key)

    async def async_select_option(self, option: str) -> None:
        if option == "self_consumption":
            await self.coordinator.async_enable_self_consumption()
        elif option == "dynamic_charging":
            await self.coordinator.async_enable_dynamic_charging()
        elif option == "home_optimization":
            await self.coordinator.async_enable_home_optimization()
        else:
            _LOGGER.warning("Unknown action for %s", option)


class ZonneplanChargePointVehicleSelect(ChargePointEntity, CoordinatorEntity, RestoreEntity, SelectEntity):
    """Select which vehicle's specs (battery capacity / consumption) are used to size the desired-kilometers number."""

    coordinator: ChargePointDataUpdateCoordinator
    _connection_uuid: str
    _install_index: int
    _key: str
    entity_description: ZonneplanSelectEntityDescription

    def __init__(
        self,
        connection_uuid: str,
        _key: str,
        coordinator: ChargePointDataUpdateCoordinator,
        install_index: int,
        description: ZonneplanSelectEntityDescription,
    ) -> None:
        """Initialize the select."""
        super().__init__(coordinator)
        self._connection_uuid = connection_uuid
        self._install_index = install_index
        self._key = _key
        self.entity_description = description
        self._restored_option: str | None = None

    @property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return self.install_uuid + "_" + self._key

    @property
    def available(self) -> bool:
        """Return True if entity and coordinator.vehicles is available."""
        return super().available and bool(self.coordinator.vehicles)

    @property
    def options(self) -> list[str]:
        return [vehicle["label"] for vehicle in self.coordinator.vehicles]

    @property
    def current_option(self) -> str | None:
        self._ensure_default_selection()
        vehicle = self.coordinator.get_vehicle(self.coordinator.selected_vehicle_uuid)
        return vehicle["label"] if vehicle else None

    def _ensure_default_selection(self) -> None:
        """Pick a vehicle when nothing is selected yet: the restored one if it still exists, else the first available."""
        if self.coordinator.selected_vehicle_uuid is not None or not self.coordinator.vehicles:
            return

        vehicle = next(
            (v for v in self.coordinator.vehicles if v.get("label") == self._restored_option),
            self.coordinator.vehicles[0],
        )
        self.coordinator.selected_vehicle_uuid = vehicle["uuid"]

    async def async_added_to_hass(self) -> None:
        """Remember the previously selected vehicle, resolved once the coordinator's vehicle list is loaded."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._restored_option = last_state.state

        self._ensure_default_selection()

    async def async_select_option(self, option: str) -> None:
        vehicle = next((v for v in self.coordinator.vehicles if v.get("label") == option), None)
        if not vehicle:
            _LOGGER.warning("Unknown vehicle for %s", option)
            return

        self.coordinator.selected_vehicle_uuid = vehicle["uuid"]
        self.coordinator.async_update_listeners()
