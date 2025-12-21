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

from .coordinator import ZonneplanUpdateCoordinator
from .const import (
    BATTERY,
    DOMAIN,
    CHARGE_POINT,
    BUTTON_TYPES,
    ZonneplanButtonEntityDescription,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry, async_add_entities):
    coordinator: ZonneplanUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    entities = []
    for uuid, connection in coordinator.connections.items():

        _LOGGER.debug("Setup buttons for connnection %s", uuid)

        charge_point = coordinator.getConnectionValue(uuid, CHARGE_POINT)
        if charge_point:
            for install_index in range(len(charge_point)):
                for sensor_key in BUTTON_TYPES[CHARGE_POINT]:
                    entities.append(
                        ZonneplanChargePointButton(
                            uuid,
                            sensor_key,
                            coordinator,
                            install_index,
                            BUTTON_TYPES[CHARGE_POINT][sensor_key],
                        )
                    )


        battery = coordinator.getConnectionValue(uuid, BATTERY)
        if battery:
            for install_index in range(len(battery)):
                for sensor_key in BUTTON_TYPES[BATTERY]:
                    entities.append(
                        ZonneplanBatteryButton(
                            uuid,
                            sensor_key,
                            coordinator,
                            install_index,
                            BUTTON_TYPES[BATTERY][sensor_key],
                        )
                    )

    async_add_entities(entities)


class ZonneplanChargePointButton(CoordinatorEntity, ButtonEntity):
    """Abstract class for a zonneplan sensor."""

    coordinator: ZonneplanUpdateCoordinator

    def __init__(
        self,
        connection_uuid,
        button_key: str,
        coordinator: ZonneplanUpdateCoordinator,
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
    def install_uuid(self) -> str:
        """Return install ID."""
        return self.coordinator.getConnectionValue(
            self._connection_uuid,
            "charge_point_installation.{install_index}.uuid".format(
                install_index=self._install_index
            ),
        )

    @property
    def unique_id(self) -> Optional[str]:
        """Return a unique ID."""
        return self.install_uuid + "_" + self._button_key

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
        return {
            "identifiers": {(DOMAIN, self.install_uuid)},
            "via_device": (DOMAIN, self._connection_uuid),
            "manufacturer": "Zonneplan",
            "name": self.coordinator.getConnectionValue(
                self._connection_uuid,
                "charge_point_installation.{install_index}.label".format(
                    install_index=self._install_index
                ),
            ) + (f" ({self._install_index + 1})" if self._install_index and self._install_index > 0 else ""),
            "model": self.coordinator.getConnectionValue(
                self._connection_uuid,
                "charge_point_installation.{install_index}.label".format(
                    install_index=self._install_index
                ),
            ),
            "serial_number": self.coordinator.getConnectionValue(
                self._connection_uuid,
                "charge_point_installation.{install_index}.meta.serial_number".format(
                    install_index=self._install_index
                ),
            ),
        }

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
            _LOGGER.warning("Unknown button action for %s", self._button_key)


class ZonneplanBatteryButton(CoordinatorEntity, ButtonEntity):
    """Class for a zonneplan battery button."""

    coordinator: ZonneplanUpdateCoordinator

    def __init__(
        self,
        connection_uuid,
        button_key: str,
        coordinator: ZonneplanUpdateCoordinator,
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
    def install_uuid(self) -> str:
        """Return install ID."""
        return self.coordinator.getConnectionValue(
            self._connection_uuid,
            "home_battery_installation.{install_index}.uuid".format(
                install_index=self._install_index
            ),
        )

    @property
    def unique_id(self) -> Optional[str]:
        """Return a unique ID."""
        return self.install_uuid + "_" + self._button_key

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success:
            return False

        control_mode = self.coordinator.getConnectionValue(self._connection_uuid, "battery_control_mode").format(
                install_index=self._install_index
            )

        if "processing" in control_mode:
            return False

        return True

        # if self._button_key == "enable_self_consumption" and control_mode["modes"]["self_consumption"]["available"] and not control_mode["modes"]["self_consumption"]["enabled"]:
        #     return True
        #
        # if self._button_key == "enable_dynamic_charging" and control_mode["modes"]["dynamic_charging"]["available"] and not control_mode["modes"]["dynamic_charging"]["enabled"]:
        #     return True
        #
        # if self._button_key == "enable_home_optimization" and control_mode["modes"]["home_optimization"]["available"] and not control_mode["modes"]["home_optimization"]["enabled"]:
        #     return True
        #
        # return False

    @property
    def device_info(self):
        """Return the device information."""
        return {
            "identifiers": {(DOMAIN, self.install_uuid)},
            "via_device": (DOMAIN, self._connection_uuid),
            "manufacturer": "Zonneplan",
            "name": self.coordinator.getConnectionValue(
                self._connection_uuid,
                "home_battery_installation.{install_index}.label".format(
                    install_index=self._install_index
                ),
            ) + (f" ({self._install_index + 1})" if self._install_index and self._install_index > 0 else ""),
            "model": self.coordinator.getConnectionValue(
                self._connection_uuid,
                "home_battery_installation.{install_index}.label".format(
                    install_index=self._install_index
                ),
            ),
            "serial_number": self.coordinator.getConnectionValue(
                self._connection_uuid,
                "home_battery_installation.{install_index}.meta.serial_number".format(
                    install_index=self._install_index
                ),
            ),
        }

    async def async_press(self) -> None:
        """Handle the button press."""

        battery_uuid = self.coordinator.getConnectionValue(
            self._connection_uuid, "battery_data.uuid"
        )

        if self._button_key == "enable_self_consumption":
            await self.coordinator.async_enable_self_consumption(
                self._connection_uuid, self._install_index, battery_uuid
            )
        elif self._button_key == "enable_dynamic_charging":
            await self.coordinator.async_enable_dynamic_charging(
                self._connection_uuid, self._install_index, battery_uuid
            )
        elif self._button_key == "enable_home_optimization":
            await self.coordinator.async_enable_home_optimization(
                self._connection_uuid, self._install_index, battery_uuid
            )
        else:
            _LOGGER.warning("Unknown button action for %s", self._button_key)
