"""Constants for the Zonneplan ONE integration."""
from __future__ import annotations
from dataclasses import dataclass
from homeassistant.components.sensor import (
    STATE_CLASS_MEASUREMENT,
    SensorEntityDescription,
)
from homeassistant.const import (
    DEVICE_CLASS_ENERGY,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_TIMESTAMP,
    ENERGY_KILO_WATT_HOUR,
    POWER_WATT,
    VOLUME_CUBIC_METERS,
)

DOMAIN = "zonneplan_one"

PV_INSTALL = "pv_installation"
P1_INSTALL = "p1_installation"


@dataclass
class ZonneplanSensorEntityDescription(SensorEntityDescription):
    """A class that describes Zoonneplan sensor entities."""

    entity_registry_enabled_default: bool = False
    last_reset_key: str | None = None
    last_reset_today_key: str | None = None


"""Available sensors"""
SENSOR_TYPES: dict[str, list[ZonneplanSensorEntityDescription]] = {
    PV_INSTALL: {
        "install": {
            "highest_measured_power_value": ZonneplanSensorEntityDescription(
                key="pv_installation.{install_index}.meta.highest_measured_power_value",
                name="Zonneplan highest yield value",
                unit_of_measurement=POWER_WATT,
                device_class=DEVICE_CLASS_POWER,
                icon="mdi:solar-power",
            ),
            "highest_power_measured_at": ZonneplanSensorEntityDescription(
                key="pv_installation.{install_index}.meta.highest_power_measured_at",
                name="Zonneplan highest yield",
                device_class=DEVICE_CLASS_TIMESTAMP,
                icon="mdi:calendar",
            ),
            "total_power_measured": ZonneplanSensorEntityDescription(
                key="pv_installation.{install_index}.meta.total_power_measured",
                name="Zonneplan yield total",
                unit_of_measurement=ENERGY_KILO_WATT_HOUR,
                device_class=DEVICE_CLASS_ENERGY,
                icon="mdi:solar-power",
                entity_registry_enabled_default=True,
                state_class=STATE_CLASS_MEASUREMENT,
                last_reset_key="pv_installation.{install_index}.meta.first_measured_at",
            ),
            "last_measured_power_value": ZonneplanSensorEntityDescription(
                key="pv_installation.{install_index}.meta.last_measured_power_value",
                name="Zonneplan last measured value",
                unit_of_measurement=POWER_WATT,
                device_class=DEVICE_CLASS_POWER,
                icon="mdi:solar-power",
                entity_registry_enabled_default=True,
            ),
            "first_measured_at": ZonneplanSensorEntityDescription(
                key="pv_installation.{install_index}.meta.first_measured_at",
                name="Zonneplan first measured",
                device_class=DEVICE_CLASS_TIMESTAMP,
                icon="mdi:calendar-clock",
            ),
            "last_measured_at": ZonneplanSensorEntityDescription(
                key="pv_installation.{install_index}.meta.last_measured_at",
                name="Zonneplan last measured",
                device_class=DEVICE_CLASS_TIMESTAMP,
                icon="mdi:calendar-clock",
                entity_registry_enabled_default=True,
            ),
        },
        "totals": {
            "total_today": ZonneplanSensorEntityDescription(
                key="live_data.total",
                name="Zonneplan yield today",
                unit_of_measurement=ENERGY_KILO_WATT_HOUR,
                device_class=DEVICE_CLASS_ENERGY,
                icon="mdi:solar-power",
                entity_registry_enabled_default=True,
                state_class=STATE_CLASS_MEASUREMENT,
                last_reset_today_key="live_data.date",
            ),
        },
    },
    P1_INSTALL: {
        "totals": {
            "electricity_total_today": ZonneplanSensorEntityDescription(
                key="electricity.measurement_groups.0.total",
                name="Zonneplan P1 electricity consumption today",
                unit_of_measurement=ENERGY_KILO_WATT_HOUR,
                device_class=DEVICE_CLASS_ENERGY,
                entity_registry_enabled_default=True,
                state_class=STATE_CLASS_MEASUREMENT,
                last_reset_today_key="electricity.measurement_groups.0.date",
            ),
            "electricity_total_today_low_tariff": ZonneplanSensorEntityDescription(
                key="electricity.measurement_groups.0.meta.low_tariff_group",
                name="Zonneplan P1 electricity consumption today low tariff",
                unit_of_measurement=ENERGY_KILO_WATT_HOUR,
                device_class=DEVICE_CLASS_ENERGY,
                entity_registry_enabled_default=False,
                state_class=STATE_CLASS_MEASUREMENT,
                last_reset_today_key="electricity.measurement_groups.0.date",
            ),
            "electricity_total_today_normal_tariff": ZonneplanSensorEntityDescription(
                key="electricity.measurement_groups.0.meta.normal_tariff_group",
                name="Zonneplan P1 electricity consumption today normal tariff",
                unit_of_measurement=ENERGY_KILO_WATT_HOUR,
                device_class=DEVICE_CLASS_ENERGY,
                entity_registry_enabled_default=False,
                state_class=STATE_CLASS_MEASUREMENT,
                last_reset_today_key="electricity.measurement_groups.0.date",
            ),
            "electricity_total_today_high_tariff": ZonneplanSensorEntityDescription(
                key="electricity.measurement_groups.0.meta.high_tariff_group",
                name="Zonneplan P1 electricity consumption today high tariff",
                unit_of_measurement=ENERGY_KILO_WATT_HOUR,
                device_class=DEVICE_CLASS_ENERGY,
                entity_registry_enabled_default=False,
                state_class=STATE_CLASS_MEASUREMENT,
                last_reset_today_key="electricity.measurement_groups.0.date",
            ),
            "gas_total_today": ZonneplanSensorEntityDescription(
                key="gas.measurement_groups.0.total",
                name="Zonneplan P1 gas consumption today",
                unit_of_measurement=VOLUME_CUBIC_METERS,
                icon="mdi:fire",
                entity_registry_enabled_default=True,
                state_class=STATE_CLASS_MEASUREMENT,
                last_reset_today_key="gas.measurement_groups.0.date",
            ),
        },
        "install": {
            "electricity_last_measured_delivery_value": ZonneplanSensorEntityDescription(
                key="p1_installation.{install_index}.meta.electricity_last_measured_delivery_value",
                name="Zonneplan P1 electricity consumption",
                unit_of_measurement=POWER_WATT,
                device_class=DEVICE_CLASS_POWER,
                entity_registry_enabled_default=True,
            ),
            "electricity_last_measured_production_value": ZonneplanSensorEntityDescription(
                key="p1_installation.{install_index}.meta.electricity_last_measured_production_value",
                name="Zonneplan P1 electricity production",
                unit_of_measurement=POWER_WATT,
                device_class=DEVICE_CLASS_POWER,
                entity_registry_enabled_default=True,
                state_class=STATE_CLASS_MEASUREMENT,
                last_reset_key="p1_installation.{install_index}.meta.electricity_first_measured_at",
            ),
            "electricity_last_measured_average_value": ZonneplanSensorEntityDescription(
                key="p1_installation.{install_index}.meta.electricity_last_measured_average_value",
                name="Zonneplan P1 electricity average",
                unit_of_measurement=POWER_WATT,
                device_class=DEVICE_CLASS_POWER,
                entity_registry_enabled_default=True,
                state_class=STATE_CLASS_MEASUREMENT,
                last_reset_key="p1_installation.{install_index}.meta.electricity_first_measured_at",
            ),
            "electricity_first_measured_at": ZonneplanSensorEntityDescription(
                key="p1_installation.{install_index}.meta.electricity_first_measured_at",
                name="Zonneplan P1 electricity first measured",
                device_class=DEVICE_CLASS_TIMESTAMP,
                icon="mdi:calendar-clock",
            ),
            "electricity_last_measured_at": ZonneplanSensorEntityDescription(
                key="p1_installation.{install_index}.meta.electricity_last_measured_at",
                name="Zonneplan P1 electricity last measured",
                device_class=DEVICE_CLASS_TIMESTAMP,
                icon="mdi:calendar-clock",
                entity_registry_enabled_default=True,
            ),
            "electricity_last_measured_production_at": ZonneplanSensorEntityDescription(
                key="p1_installation.{install_index}.meta.electricity_last_measured_production_at",
                name="Zonneplan P1 electricity last measured production",
                device_class=DEVICE_CLASS_TIMESTAMP,
                icon="mdi:calendar-clock",
                entity_registry_enabled_default=True,
            ),
            "gas_last_measured_value": ZonneplanSensorEntityDescription(
                key="p1_installation.{install_index}.meta.gas_last_measured_value",
                name="Zonneplan P1 gas last measured consumption",
                unit_of_measurement=VOLUME_CUBIC_METERS,
                icon="mdi:fire",
                entity_registry_enabled_default=True,
                state_class=STATE_CLASS_MEASUREMENT,
                last_reset_key="p1_installation.{install_index}.meta.gas_first_measured_at",
            ),
            "gas_first_measured_at": ZonneplanSensorEntityDescription(
                key="p1_installation.{install_index}.meta.gas_first_measured_at",
                name="Zonneplan P1 gas first measured",
                device_class=DEVICE_CLASS_TIMESTAMP,
                icon="mdi:calendar-clock",
            ),
            "gas_last_measured_at": ZonneplanSensorEntityDescription(
                key="p1_installation.{install_index}.meta.gas_last_measured_at",
                name="Zonneplan P1 gas last measured",
                device_class=DEVICE_CLASS_TIMESTAMP,
                icon="mdi:calendar-clock",
                entity_registry_enabled_default=True,
            ),
        },
    },
}
