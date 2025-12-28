"""Zonneplan button"""
from typing import Optional

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
import logging
from homeassistant.core import (
    HomeAssistant
)
from homeassistant.components.button import (
    ButtonEntity,
)

from .coordinators.account_data_coordinator import ZonneplanConfigEntry
from .coordinators.charge_point_data_coordinator import ChargePointDataUpdateCoordinator
from .const import (
    CHARGE_POINT,
    BUTTON_TYPES,
    ZonneplanButtonEntityDescription,
)
from .entity import ChargePointEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ZonneplanConfigEntry, async_add_entities):
    entities = []
    for uuid, connection in entry.runtime_data.coordinators.items():

        if connection.charge_point_installation:
            _LOGGER.debug("Setup buttons for connnection %s", uuid)

            for sensor_key in BUTTON_TYPES[CHARGE_POINT]:
                entities.append(
                    ZonneplanChargePointButton(
                        uuid,
                        sensor_key,
                        connection.charge_point_installation,
                        0,
                        BUTTON_TYPES[CHARGE_POINT][sensor_key],
                    )
                )

    async_add_entities(entities)


class ZonneplanChargePointButton(ChargePointEntity, CoordinatorEntity, ButtonEntity):
    """Zonneplan Charge Point Button"""

    coordinator: ChargePointDataUpdateCoordinator
    entity_description: ZonneplanButtonEntityDescription
    _connection_uuid: str
    _button_key: str
    _install_index: int

    def __init__(
            self,
            connection_uuid,
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
    def unique_id(self) -> Optional[str]:
        """Return a unique ID."""
        return self.install_uuid + "_" + self._button_key

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

        if self._button_key == "stop" and state["state"] == "Charging":
            return True

        if self._button_key == "start" and state["state"] == "VehicleDetected":
            return True

        return False

    async def async_press(self) -> None:
        """Handle the button press."""

        if self._button_key == "start":
            await self.coordinator.async_start_charge()
        elif self._button_key == "stop":
            await self.coordinator.async_stop_charge()
        else:
            _LOGGER.warning("Unknown button action for %s", self._button_key)
