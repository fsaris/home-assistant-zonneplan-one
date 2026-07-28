"""Zonneplan button."""

import logging

from homeassistant.components.button import (
    ButtonEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import (
    BUTTON_TYPES,
    CHARGE_POINT,
    ZonneplanButtonEntityDescription,
)
from .coordinators.account_data_coordinator import ZonneplanConfigEntry
from .coordinators.charge_point_data_coordinator import ChargePointDataUpdateCoordinator
from .entity import ChargePointEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: ZonneplanConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    entities = []
    for uuid, connection in entry.runtime_data.coordinators.items():
        if connection.charge_point_installation:
            _LOGGER.debug("Setup buttons for connnection %s", uuid)

            entities.extend(
                ZonneplanChargePointButton(
                    uuid,
                    sensor_key,
                    connection.charge_point_installation,
                    0,
                    BUTTON_TYPES[CHARGE_POINT][sensor_key],
                )
                for sensor_key in BUTTON_TYPES[CHARGE_POINT]
            )

    async_add_entities(entities)


class ZonneplanChargePointButton(ChargePointEntity, CoordinatorEntity, ButtonEntity):
    """Zonneplan Charge Point Button."""

    coordinator: ChargePointDataUpdateCoordinator
    entity_description: ZonneplanButtonEntityDescription
    _connection_uuid: str
    _button_key: str
    _install_index: int

    def __init__(
        self,
        connection_uuid: str,
        button_key: str,
        coordinator: ChargePointDataUpdateCoordinator,
        install_index: int,
        description: ZonneplanButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._connection_uuid = connection_uuid
        self._button_key = button_key
        self._install_index = install_index
        self.entity_description = description

    @property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return self.install_uuid + "_" + self._button_key

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.data or not self.coordinator.last_update_success:
            return False

        state = self.coordinator.get_data_value("state")

        if not state or not state["connectivity_state"] or "processing" in state:
            return False

        available = {
            "start": lambda: state["state"] == "VehicleDetected",
            "stop": lambda: state["state"] == "Charging",
            "apply_dynamic_charge": lambda: (
                self.coordinator.has_pending_dynamic_charge_changes() and self.coordinator.dynamic_charge_params_are_valid()
            ),
            "discard_dynamic_charge": self.coordinator.has_pending_dynamic_charge_changes,
            "reset_dynamic_charge": self.coordinator.has_dynamic_charge_schedule,
        }.get(self._button_key)

        return bool(available and available())

    async def async_press(self) -> None:
        """Handle the button press."""
        if self._button_key == "start":
            await self.coordinator.async_start_charge()
        elif self._button_key == "stop":
            await self.coordinator.async_stop_charge()
        elif self._button_key == "apply_dynamic_charge":
            await self.coordinator.async_apply_dynamic_charge()
        elif self._button_key == "discard_dynamic_charge":
            self.coordinator.discard_dynamic_charge_changes()
        elif self._button_key == "reset_dynamic_charge":
            await self.coordinator.async_reset_dynamic_charge()
        else:
            _LOGGER.warning("Unknown button action for %s", self._button_key)
