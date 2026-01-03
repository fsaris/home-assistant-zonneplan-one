"""Constants for the Zonneplan integration."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta, UTC
from typing import Callable

from homeassistant.components.number import NumberEntityDescription, NumberMode
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.components.binary_sensor import (
    BinarySensorEntityDescription,
)
from homeassistant.components.button import (
    ButtonEntityDescription,
)
from homeassistant.const import (
    CURRENCY_EURO,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfVolume,
    UnitOfLength,
    PERCENTAGE,
)

DOMAIN = "zonneplan_one"

GAS = "gas"
ELECTRICITY = "electricity"
PV_INSTALL = "pv_installation"
P1_INSTALL = "p1_installation"
P1_ELECTRICITY = "p1_electricity"
P1_GAS = "p1_gas"
ELECTRICITY_HOME_CONSUMPTION = "electricity_home_consumption"
CHARGE_POINT = "charge_point_installation"
BATTERY = "home_battery_installation"
BATTERY_CONTROL = "battery_control"
BATTERY_CHARTS = "battery_charts"

NONE_IS_ZERO = "none-is-zero"
NONE_USE_PREVIOUS = "none-is-previous"

VERSION = "2026.1.0"


@dataclass
class Attribute:
    key: str
    label: str


@dataclass(frozen=True, kw_only=True)
class ZonneplanSensorEntityDescription(SensorEntityDescription):
    """A class that describes Zonneplan sensor entities."""

    entity_registry_enabled_default: bool = False
    value_factor: float | None = None
    none_value_behaviour: str = ""
    daily_update_hour: int | None = None
    attributes: None | list[Attribute] = None
    last_reset_key: None | str = None
    has_entity_name: bool = True
    key_lambda: Callable[[], str]|None = None


@dataclass(frozen=True, kw_only=True)
class ZonneplanBinarySensorEntityDescription(BinarySensorEntityDescription):
    """A class that describes Zonneplan binary sensor entities."""

    entity_registry_enabled_default: bool = False
    attributes: None | list[Attribute] = None
    has_entity_name: bool = True


@dataclass(frozen=True, kw_only=True)
class ZonneplanButtonEntityDescription(ButtonEntityDescription):
    """A class that describes Zonneplan button entities."""

    entity_registry_enabled_default: bool = True
    has_entity_name: bool = True


@dataclass(frozen=True, kw_only=True)
class ZonneplanNumberEntityDescription(NumberEntityDescription):
    """A class that describes Zonneplan number entities."""

    entity_registry_enabled_default: bool = True
    has_entity_name: bool = True


@dataclass(frozen=True, kw_only=True)
class ZonneplanSelectEntityDescription(SelectEntityDescription):
    """A class that describes Zonneplan select entities."""

    entity_registry_enabled_default: bool = True
    has_entity_name: bool = True


"""Available sensors"""
SENSOR_TYPES: dict[str, dict[str, ZonneplanSensorEntityDescription] | dict[str, dict[str, ZonneplanSensorEntityDescription]]] = {
    ELECTRICITY: {
        "usage": ZonneplanSensorEntityDescription(
            key="usage.value",
            name="Current usage",
            translation_key="usage",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        "usage_measured_at": ZonneplanSensorEntityDescription(
            key="usage.measured_at",
            name="Current usage measured at",
            translation_key="usage_measured_at",
            device_class=SensorDeviceClass.TIMESTAMP,
            icon="mdi:calendar-clock",
        ),
        "sustainability_score": ZonneplanSensorEntityDescription(
            key="usage.sustainability_score",
            name="Sustainability score",
            translation_key="sustainability_score",
            icon="mdi:leaf-circle-outline",
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=True,
            value_factor=0.1,
            native_unit_of_measurement=PERCENTAGE,
        ),
        "current_tariff_group": ZonneplanSensorEntityDescription(
            key="current_tariff_group",
            key_lambda= lambda: f"price_per_date_and_hour.{(datetime.now(UTC)).strftime('%Y-%m-%d %H')}.tariff_group",
            name="Current tariff group",
            translation_key="current_tariff_group",
            entity_registry_enabled_default=True,
        ),
        "current_tariff": ZonneplanSensorEntityDescription(
            key="current_tariff",
            key_lambda= lambda: f"price_per_date_and_hour.{datetime.now(UTC).strftime('%Y-%m-%d %H')}.electricity_price",
            name="Current electricity tariff",
            translation_key="current_electricity_tariff",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
            suggested_display_precision=2,
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=True,
            attributes=[
                Attribute(
                    key="price_per_hour",
                    label="forecast",
                )
            ],
        ),
        "status_message": ZonneplanSensorEntityDescription(
            key="usage.status_message",
            name="Status message",
            translation_key="status_message",
            icon="mdi:message-text-outline",
        ),
        "status_tip": ZonneplanSensorEntityDescription(
            key="usage.status_tip",
            name="Status tip",
            translation_key="status_tip",
            icon="mdi:message-text-outline",
            entity_registry_enabled_default=True,
        ),
        "forcast_tariff_1": ZonneplanSensorEntityDescription(
            key="forcast_tariff_1",
            key_lambda= lambda: f"price_per_date_and_hour.{(datetime.now(UTC) + timedelta(hours=1)).strftime('%Y-%m-%d %H')}.electricity_price",
            name="Forecast tariff hour 1",
            translation_key="forecast_tariff_hour_1",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
            suggested_display_precision=2,
        ),
        "forcast_tariff_2": ZonneplanSensorEntityDescription(
            key="forcast_tariff_2",
            key_lambda= lambda: f"price_per_date_and_hour.{(datetime.now(UTC) + timedelta(hours=2)).strftime('%Y-%m-%d %H')}.electricity_price",
            name="Forecast tariff hour 2",
            translation_key="forecast_tariff_hour_2",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
            suggested_display_precision=2,
        ),
        "forcast_tariff_3": ZonneplanSensorEntityDescription(
            key="forcast_tariff_3",
            key_lambda= lambda: f"price_per_date_and_hour.{(datetime.now(UTC) + timedelta(hours=3)).strftime('%Y-%m-%d %H')}.electricity_price",
            name="Forecast tariff hour 3",
            translation_key="forecast_tariff_hour_3",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
            suggested_display_precision=2,
        ),
        "forcast_tariff_4": ZonneplanSensorEntityDescription(
            key="forcast_tariff_4",
            key_lambda= lambda: f"price_per_date_and_hour.{(datetime.now(UTC) + timedelta(hours=4)).strftime('%Y-%m-%d %H')}.electricity_price",
            name="Forecast tariff hour 4",
            translation_key="forecast_tariff_hour_4",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
            suggested_display_precision=2,
        ),
        "forcast_tariff_5": ZonneplanSensorEntityDescription(
            key="forcast_tariff_5",
            key_lambda= lambda: f"price_per_date_and_hour.{(datetime.now(UTC) + timedelta(hours=5)).strftime('%Y-%m-%d %H')}.electricity_price",
            name="Forecast tariff hour 5",
            translation_key="forecast_tariff_hour_5",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
            suggested_display_precision=2,
        ),
        "forcast_tariff_6": ZonneplanSensorEntityDescription(
            key="forcast_tariff_6",
            key_lambda= lambda: f"price_per_date_and_hour.{(datetime.now(UTC) + timedelta(hours=6)).strftime('%Y-%m-%d %H')}.electricity_price",
            name="Forecast tariff hour 6",
            translation_key="forecast_tariff_hour_6",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
            suggested_display_precision=2,
        ),
        "forcast_tariff_7": ZonneplanSensorEntityDescription(
            key="forcast_tariff_7",
            key_lambda= lambda: f"price_per_date_and_hour.{(datetime.now(UTC) + timedelta(hours=7)).strftime('%Y-%m-%d %H')}.electricity_price",
            name="Forecast tariff hour 7",
            translation_key="forecast_tariff_hour_7",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
            suggested_display_precision=2,
        ),
        "forcast_tariff_8": ZonneplanSensorEntityDescription(
            key="forcast_tariff_8",
            key_lambda= lambda: f"price_per_date_and_hour.{(datetime.now(UTC) + timedelta(hours=8)).strftime('%Y-%m-%d %H')}.electricity_price",
            name="Forecast tariff hour 8",
            translation_key="forecast_tariff_hour_8",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
            suggested_display_precision=2,
        ),
        "forcast_tariff_group_1": ZonneplanSensorEntityDescription(
            key="forcast_tariff_group_1",
            key_lambda= lambda: f"price_per_date_and_hour.{(datetime.now(UTC) + timedelta(hours=1)).strftime('%Y-%m-%d %H')}.tariff_group",
            name="Forecast tariff group hour 1",
            translation_key="forecast_tariff_group_hour_1",
            icon="mdi:cash",
        ),
        "forcast_tariff_group_2": ZonneplanSensorEntityDescription(
            key="forcast_tariff_group_2",
            key_lambda= lambda: f"price_per_date_and_hour.{(datetime.now(UTC) + timedelta(hours=2)).strftime('%Y-%m-%d %H')}.tariff_group",
            name="Forecast tariff group hour 2",
            translation_key="forecast_tariff_group_hour_2",
        ),
        "forcast_tariff_group_3": ZonneplanSensorEntityDescription(
            key="forcast_tariff_group_3",
            key_lambda= lambda: f"price_per_date_and_hour.{(datetime.now(UTC) + timedelta(hours=3)).strftime('%Y-%m-%d %H')}.tariff_group",
            name="Forecast tariff group hour 3",
            translation_key="forecast_tariff_group_hour_3",
        ),
        "forcast_tariff_group_4": ZonneplanSensorEntityDescription(
            key="forcast_tariff_group_4",
            key_lambda= lambda: f"price_per_date_and_hour.{(datetime.now(UTC) + timedelta(hours=4)).strftime('%Y-%m-%d %H')}.tariff_group",
            name="Forecast tariff group hour 4",
            translation_key="forecast_tariff_group_hour_4",
        ),
        "forcast_tariff_group_5": ZonneplanSensorEntityDescription(
            key="forcast_tariff_group_5",
            key_lambda= lambda: f"price_per_date_and_hour.{(datetime.now(UTC) + timedelta(hours=5)).strftime('%Y-%m-%d %H')}.tariff_group",
            name="Forecast tariff group hour 5",
            translation_key="forecast_tariff_group_hour_5",
        ),
        "forcast_tariff_group_6": ZonneplanSensorEntityDescription(
            key="forcast_tariff_group_6",
            key_lambda= lambda: f"price_per_date_and_hour.{(datetime.now(UTC) + timedelta(hours=6)).strftime('%Y-%m-%d %H')}.tariff_group",
            name="Forecast tariff group hour 6",
            translation_key="forecast_tariff_group_hour_6",
        ),
        "forcast_tariff_group_7": ZonneplanSensorEntityDescription(
            key="forcast_tariff_group_7",
            key_lambda= lambda: f"price_per_date_and_hour.{(datetime.now(UTC) + timedelta(hours=7)).strftime('%Y-%m-%d %H')}.tariff_group",
            name="Forecast tariff group hour 7",
            translation_key="forecast_tariff_group_hour_7",
        ),
        "forcast_tariff_group_8": ZonneplanSensorEntityDescription(
            key="forcast_tariff_group_8",
            key_lambda= lambda: f"price_per_date_and_hour.{(datetime.now(UTC) + timedelta(hours=8)).strftime('%Y-%m-%d %H')}.tariff_group",
            name="Forecast tariff group hour 8",
            translation_key="forecast_tariff_group_hour_8",
        ),
    },
    GAS: {
        "current_tariff_gas": ZonneplanSensorEntityDescription(
            key="gas_price",
            name="Current gas tariff",
            translation_key="current_gas_tariff",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfVolume.CUBIC_METERS}",
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=True,
            none_value_behaviour=NONE_USE_PREVIOUS,
            daily_update_hour=6,
            suggested_display_precision=2,
        ),
        "next_tariff_gas": ZonneplanSensorEntityDescription(
            key="gas_price_next",
            name="Next gas tariff",
            translation_key="next_gas_tariff",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfVolume.CUBIC_METERS}",
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=True,
            none_value_behaviour=NONE_USE_PREVIOUS,
            daily_update_hour=6,
            suggested_display_precision=2,
        ),
    },
    PV_INSTALL: {
        "install": {
            "total_power_measured": ZonneplanSensorEntityDescription(
                key="contracts.{install_index}.meta.total_power_measured",
                name="Yield total",
                translation_key="yield_total",
                native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                value_factor=0.001,
                device_class=SensorDeviceClass.ENERGY,
                icon="mdi:solar-power",
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.TOTAL_INCREASING,
            ),
            "last_measured_power_value": ZonneplanSensorEntityDescription(
                key="contracts.{install_index}.meta.last_measured_power_value",
                name="Last measured value",
                translation_key="last_measured_value",
                native_unit_of_measurement=UnitOfPower.WATT,
                device_class=SensorDeviceClass.POWER,
                icon="mdi:solar-power",
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            "first_measured_at": ZonneplanSensorEntityDescription(
                key="contracts.{install_index}.meta.first_measured_at",
                name="First measured",
                translation_key="first_measured",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:calendar-clock",
            ),
            "last_measured_at": ZonneplanSensorEntityDescription(
                key="contracts.{install_index}.meta.last_measured_at",
                name="Last measured",
                translation_key="last_measured",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:calendar-clock",
                entity_registry_enabled_default=True,
            ),
            "total_earned": ZonneplanSensorEntityDescription(
                key="contracts.{install_index}.meta.total_earned",
                name="Powerplay total",
                translation_key="powerplay_total",
                value_factor=0.0000001,
                device_class=SensorDeviceClass.MONETARY,
                native_unit_of_measurement='EUR',
                state_class=SensorStateClass.TOTAL,
                entity_registry_enabled_default=False,
            ),
            "total_day": ZonneplanSensorEntityDescription(
                key="contracts.{install_index}.meta.total_day",
                name="Powerplay today",
                translation_key="powerplay_today",
                value_factor=0.0000001,
                device_class=SensorDeviceClass.MONETARY,
                native_unit_of_measurement='EUR',
                state_class=SensorStateClass.TOTAL,
                last_reset_key="measurement_groups.0.date",
                entity_registry_enabled_default=False,
            ),
        },
        "totals": {
            "total_today": ZonneplanSensorEntityDescription(
                key="measurement_groups.0.total",
                name="Yield today",
                translation_key="yield_today",
                native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                value_factor=0.001,
                device_class=SensorDeviceClass.ENERGY,
                icon="mdi:solar-power",
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.TOTAL_INCREASING,
            ),
        },
    },
    P1_ELECTRICITY: {
        "totals": {
            "electricity_total_today": ZonneplanSensorEntityDescription(
                key="measurement_groups.0.totals.d",
                name="Electricity consumption today",
                translation_key="electricity_consumption_today",
                native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                value_factor=0.001,
                device_class=SensorDeviceClass.ENERGY,
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.TOTAL_INCREASING,
            ),
            "electricity_total_today_returned": ZonneplanSensorEntityDescription(
                key="measurement_groups.0.totals.p",
                name="Electricity returned today",
                translation_key="electricity_returned_today",
                native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                value_factor=0.001,
                device_class=SensorDeviceClass.ENERGY,
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.TOTAL_INCREASING,
            ),
            "electricity_delivery_costs_incl_tax": ZonneplanSensorEntityDescription(
                key="measurement_groups.0.meta.delivery_costs_incl_tax",
                name="Electricity delivery costs today",
                translation_key="electricity_delivery_costs_today",
                value_factor=0.0000001,
                device_class=SensorDeviceClass.MONETARY,
                native_unit_of_measurement='EUR',
                entity_registry_enabled_default=False,
                state_class=SensorStateClass.TOTAL,
                last_reset_key="measurement_groups.0.date",
            ),
            "electricity_delivery_costs_this_month": ZonneplanSensorEntityDescription(
                key="measurement_groups.2.meta.delivery_costs_incl_tax",
                name="Electricity delivery costs this month",
                translation_key="electricity_delivery_costs_this_month",
                native_unit_of_measurement=CURRENCY_EURO,
                device_class=SensorDeviceClass.MONETARY,
                state_class=SensorStateClass.TOTAL,
                value_factor=0.0000001, 
                none_value_behaviour=NONE_IS_ZERO,
                last_reset_key="measurement_groups.2.date",
            ),        
            "electricity_delivery_costs_this_year": ZonneplanSensorEntityDescription(
                key="measurement_groups.3.meta.delivery_costs_incl_tax",
                name="Electricity delivery costs this year",
                translation_key="electricity_delivery_costs_this_year",
                native_unit_of_measurement=CURRENCY_EURO,
                device_class=SensorDeviceClass.MONETARY,
                state_class=SensorStateClass.TOTAL,
                value_factor=0.0000001,
                none_value_behaviour=NONE_IS_ZERO,
                last_reset_key="measurement_groups.3.date",
            ),            
            "electricity_production_costs_incl_tax": ZonneplanSensorEntityDescription(
                key="measurement_groups.0.meta.production_costs_incl_tax",
                name="Electricity production costs today",
                translation_key="electricity_production_costs_today",
                value_factor=0.0000001,
                device_class=SensorDeviceClass.MONETARY,
                native_unit_of_measurement='EUR',
                entity_registry_enabled_default=False,
                state_class=SensorStateClass.TOTAL,
                last_reset_key="measurement_groups.0.date",
                none_value_behaviour=NONE_IS_ZERO,
            ),
            "electricity_production_costs_this_month": ZonneplanSensorEntityDescription(
                key="measurement_groups.2.meta.production_costs_incl_tax",
                name="Electricity production costs this month",
                translation_key="electricity_production_costs_this_month",
                native_unit_of_measurement=CURRENCY_EURO,
                device_class=SensorDeviceClass.MONETARY,
                state_class=SensorStateClass.TOTAL,
                value_factor=0.0000001,
                none_value_behaviour=NONE_IS_ZERO,
                last_reset_key="measurement_groups.2.date",
            ),
            "electricity_production_costs_this_year": ZonneplanSensorEntityDescription(
                key="measurement_groups.3.meta.production_costs_incl_tax",
                name="Electricity production costs this year",
                translation_key="electricity_production_costs_this_year",
                native_unit_of_measurement=CURRENCY_EURO,
                device_class=SensorDeviceClass.MONETARY,
                state_class=SensorStateClass.TOTAL,
                value_factor=0.0000001,
                none_value_behaviour=NONE_IS_ZERO,
                last_reset_key="measurement_groups.3.date",
            ),
        },
        "install": {
            "electricity_last_measured_delivery_value": ZonneplanSensorEntityDescription(
                key="contracts.{install_index}.meta.electricity_last_measured_delivery_value",
                name="Electricity consumption",
                translation_key="electricity_consumption",
                native_unit_of_measurement=UnitOfPower.WATT,
                device_class=SensorDeviceClass.POWER,
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.MEASUREMENT,
                none_value_behaviour=NONE_IS_ZERO,
            ),
            "electricity_last_measured_production_value": ZonneplanSensorEntityDescription(
                key="contracts.{install_index}.meta.electricity_last_measured_production_value",
                name="Electricity production",
                translation_key="electricity_production",
                native_unit_of_measurement=UnitOfPower.WATT,
                device_class=SensorDeviceClass.POWER,
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.MEASUREMENT,
                none_value_behaviour=NONE_IS_ZERO,
            ),
            "electricity_last_measured_average_value": ZonneplanSensorEntityDescription(
                key="contracts.{install_index}.meta.electricity_last_measured_average_value",
                name="Electricity average",
                translation_key="electricity_average",
                native_unit_of_measurement=UnitOfPower.WATT,
                device_class=SensorDeviceClass.POWER,
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.MEASUREMENT,
                none_value_behaviour=NONE_IS_ZERO,
            ),
            "electricity_first_measured_at": ZonneplanSensorEntityDescription(
                key="contracts.{install_index}.meta.electricity_first_measured_at",
                name="Electricity first measured",
                translation_key="electricity_first_measured",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:calendar-clock",
            ),
            "electricity_last_measured_at": ZonneplanSensorEntityDescription(
                key="contracts.{install_index}.meta.electricity_last_measured_at",
                name="Electricity last measured",
                translation_key="electricity_last_measured",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:calendar-clock",
                entity_registry_enabled_default=True,
            ),
            "electricity_last_measured_production_at": ZonneplanSensorEntityDescription(
                key="contracts.{install_index}.meta.electricity_last_measured_production_at",
                name="Electricity last measured production",
                translation_key="electricity_last_measured_production",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:calendar-clock",
                entity_registry_enabled_default=True,
            ),
            "dsmr_version": ZonneplanSensorEntityDescription(
                key="contracts.{install_index}.meta.dsmr_version",
                name="Dsmr version",
                translation_key="dsmr_version",
                icon="mdi:meter-electric",
            ),
        },
    },
    P1_GAS: {
        "totals": {
            "gas_total_today": ZonneplanSensorEntityDescription(
                key="measurement_groups.0.total",
                name="Gas consumption today",
                translation_key="gas_consumption_today",
                native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
                value_factor=0.001,
                device_class=SensorDeviceClass.GAS,
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.TOTAL_INCREASING,
            ),
            "gas_delivery_costs_incl_tax": ZonneplanSensorEntityDescription(
                key="measurement_groups.0.meta.delivery_costs_incl_tax",
                name="Gas delivery costs today",
                translation_key="gas_delivery_costs_today",
                value_factor=0.0000001,
                device_class=SensorDeviceClass.MONETARY,
                native_unit_of_measurement='EUR',
                entity_registry_enabled_default=False,
                state_class=SensorStateClass.TOTAL,
                last_reset_key="measurement_groups.0.date",
            ),
        },
        "install": {
            "gas_first_measured_at": ZonneplanSensorEntityDescription(
                key="contracts.{install_index}.meta.gas_first_measured_at",
                name="Gas first measured",
                translation_key="gas_first_measured",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:calendar-clock",
            ),
            "gas_last_measured_at": ZonneplanSensorEntityDescription(
                key="contracts.{install_index}.meta.gas_last_measured_at",
                name="Gas last measured",
                translation_key="gas_last_measured",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:calendar-clock",
                entity_registry_enabled_default=True,
            ),
        },
    },
    BATTERY_CONTROL: {
        "battery_control_mode": ZonneplanSensorEntityDescription(
            key="battery_control_mode.control_mode",
            name="Battery control mode",
            translation_key="battery_control_mode",
            entity_registry_enabled_default=False,
        ),
    },
    BATTERY: {
        "battery_state": ZonneplanSensorEntityDescription(
            key="contracts.{install_index}.meta.battery_state",
            name="Battery state",
            translation_key="battery_state",
            entity_registry_enabled_default=True,
        ),
        "state_of_charge": ZonneplanSensorEntityDescription(
            key="contracts.{install_index}.meta.state_of_charge",
            name="Percentage",
            translation_key="state_of_charge",
            device_class=SensorDeviceClass.BATTERY,
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=True,
            value_factor=0.1,
            native_unit_of_measurement=PERCENTAGE,
        ),
        "power_ac": ZonneplanSensorEntityDescription(
            key="contracts.{install_index}.meta.power_ac",
            name="Power",
            translation_key="power",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        "inverter_state": ZonneplanSensorEntityDescription(
            key="contracts.{install_index}.meta.inverter_state",
            name="Inverter state",
            translation_key="inverter_state",
        ),
        "total_earned": ZonneplanSensorEntityDescription(
            key="contracts.{install_index}.meta.total_earned",
            name="Total",
            translation_key="total_earned",
            value_factor=0.0000001,
            device_class=SensorDeviceClass.MONETARY,
            native_unit_of_measurement='EUR',
            state_class=SensorStateClass.TOTAL,
            entity_registry_enabled_default=True,
        ),
        "total_day": ZonneplanSensorEntityDescription(
            key="contracts.{install_index}.meta.total_day",
            name="Today",
            translation_key="total_day",
            value_factor=0.0000001,
            device_class=SensorDeviceClass.MONETARY,
            native_unit_of_measurement='EUR',
            state_class=SensorStateClass.TOTAL,
            last_reset_key="measurement_groups.0.date",
            entity_registry_enabled_default=True,
        ),
        "average_day": ZonneplanSensorEntityDescription(
            key="contracts.{install_index}.meta.average_day",
            name="Average day",
            translation_key="average_day",
            value_factor=0.0000001,
            device_class=SensorDeviceClass.MONETARY,
            native_unit_of_measurement='EUR',
            state_class=SensorStateClass.TOTAL,
            last_reset_key="measurement_groups.0.date",
            entity_registry_enabled_default=True,
        ),
        "delivery_day": ZonneplanSensorEntityDescription(
            key="contracts.{install_index}.meta.delivery_day",
            name="Delivery today",
            translation_key="delivery_today",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            value_factor=0.001,
            device_class=SensorDeviceClass.ENERGY,
            entity_registry_enabled_default=True,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        "production_day": ZonneplanSensorEntityDescription(
            key="contracts.{install_index}.meta.production_day",
            name="Production today",
            translation_key="production_today",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            value_factor=0.001,
            device_class=SensorDeviceClass.ENERGY,
            entity_registry_enabled_default=True,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        "first_measured_at": ZonneplanSensorEntityDescription(
            key="contracts.{install_index}.meta.first_measured_at",
            name="First measured",
            translation_key="first_measured",
            device_class=SensorDeviceClass.TIMESTAMP,
            icon="mdi:calendar-clock",
        ),
        "last_measured_at": ZonneplanSensorEntityDescription(
            key="contracts.{install_index}.meta.last_measured_at",
            name="Last measured",
            translation_key="last_measured",
            device_class=SensorDeviceClass.TIMESTAMP,
            icon="mdi:calendar-clock",
            entity_registry_enabled_default=True,
        ),
        "cycle_count": ZonneplanSensorEntityDescription(
            key="contracts.{install_index}.meta.cycle_count",
            name="Battery cycles",
            translation_key="battery_cycles",
            icon="mdi:battery-sync",
            entity_registry_enabled_default=True,
            state_class=SensorStateClass.TOTAL,
        ),
    },
    BATTERY_CHARTS: {
        "result_this_year": ZonneplanSensorEntityDescription(
            key="this_year.total_result",
            name="Result this year",
            translation_key="result_this_year",
            device_class=SensorDeviceClass.MONETARY,
            native_unit_of_measurement='EUR',
            state_class=SensorStateClass.TOTAL,
            entity_registry_enabled_default=True,
            attributes=[
                Attribute(
                    key="this_year.year",
                    label="year",
                ),
                Attribute(
                    key="this_year.total_delivery_kwh",
                    label="total_delivery_kwh",
                ),
                Attribute(
                    key="this_year.total_production_kwh",
                    label="total_production_kwh",
                ),
                Attribute(
                    key="this_year.months",
                    label="months",
                ),
            ],
        ),
        "result_last_year": ZonneplanSensorEntityDescription(
            key="last_year.total_result",
            name="Result last year",
            translation_key="result_last_year",
            device_class=SensorDeviceClass.MONETARY,
            native_unit_of_measurement='EUR',
            state_class=SensorStateClass.TOTAL,
            entity_registry_enabled_default=True,
            attributes=[
                Attribute(
                    key="last_year.year",
                    label="year",
                ),
                Attribute(
                    key="last_year.total_delivery_kwh",
                    label="total_delivery_kwh",
                ),
                Attribute(
                    key="last_year.total_production_kwh",
                    label="total_production_kwh",
                ),
                Attribute(
                    key="last_year.months",
                    label="months",
                ),
            ],
        ),
        "result_this_month": ZonneplanSensorEntityDescription(
            key="this_month.total_result",
            name="Result this month",
            translation_key="result_this_month",
            device_class=SensorDeviceClass.MONETARY,
            native_unit_of_measurement='EUR',
            state_class=SensorStateClass.TOTAL,
            entity_registry_enabled_default=True,
            attributes=[
                Attribute(
                    key="this_month.month",
                    label="month",
                ),
                Attribute(
                    key="this_month.total_delivery_kwh",
                    label="total_delivery_kwh",
                ),
                Attribute(
                    key="this_month.total_production_kwh",
                    label="total_production_kwh",
                ),
                Attribute(
                    key="this_month.days",
                    label="days",
                ),
            ],
        ),
        "result_last_month": ZonneplanSensorEntityDescription(
            key="last_month.total_result",
            name="Result last month",
            translation_key="result_last_month",
            device_class=SensorDeviceClass.MONETARY,
            native_unit_of_measurement='EUR',
            state_class=SensorStateClass.TOTAL,
            entity_registry_enabled_default=True,
            attributes=[
                Attribute(
                    key="last_month.month",
                    label="month",
                ),
                Attribute(
                    key="last_month.total_delivery_kwh",
                    label="total_delivery_kwh",
                ),
                Attribute(
                    key="last_month.total_production_kwh",
                    label="total_production_kwh",
                ),
                Attribute(
                    key="last_month.days",
                    label="days",
                ),
            ],
        ),
    },
    ELECTRICITY_HOME_CONSUMPTION: {
        "delivery_costs_this_month": ZonneplanSensorEntityDescription(
            key="measurement_groups.2.meta.delivery_costs_incl_tax",
            name="Net delivery costs this month",
            translation_key="delivery_costs_this_month",
            native_unit_of_measurement=CURRENCY_EURO,
            device_class=SensorDeviceClass.MONETARY,
            state_class=SensorStateClass.TOTAL,
            value_factor=0.0000001,
            none_value_behaviour=NONE_IS_ZERO,
            last_reset_key="measurement_groups.2.date",
        ),
        "delivery_costs_this_year": ZonneplanSensorEntityDescription(
            key="measurement_groups.3.meta.delivery_costs_incl_tax",
            name="Net delivery costs this year",
            translation_key="delivery_costs_this_year",
            native_unit_of_measurement=CURRENCY_EURO,
            device_class=SensorDeviceClass.MONETARY,
            state_class=SensorStateClass.TOTAL,
            value_factor=0.0000001,
            none_value_behaviour=NONE_IS_ZERO,
            last_reset_key="measurement_groups.3.date",
        ),
        "production_costs_this_month": ZonneplanSensorEntityDescription(
            key="measurement_groups.2.meta.production_costs_incl_tax",
            name="Net production costs this month",
            translation_key="production_costs_this_month",
            native_unit_of_measurement=CURRENCY_EURO,
            device_class=SensorDeviceClass.MONETARY,
            state_class=SensorStateClass.TOTAL,
            value_factor=0.0000001,
            none_value_behaviour=NONE_IS_ZERO,
            last_reset_key="measurement_groups.2.date",
        ),
        "production_costs_this_year": ZonneplanSensorEntityDescription(
            key="measurement_groups.3.meta.production_costs_incl_tax",
            name="Net production costs this year",
            translation_key="production_costs_this_year",
            native_unit_of_measurement=CURRENCY_EURO,
            device_class=SensorDeviceClass.MONETARY,
            state_class=SensorStateClass.TOTAL,
            value_factor=0.0000001,
            none_value_behaviour=NONE_IS_ZERO,
            last_reset_key="measurement_groups.3.date",
        ),
        "energy_delivered_sum_today": ZonneplanSensorEntityDescription(
            key="measurement_groups.2.measurements.-1.values.d",
            name="Net delivery today",
            translation_key="energy_delivered_sum_today",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            value_factor=0.001,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            entity_registry_enabled_default=True,
        ),
        "energy_delivered_sum_this_month": ZonneplanSensorEntityDescription(
            key="measurement_groups.2.meta.energy_delivered_sum",
            name="Net delivery this month",
            translation_key="energy_delivered_sum_this_month",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            value_factor=0.001,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            entity_registry_enabled_default=True,
        ),
        "energy_delivered_sum_this_year": ZonneplanSensorEntityDescription(
            key="measurement_groups.3.meta.energy_delivered_sum",
            name="Net delivery this year",
            translation_key="energy_delivered_sum_this_year",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            value_factor=0.001,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            entity_registry_enabled_default=True,
        ),
        "energy_produced_sum_today": ZonneplanSensorEntityDescription(
            key="measurement_groups.2.measurements.-1.values.p",
            name="Net production today",
            translation_key="energy_produced_sum_today",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            value_factor=0.001,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            entity_registry_enabled_default=True,
        ),
        "energy_produced_sum_this_month": ZonneplanSensorEntityDescription(
            key="measurement_groups.2.meta.energy_produced_sum",
            name="Net production this month",
            translation_key="energy_produced_sum_this_month",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            value_factor=0.001,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            entity_registry_enabled_default=True,
        ),
        "energy_produced_sum_this_year": ZonneplanSensorEntityDescription(
            key="measurement_groups.3.meta.energy_produced_sum",
            name="Net production this year",
            translation_key="energy_produced_sum_this_year",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            value_factor=0.001,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL_INCREASING,
            entity_registry_enabled_default=True,
        ),
    },
    CHARGE_POINT: {
        "state": ZonneplanSensorEntityDescription(
            key="state.state",
            name="Charge point state",
            translation_key="charge_point_state",
            entity_registry_enabled_default=True,
            attributes=[
                Attribute(
                    key="state",
                    label="state",
                ),
                Attribute(
                    key="charge_schedules",
                    label="charge schedules",
                ),
            ],
        ),
        "power_actual": ZonneplanSensorEntityDescription(
            key="state.power_actual",
            name="Charge point power",
            translation_key="charge_point_power",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        "energy_delivered_session": ZonneplanSensorEntityDescription(
            key="state.energy_delivered_session",
            name="Charge point energy delivered session",
            translation_key="charge_point_energy_delivered_session",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            value_factor=0.001,
            device_class=SensorDeviceClass.ENERGY,
            entity_registry_enabled_default=True,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        "session_charging_cost_total": ZonneplanSensorEntityDescription(
            key="meta.session_charging_cost_total",
            name="Charge point session cost",
            translation_key="charge_point_session_cost",
            value_factor=0.0000001,
            icon="mdi:cash",
            native_unit_of_measurement='EUR',
            entity_registry_enabled_default=True,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        "charging_cost_total": ZonneplanSensorEntityDescription(
            key="meta.charging_cost_total",
            name="Charge point cost total",
            translation_key="charge_point_cost_total",
            value_factor=0.0000001,
            icon="mdi:cash",
            native_unit_of_measurement='EUR',
            entity_registry_enabled_default=True,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        "session_flex_result": ZonneplanSensorEntityDescription(
            key="meta.session_flex_result",
            name="Charge point session flex result",
            translation_key="charge_point_session_flex_result",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement='EUR',
            state_class=SensorStateClass.TOTAL_INCREASING,
            entity_registry_enabled_default=True,
            none_value_behaviour=NONE_IS_ZERO,
        ),
        "session_average_cost_in_cents": ZonneplanSensorEntityDescription(
            key="meta.session_average_cost_in_cents",
            name="Charge point session average costs",
            translation_key="charge_point_session_average_costs",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=True,
        ),
        "charge_schedules.start_time": ZonneplanSensorEntityDescription(
            key="charge_schedules.0.start_time",
            name="Charge point next schedule start",
            translation_key="charge_point_next_schedule_start",
            device_class=SensorDeviceClass.TIMESTAMP,
            icon="mdi:calendar-clock",
            entity_registry_enabled_default=True,
        ),
        "charge_schedules.end_time": ZonneplanSensorEntityDescription(
            key="charge_schedules.0.end_time",
            name="Charge point next schedule end",
            translation_key="charge_point_next_schedule_end",
            device_class=SensorDeviceClass.TIMESTAMP,
            icon="mdi:calendar-clock",
            entity_registry_enabled_default=True,
        ),
        "dynamic_load_balancing_health": ZonneplanSensorEntityDescription(
            key="state.dynamic_load_balancing_health",
            name="Charge point dynamic load balancing health",
            translation_key="charge_point_dynamic_load_balancing_health",
        ),
        "start_mode": ZonneplanSensorEntityDescription(
            key="state.start_mode",
            name="Charge point start mode",
            translation_key="charge_point_start_mode",
        ),
        "dynamic_charging_user_constraints.desired_distance_in_kilometers": ZonneplanSensorEntityDescription(
            key="state.dynamic_charging_user_constraints.desired_distance_in_kilometers",
            name="Charge point dynamic load desired distance",
            translation_key="charge_point_dynamic_load_desired_distance",
            native_unit_of_measurement=UnitOfLength.KILOMETERS,
            entity_registry_enabled_default=True,
        ),
        "dynamic_charging_user_constraints.desired_end_time": ZonneplanSensorEntityDescription(
            key="state.dynamic_charging_user_constraints.desired_end_time",
            name="Charge point dynamic load desired end time",
            translation_key="charge_point_dynamic_load_desired_end_time",
            device_class=SensorDeviceClass.TIMESTAMP,
            icon="mdi:calendar-clock",
            entity_registry_enabled_default=True,
        ),
        "charge_point_session.start_time": ZonneplanSensorEntityDescription(
            key="state.charge_point_session.start_time",
            name="Charge point session start time",
            translation_key="charge_point_session_start_time",
            device_class=SensorDeviceClass.TIMESTAMP,
            icon="mdi:calendar-clock",
            entity_registry_enabled_default=True,
        ),
        "charge_point_session.charged_distance_in_kilometers": ZonneplanSensorEntityDescription(
            key="state.charge_point_session.charged_distance_in_kilometers",
            name="Charge point session charged distance",
            translation_key="charge_point_session_charged_distance",
            native_unit_of_measurement=UnitOfLength.KILOMETERS,
            entity_registry_enabled_default=True,
        ),
    },
}

BINARY_SENSORS_TYPES: dict[str, dict[str, ZonneplanBinarySensorEntityDescription]] = {
    BATTERY: {
        "dynamic_charging_enabled": ZonneplanBinarySensorEntityDescription(
            key="contracts.{install_index}.meta.dynamic_charging_enabled",
            name="Dynamic charging enabled",
            translation_key="dynamic_charging_enabled",
            entity_registry_enabled_default=True,
        ),
        "dynamic_load_balancing_enabled": ZonneplanBinarySensorEntityDescription(
            key="contracts.{install_index}.meta.dynamic_load_balancing_enabled",
            name="Dynamic load balancing enabled",
            translation_key="dynamic_load_balancing_enabled",
            entity_registry_enabled_default=True,
        ),
        "dynamic_load_balancing_overload_active": ZonneplanBinarySensorEntityDescription(
            key="contracts.{install_index}.meta.dynamic_load_balancing_overload_active",
            name="Dynamic load balancing overload active",
            translation_key="dynamic_load_balancing_overload_active",
            entity_registry_enabled_default=True,
        ),
        "manual_control_enabled": ZonneplanBinarySensorEntityDescription(
            key="contracts.{install_index}.meta.manual_control_enabled",
            name="Manual control enabled",
            translation_key="manual_control_enabled",
            entity_registry_enabled_default=True,
        ),
        "self_consumption_enabled": ZonneplanBinarySensorEntityDescription(
            key="contracts.{install_index}.meta.self_consumption_enabled",
            name="Self consumption enabled",
            translation_key="self_consumption_enabled",
            entity_registry_enabled_default=True,
        ),
        "home_optimization_enabled": ZonneplanBinarySensorEntityDescription(
            key="contracts.{install_index}.meta.home_optimization_enabled",
            name="Home optimization enabled",
            translation_key="home_optimization_enabled",
            entity_registry_enabled_default=True,
        ),
        "home_optimization_active": ZonneplanBinarySensorEntityDescription(
            key="contracts.{install_index}.meta.home_optimization_active",
            name="Home optimization active",
            translation_key="home_optimization_active",
            entity_registry_enabled_default=True,
        ),
        "grid_congestion_active": ZonneplanBinarySensorEntityDescription(
            key="contracts.{install_index}.meta.grid_congestion_active",
            name="Grid congestion active",
            translation_key="grid_congestion_active",
            entity_registry_enabled_default=True,
        ),
    },
    PV_INSTALL: {
        "dynamic_control_enabled": ZonneplanBinarySensorEntityDescription(
            key="contracts.{install_index}.meta.dynamic_control_enabled",
            name="Powerplay enabled",
            translation_key="powerplay_enabled",
            entity_registry_enabled_default=False,
        ),
        "power_limit_active": ZonneplanBinarySensorEntityDescription(
            key="contracts.{install_index}.meta.power_limit_active",
            name="Power limit active",
            translation_key="power_limit_active",
            entity_registry_enabled_default=False,
        ),
    },
    CHARGE_POINT: {
        "connectivity_state": ZonneplanBinarySensorEntityDescription(
            key="state.connectivity_state",
            name="Charge point connectivity state",
            translation_key="charge_point_connectivity_state",
            entity_registry_enabled_default=True,
        ),
        "can_charge": ZonneplanBinarySensorEntityDescription(
            key="state.can_charge",
            name="Charge point can charge",
            translation_key="charge_point_can_charge",
            entity_registry_enabled_default=True,
        ),
        "can_schedule": ZonneplanBinarySensorEntityDescription(
            key="state.can_schedule",
            name="Charge point can schedule",
            translation_key="charge_point_can_schedule",
            entity_registry_enabled_default=True,
        ),
        "charging_manually": ZonneplanBinarySensorEntityDescription(
            key="state.charging_manually",
            name="Charge point charging manually",
            translation_key="charge_point_charging_manually",
            entity_registry_enabled_default=True,
        ),
        "charging_automatically": ZonneplanBinarySensorEntityDescription(
            key="state.charging_automatically",
            name="Charge point charging automatically",
            translation_key="charge_point_charging_automatically",
            entity_registry_enabled_default=True,
        ),
        "plug_and_charge": ZonneplanBinarySensorEntityDescription(
            key="state.plug_and_charge",
            name="Charge point plug and charge",
            translation_key="charge_point_plug_and_charge",
            entity_registry_enabled_default=True,
        ),
        "overload_protection_active": ZonneplanBinarySensorEntityDescription(
            key="state.overload_protection_active",
            name="Charge point overload protection active",
            translation_key="charge_point_overload_protection_active",
        ),
        "dynamic_charging_enabled": ZonneplanBinarySensorEntityDescription(
            key="state.dynamic_charging_enabled",
            name="Charge point dynamic charging enabled",
            translation_key="charge_point_dynamic_charging_enabled",
            entity_registry_enabled_default=True,
        ),
        "dynamic_charging_flex_enabled": ZonneplanBinarySensorEntityDescription(
            key="state.dynamic_charging_flex_enabled",
            name="Charge point dynamic charging flex enabled",
            translation_key="charge_point_dynamic_charging_flex_enabled",
            entity_registry_enabled_default=True,
        ),
        "dynamic_charging_flex_suppressed": ZonneplanBinarySensorEntityDescription(
            key="state.dynamic_charging_flex_suppressed",
            name="Charge point dynamic charging flex suppressed",
            translation_key="charge_point_dynamic_charging_flex_suppressed",
        ),
    }
}

BUTTON_TYPES: dict[str, dict[str, ZonneplanButtonEntityDescription]] = {
    CHARGE_POINT: {
        "start": ZonneplanButtonEntityDescription(
            key="charge_point.start",
            name="Start charge",
            translation_key="start_charge",
        ),
        "stop": ZonneplanButtonEntityDescription(
            key="charge_point.stop",
            name="Stop charge",
            translation_key="stop_charge",
        ),
    },
}

NUMBER_TYPES: dict[str, dict[str, ZonneplanNumberEntityDescription]] = {
    BATTERY_CONTROL: {
        "max_desired_discharge_power_watts": ZonneplanNumberEntityDescription(
            key="battery_home_optimization.max_desired_discharge_power_watts",
            name="Max discharge power (Home optimization)",
            translation_key="max_discharge_power",
            mode=NumberMode.SLIDER,
            native_step=100,
            icon="mdi:battery-arrow-down-outline",
        ),
        "max_desired_charge_power_watts": ZonneplanNumberEntityDescription(
            key="battery_home_optimization.max_desired_charge_power_watts",
            name="Max charge power (Home optimization)",
            translation_key="max_charge_power",
            mode=NumberMode.SLIDER,
            native_step=100,
            icon="mdi:battery-arrow-up-outline",
        ),
    }
}

SELECT_TYPES = {
    BATTERY_CONTROL: {
        "control_mode": ZonneplanSelectEntityDescription(
            key="battery_control_mode.control_mode",
            name="Battery control mode",
            translation_key="battery_control_mode",
            icon="mdi:battery-sync-outline",
        )
    }
}
