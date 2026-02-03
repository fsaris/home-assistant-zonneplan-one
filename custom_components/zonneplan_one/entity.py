"""Zonneplan Battery Entity."""

from typing import Protocol

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .coordinators.battery_charts_data_coordinator import (
    BatteryChartsDataUpdateCoordinator,
)
from .coordinators.battery_control_data_coordinator import (
    BatteryControlDataUpdateCoordinator,
)
from .coordinators.battery_data_coordinator import BatteryDataUpdateCoordinator
from .coordinators.charge_point_data_coordinator import ChargePointDataUpdateCoordinator
from .coordinators.electricity_data_coordinator import ElectricityDataUpdateCoordinator
from .coordinators.gas_data_coordinator import GasDataUpdateCoordinator
from .coordinators.pv_data_coordinator import PvDataUpdateCoordinator


def base_device_info(identifier: str) -> DeviceInfo:
    return {
        "identifiers": {(DOMAIN, identifier)},
        "manufacturer": "Zonneplan",
        "name": "Zonneplan",
    }


class HasBatteryDataCoordinator(Protocol):
    coordinator: BatteryDataUpdateCoordinator | BatteryChartsDataUpdateCoordinator | BatteryControlDataUpdateCoordinator
    _connection_uuid: str

    @property
    def install_uuid(self) -> str:
        pass


class HasChargePointDataUpdateCoordinator(Protocol):
    coordinator: ChargePointDataUpdateCoordinator
    _connection_uuid: str

    @property
    def install_uuid(self) -> str:
        pass


class HasPvDataUpdateCoordinator(Protocol):
    coordinator: PvDataUpdateCoordinator
    _connection_uuid: str
    _install_index: int

    @property
    def install_uuid(self) -> str:
        pass


class HasP1DataUpdateCoordinator(Protocol):
    coordinator: ElectricityDataUpdateCoordinator | GasDataUpdateCoordinator
    _connection_uuid: str
    _install_index: int

    @property
    def install_uuid(self) -> str:
        pass


class BatteryEntity:
    """Defines a base Zonneplan Battery Entity."""

    @property
    def install_uuid(self: HasBatteryDataCoordinator) -> str:
        """Return install ID."""
        return self.coordinator.contract["uuid"]

    @property
    def device_info(self: HasBatteryDataCoordinator) -> DeviceInfo:
        """Return the device information."""
        return {
            "identifiers": {(DOMAIN, self.install_uuid)},
            "name": self.coordinator.contract["label"],
            "model": self.coordinator.contract["label"],
            "serial_number": self.coordinator.contract.get("meta", {}).get("identifier"),
        }


class ChargePointEntity:
    """Defines a base Zonneplan Charge Point Entity."""

    @property
    def install_uuid(self: HasChargePointDataUpdateCoordinator) -> str:
        """Return install ID."""
        return self.coordinator.contract["uuid"]

    @property
    def device_info(self: HasChargePointDataUpdateCoordinator) -> DeviceInfo:
        """Return the device information."""
        return {
            "identifiers": {(DOMAIN, self.install_uuid)},
            "manufacturer": "Zonneplan",
            "name": self.coordinator.contract["label"],
            "model": self.coordinator.contract["label"],
            "serial_number": self.coordinator.contract.get("meta", {}).get("serial_number"),
        }


class PvEntity:
    """Defines a base Zonneplan PV Entity."""

    @property
    def install_uuid(self: HasPvDataUpdateCoordinator) -> str:
        """Return install ID."""
        if self._install_index < 0:
            return self._connection_uuid
        return self.coordinator.contracts[self._install_index]["uuid"]

    @property
    def device_info(self: HasPvDataUpdateCoordinator) -> DeviceInfo:
        """Return the device information."""
        device_info: DeviceInfo = base_device_info(self.coordinator.address_uuid)

        if self._install_index >= 0:
            device_info["identifiers"] = {(DOMAIN, self.install_uuid)}
            device_info["name"] = self.coordinator.contracts[self._install_index]["meta"].get("name", "") + (
                f" ({self._install_index + 1})" if self._install_index and self._install_index > 0 else ""
            )
            device_info["model"] = (
                self.coordinator.contracts[self._install_index]["label"]
                + " "
                + str(self.coordinator.contracts[self._install_index]["meta"].get("panel_count", ""))
                + " panels"
            )
            device_info["serial_number"] = self.coordinator.contracts[self._install_index]["meta"].get("sgn_serial_number", "")
            device_info["sw_version"] = (
                self.coordinator.contracts[self._install_index]["meta"].get("module_firmware_version", "") or "unknown"
            )
            device_info["hw_version"] = (
                self.coordinator.contracts[self._install_index]["meta"].get("inverter_firmware_version", "") or "unknown"
            )

        return device_info


class P1Entity:
    """Defines a base Zonneplan P1 Entity."""

    @property
    def install_uuid(self: HasP1DataUpdateCoordinator) -> str:
        """Return install ID."""
        if self._install_index < 0:
            return self._connection_uuid
        return self.coordinator.contracts[self._install_index]["uuid"]

    @property
    def device_info(self: HasP1DataUpdateCoordinator) -> DeviceInfo:
        """Return the device information."""
        device_info: DeviceInfo = base_device_info(self.coordinator.address_uuid)

        if self._install_index >= 0:
            device_info["identifiers"] = {(DOMAIN, self.install_uuid)}
            device_info["name"] = self.coordinator.contracts[self._install_index]["label"] + (
                f" ({self._install_index + 1})" if self._install_index and self._install_index > 0 else ""
            )
            device_info["model"] = self.coordinator.contracts[self._install_index]["label"]
            device_info["serial_number"] = self.coordinator.contracts[self._install_index]["meta"].get("sgn_serial_number", "")
            device_info["sw_version"] = self.coordinator.contracts[self._install_index]["meta"].get("sgn_firmware", "") or "unknown"

        return device_info
