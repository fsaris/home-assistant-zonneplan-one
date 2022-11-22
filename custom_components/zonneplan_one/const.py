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
    PERCENTAGE,
)

DOMAIN = "zonneplan_one"

SUMMARY = "summary_data"
PV_INSTALL = "pv_installation"
P1_INSTALL = "p1_installation"

NONE_IS_ZERO = 'none-is-zero'
NONE_USE_PREVIOUS = 'none-is-previous'

@dataclass
class ZonneplanSensorEntityDescription(SensorEntityDescription):
    """A class that describes Zonneplan sensor entities."""

    entity_registry_enabled_default: bool = False
    value_factor: Number = None
    none_value_behaviour: String = ''
    daily_update_hour: None|Number = None


"""Available sensors"""
SENSOR_TYPES: dict[str, list[ZonneplanSensorEntityDescription]] = {
    SUMMARY: {
        "usage": ZonneplanSensorEntityDescription(
            key="summary_data.usage.value",
            name="Zonneplan current usage",
            native_unit_of_measurement=POWER_WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=True,
        ),
        "usage_measured_at": ZonneplanSensorEntityDescription(
            key="summary_data.usage.measured_at",
            name="Zonneplan current usage measured at",
            device_class=SensorDeviceClass.TIMESTAMP,
            icon="mdi:calendar-clock",
        ),
        "sustainability_score": ZonneplanSensorEntityDescription(
            key="summary_data.usage.sustainability_score",
            name="Zonneplan sustainability score",
            icon="mdi:leaf-circle-outline",
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=True,
            value_factor=0.1,
            native_unit_of_measurement=PERCENTAGE,
        ),
        "current_tariff_group": ZonneplanSensorEntityDescription(
            key="summary_data.usage.type",
            name="Zonneplan current tariff group",
        ),
        "current_tariff": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.24.price",
            name="Zonneplan current electricity tariff",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
            state_class=SensorStateClass.MEASUREMENT,
        ),
        "current_tariff_gas": ZonneplanSensorEntityDescription(
            key="gas_data.measurement_groups.0.meta.price",
            name="Zonneplan current gas tariff",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{VOLUME_CUBIC_METERS}",
            state_class=SensorStateClass.MEASUREMENT,
            none_value_behaviour=NONE_USE_PREVIOUS,
            daily_update_hour=6,
        ),
        "status_message": ZonneplanSensorEntityDescription(
            key="summary_data.usage.status_message",
            name="Zonneplan status message",
            icon="mdi:message-text-outline",
        ),
        "status_tip": ZonneplanSensorEntityDescription(
            key="summary_data.usage.status_tip",
            name="Zonneplan status tip",
            icon="mdi:message-text-outline",
            entity_registry_enabled_default=True,
        ),
        "forcast_tariff_1": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.25.price",
            name="Zonneplan forcast tariff hour 1",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
        ),
        "forcast_tariff_2": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.26.price",
            name="Zonneplan forcast tariff hour 2",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
        ),
        "forcast_tariff_3": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.27.price",
            name="Zonneplan forcast tariff hour 3",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
        ),
        "forcast_tariff_4": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.28.price",
            name="Zonneplan forcast tariff hour 4",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
        ),
        "forcast_tariff_5": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.29.price",
            name="Zonneplan forcast tariff hour 5",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
        ),
        "forcast_tariff_6": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.30.price",
            name="Zonneplan forcast tariff hour 6",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
        ),
        "forcast_tariff_7": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.31.price",
            name="Zonneplan forcast tariff hour 7",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
        ),
        "forcast_tariff_8": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.32.price",
            name="Zonneplan forcast tariff hour 8",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{ENERGY_KILO_WATT_HOUR}",
        ),
        "forcast_tariff_group_1": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.25.tariff_group",
            name="Zonneplan forcast tariff group hour 1",
            icon="mdi:cash",
        ),
        "forcast_tariff_group_2": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.26.tariff_group",
            name="Zonneplan forcast tariff group hour 2",
        ),
        "forcast_tariff_group_3": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.27.tariff_group",
            name="Zonneplan forcast tariff group hour 3",
        ),
        "forcast_tariff_group_4": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.28.tariff_group",
            name="Zonneplan forcast tariff group hour 4",
        ),
        "forcast_tariff_group_5": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.29.tariff_group",
            name="Zonneplan forcast tariff group hour 5",
        ),
        "forcast_tariff_group_6": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.30.tariff_group",
            name="Zonneplan forcast tariff group hour 6",
        ),
        "forcast_tariff_group_7": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.31.tariff_group",
            name="Zonneplan forcast tariff group hour 7",
        ),
        "forcast_tariff_group_8": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.32.tariff_group",
            name="Zonneplan forcast tariff group hour 8",
        ),
    },
    PV_INSTALL: {
        "install": {
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
                none_value_behaviour=NONE_IS_ZERO,
            ),
            "electricity_last_measured_production_value": ZonneplanSensorEntityDescription(
                key="p1_installation.{install_index}.meta.electricity_last_measured_production_value",
                name="Zonneplan P1 electricity production",
                native_unit_of_measurement=POWER_WATT,
                device_class=SensorDeviceClass.POWER,
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.MEASUREMENT,
                none_value_behaviour=NONE_IS_ZERO,
            ),
            "electricity_last_measured_average_value": ZonneplanSensorEntityDescription(
                key="p1_installation.{install_index}.meta.electricity_last_measured_average_value",
                name="Zonneplan P1 electricity average",
                native_unit_of_measurement=POWER_WATT,
                device_class=SensorDeviceClass.POWER,
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.MEASUREMENT,
                none_value_behaviour=NONE_IS_ZERO,
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
