"""Zonneplan button"""
from typing import Optional, Any
from voluptuous.validators import Number

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
import logging
from homeassistant.core import callback
from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.components.button import (
    ButtonEntity,
)

from .coordinator import ZonneplanUpdateCoordinator
from .const import (
    DOMAIN,
    CHARGE_POINT,
    BUTTON_TYPES,
    ZonneplanButtonEntityDescription,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistantType, config_entry, async_add_entities):
    coordinator: ZonneplanUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    entities = []
    for uuid, connection in coordinator.connections.items():
        charge_point = coordinator.getConnectionValue(uuid, CHARGE_POINT)

        _LOGGER.debug("Setup buttons for connnection %s", uuid)

        if charge_point:
            for install_index in range(len(charge_point)):
                for sensor_key in BUTTON_TYPES[CHARGE_POINT]:
                    entities.append(
                        ZonneplanButton(
                            uuid,
                            sensor_key,
                            coordinator,
                            install_index,
                            BUTTON_TYPES[CHARGE_POINT][sensor_key],
                        )
                    )

    async_add_entities(entities)


class ZonneplanButton(CoordinatorEntity, ButtonEntity):
    """Abstract class for a zonneplan sensor."""

    coordinator: ZonneplanUpdateCoordinator

    def __init__(
        self,
        connection_uuid,
        button_key: str,
        coordinator: ZonneplanUpdateCoordinator,
        install_index: Number,
        description: ZonneplanButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._connection_uuid = connection_uuid
        self._button_key = button_key
        self._install_index = install_index
        self.entity_description = description

    @property
    def install_uuid(self) -> str:
        """Return install ID."""
        return self._connection_uuid

    @property
    def unique_id(self) -> Optional[str]:
        """Return a unique ID."""
        return self.install_uuid + "_" + self._button_key

    @property
    def name(self) -> str:
        """Return the name of the entity."""

        name = self.entity_description.name
        if self._install_index and self._install_index > 0:
            name += " (" + str(self._install_index + 1) + ")"

        return name

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False

        state = self.coordinator.getConnectionValue(self._connection_uuid, "charge_point_data.state")

        if not state["connectivity_state"]:
            return False

        if "processing" in state:
            return False

        if self._button_key == "stop" and state["state"] == "Charging":
            return True

        if self._button_key == "start" and state["state"] == "VehicleDetected":
            return True

    @property
    def device_info(self):
        """Return the device information."""
        device_info = {
            "identifiers": {(DOMAIN, self._connection_uuid, CHARGE_POINT)},
            "manufacturer": "Zonneplan",
            "name": self.coordinator.getConnectionValue(
                self._connection_uuid,
                "charge_point_installation.0.label",
            ),
        }

        if self._install_index >= 0:
            device_info["identifiers"].add((DOMAIN, self.install_uuid))
            device_info["name"] = self.coordinator.getConnectionValue(
                self._connection_uuid,
                "charge_point_installation.{install_index}.label".format(
                    install_index=self._install_index
                ),
            )
            device_info["model"] = self.coordinator.getConnectionValue(
                self._connection_uuid,
                "charge_point_installation.{install_index}.meta.serial_number".format(
                    install_index=self._install_index
                ),
            )

        return device_info

    async def async_press(self) -> None:
        """Handle the button press."""

        charge_point_uuid = self.coordinator.getConnectionValue(
            self._connection_uuid, "charge_point_data.uuid"
        )

        if self._button_key == "start":
            await self.coordinator.async_startCharge(
                self._connection_uuid, charge_point_uuid
            )
        elif self._button_key == "stop":
            await self.coordinator.async_stopCharge(
                self._connection_uuid, charge_point_uuid
            )
        else:
            _LOGGER.warning("Unknonw button action for %s", self._button_key)
