"""Constants for the Zonneplan ONE integration."""
from __future__ import annotations
from dataclasses import dataclass

from voluptuous.validators import Number
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CURRENCY_EURO,
    ENERGY_KILO_WATT_HOUR,
    POWER_WATT,
    VOLUME_CUBIC_METERS,
)

DOMAIN = "zonneplan_one"

SUMMARY = "summary_data"
PV_INSTALL = "pv_installation"
P1_INSTALL = "p1_installation"


@dataclass
class ZonneplanSensorEntityDescription(SensorEntityDescription):
    """A class that describes Zoonneplan sensor entities."""

    entity_registry_enabled_default: bool = False
    value_factor: Number = None


"""Available sensors"""
SENSOR_TYPES: dict[str, list[ZonneplanSensorEntityDescription]] = {
    SUMMARY: {
        "usage": ZonneplanSensorEntityDescription(
            key="summary_data.usage.value",
            name="Current usage",
            native_unit_of_measurement=POWER_WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=True,
        ),
        "usage_measured_at": ZonneplanSensorEntityDescription(
            key="summary_data.usage.measured_at",
            name="Current usage measured at",
            device_class=SensorDeviceClass.TIMESTAMP,
            icon="mdi:calendar-clock",
        ),
        "sustainability_score": ZonneplanSensorEntityDescription(
            key="summary_data.usage.sustainability_score",
            name="Sustainability score",
            icon="mdi:leaf-circle-outline",
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=True,
            value_factor=0.1,
            native_unit_of_measurement="%",
        ),
        "current_tariff_group": ZonneplanSensorEntityDescription(
            key="summary_data.usage.type",
            name="Current tariff group",
        ),
        "current_tariff": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.0.price",
            name="Current tariff",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=CURRENCY_EURO,
        ),
        "status_message": ZonneplanSensorEntityDescription(
            key="summary_data.usage.status_message",
            name="Status message",
            icon="mdi:message-text-outline",
        ),
        "status_tip": ZonneplanSensorEntityDescription(
            key="summary_data.usage.status_tip",
            name="Status tip",
            icon="mdi:message-text-outline",
            entity_registry_enabled_default=True,
        ),
    },
    PV_INSTALL: {
        "install": {
            "highest_measured_power_value": ZonneplanSensorEntityDescription(
                key="pv_installation.{install_index}.meta.highest_measured_power_value",
                name="Zonneplan highest yield value",
                native_unit_of_measurement=POWER_WATT,
                device_class=SensorDeviceClass.POWER,
                icon="mdi:solar-power",
                state_class=SensorStateClass.MEASUREMENT,
            ),
            "highest_power_measured_at": ZonneplanSensorEntityDescription(
                key="pv_installation.{install_index}.meta.highest_power_measured_at",
                name="Zonneplan highest yield",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:calendar",
            ),
            "total_power_measured": ZonneplanSensorEntityDescription(
                key="pv_installation.{install_index}.meta.total_power_measured",
                name="Zonneplan yield total",
                native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
                value_factor=0.001,
                device_class=SensorDeviceClass.ENERGY,
                icon="mdi:solar-power",
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.TOTAL_INCREASING,
            ),
            "last_measured_power_value": ZonneplanSensorEntityDescription(
                key="pv_installation.{install_index}.meta.last_measured_power_value",
                name="Zonneplan last measured value",
                native_unit_of_measurement=POWER_WATT,
                device_class=SensorDeviceClass.POWER,
                icon="mdi:solar-power",
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            "first_measured_at": ZonneplanSensorEntityDescription(
                key="pv_installation.{install_index}.meta.first_measured_at",
                name="Zonneplan first measured",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:calendar-clock",
            ),
            "last_measured_at": ZonneplanSensorEntityDescription(
                key="pv_installation.{install_index}.meta.last_measured_at",
                name="Zonneplan last measured",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:calendar-clock",
                entity_registry_enabled_default=True,
            ),
        },
        "totals": {
            "total_today": ZonneplanSensorEntityDescription(
                key="live_data.total",
                name="Zonneplan yield today",
                native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
                value_factor=0.001,
                device_class=SensorDeviceClass.ENERGY,
                icon="mdi:solar-power",
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.TOTAL_INCREASING,
            ),
        },
    },
    P1_INSTALL: {
        "totals": {
            "electricity_total_today": ZonneplanSensorEntityDescription(
                key="electricity_data.measurement_groups.0.total",
                name="Zonneplan P1 electricity consumption today",
                native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
                value_factor=0.001,
                device_class=SensorDeviceClass.ENERGY,
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.TOTAL_INCREASING,
            ),
            "electricity_total_today_low_tariff": ZonneplanSensorEntityDescription(
                key="electricity_data.measurement_groups.0.meta.low_tariff_group",
                name="Zonneplan P1 electricity consumption today low tariff",
                native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
                value_factor=0.001,
                device_class=SensorDeviceClass.ENERGY,
                entity_registry_enabled_default=False,
                state_class=SensorStateClass.TOTAL_INCREASING,
            ),
            "electricity_total_today_normal_tariff": ZonneplanSensorEntityDescription(
                key="electricity_data.measurement_groups.0.meta.normal_tariff_group",
                name="Zonneplan P1 electricity consumption today normal tariff",
                native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
                value_factor=0.001,
                device_class=SensorDeviceClass.ENERGY,
                entity_registry_enabled_default=False,
                state_class=SensorStateClass.TOTAL_INCREASING,
            ),
            "electricity_total_today_high_tariff": ZonneplanSensorEntityDescription(
                key="electricity_data.measurement_groups.0.meta.high_tariff_group",
                name="Zonneplan P1 electricity consumption today high tariff",
                native_unit_of_measurement=ENERGY_KILO_WATT_HOUR,
                value_factor=0.001,
                device_class=SensorDeviceClass.ENERGY,
                entity_registry_enabled_default=False,
                state_class=SensorStateClass.TOTAL_INCREASING,
            ),
            "gas_total_today": ZonneplanSensorEntityDescription(
                key="gas_data.measurement_groups.0.total",
                name="Zonneplan P1 gas consumption today",
                native_unit_of_measurement=VOLUME_CUBIC_METERS,
                value_factor=0.001,
                device_class=SensorDeviceClass.GAS,
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.TOTAL_INCREASING,
            ),
        },
        "install": {
            "electricity_last_measured_delivery_value": ZonneplanSensorEntityDescription(
                key="p1_installation.{install_index}.meta.electricity_last_measured_delivery_value",
                name="Zonneplan P1 electricity consumption",
                native_unit_of_measurement=POWER_WATT,
                device_class=SensorDeviceClass.POWER,
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            "electricity_last_measured_production_value": ZonneplanSensorEntityDescription(
                key="p1_installation.{install_index}.meta.electricity_last_measured_production_value",
                name="Zonneplan P1 electricity production",
                native_unit_of_measurement=POWER_WATT,
                device_class=SensorDeviceClass.POWER,
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            "electricity_last_measured_average_value": ZonneplanSensorEntityDescription(
                key="p1_installation.{install_index}.meta.electricity_last_measured_average_value",
                name="Zonneplan P1 electricity average",
                native_unit_of_measurement=POWER_WATT,
                device_class=SensorDeviceClass.POWER,
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            "electricity_first_measured_at": ZonneplanSensorEntityDescription(
                key="p1_installation.{install_index}.meta.electricity_first_measured_at",
                name="Zonneplan P1 electricity first measured",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:calendar-clock",
            ),
            "electricity_last_measured_at": ZonneplanSensorEntityDescription(
                key="p1_installation.{install_index}.meta.electricity_last_measured_at",
                name="Zonneplan P1 electricity last measured",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:calendar-clock",
                entity_registry_enabled_default=True,
            ),
            "electricity_last_measured_production_at": ZonneplanSensorEntityDescription(
                key="p1_installation.{install_index}.meta.electricity_last_measured_production_at",
                name="Zonneplan P1 electricity last measured production",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:calendar-clock",
                entity_registry_enabled_default=True,
            ),
            "gas_last_measured_value": ZonneplanSensorEntityDescription(
                key="p1_installation.{install_index}.meta.gas_last_measured_value",
                name="Zonneplan P1 gas last measured consumption",
                native_unit_of_measurement=VOLUME_CUBIC_METERS,
                value_factor=0.001,
                device_class=SensorDeviceClass.GAS,
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            "gas_first_measured_at": ZonneplanSensorEntityDescription(
                key="p1_installation.{install_index}.meta.gas_first_measured_at",
                name="Zonneplan P1 gas first measured",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:calendar-clock",
            ),
            "gas_last_measured_at": ZonneplanSensorEntityDescription(
                key="p1_installation.{install_index}.meta.gas_last_measured_at",
                name="Zonneplan P1 gas last measured",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:calendar-clock",
                entity_registry_enabled_default=True,
            ),
        },
    },
}
