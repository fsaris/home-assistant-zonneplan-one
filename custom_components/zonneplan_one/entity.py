"""Zonneplan Battery Entity."""
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ZonneplanUpdateCoordinator


class ZonneplanBatteryEntity(CoordinatorEntity):
    """Defines a base Zonneplan Battery Entity."""

    coordinator: ZonneplanUpdateCoordinator
    _connection_uuid: str
    _install_index: int
    _battery_uuid: str

    def __init__(
        self,
        coordinator: ZonneplanUpdateCoordinator,
        connection_uuid: str,
        install_index: int,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._connection_uuid = connection_uuid
        self._install_index = install_index
        self._battery_uuid = self.coordinator.getConnectionValue(
            self._connection_uuid, f"home_battery_installation.{install_index}.uuid"
        )

    @property
    def install_uuid(self) -> str:
        """Return the install UUID."""
        return self.coordinator.getConnectionValue(
            self._connection_uuid,
            f"home_battery_installation.{self._install_index}.uuid",
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device information."""
        return {
            "identifiers": {(DOMAIN, self.install_uuid)},
            "via_device": (DOMAIN, self._connection_uuid),
            "manufacturer": "Zonneplan",
            "name": self.coordinator.getConnectionValue(
                self._connection_uuid,
                f"home_battery_installation.{self._install_index}.label",
            )
            + (
                f" ({self._install_index + 1})"
                if self._install_index and self._install_index > 0
                else ""
            ),
            "model": self.coordinator.getConnectionValue(
                self._connection_uuid,
                f"home_battery_installation.{self._install_index}.meta.host_device_model_name",
            ),
            "serial_number": self.coordinator.getConnectionValue(
                self._connection_uuid,
                f"home_battery_installation.{self._install_index}.meta.identifier",
            ),
        }