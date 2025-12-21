"""Constants for the Zonneplan integration."""
from __future__ import annotations
from dataclasses import dataclass

from voluptuous.validators import Number
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

SUMMARY = "summary_data"
PV_INSTALL = "pv_installation"
P1_INSTALL = "p1_installation"
CHARGE_POINT = "charge_point_installation"
BATTERY = "home_battery_installation"

NONE_IS_ZERO = "none-is-zero"
NONE_USE_PREVIOUS = "none-is-previous"

VERSION = "2025.12.0"

@dataclass
class Attribute:
    key: str
    label: str


@dataclass
class ZonneplanSensorEntityDescription(SensorEntityDescription):
    """A class that describes Zonneplan sensor entities."""

    entity_registry_enabled_default: bool = False
    value_factor: Number = None
    none_value_behaviour: str = ""
    daily_update_hour: None | Number = None
    attributes: None | list[Attribute] = None
    last_reset_key: None | str = None
    has_entity_name: bool = True


@dataclass
class ZonneplanBinarySensorEntityDescription(BinarySensorEntityDescription):
    """A class that describes Zonneplan binary sensor entities."""

    entity_registry_enabled_default: bool = False
    attributes: None | list[Attribute] = None
    has_entity_name: bool = True


@dataclass
class ZonneplanButtonEntityDescription(ButtonEntityDescription):
    """A class that describes Zonneplan button entities."""

    entity_registry_enabled_default: bool = True
    has_entity_name: bool = True


"""Available sensors"""
SENSOR_TYPES: dict[str, list[ZonneplanSensorEntityDescription]] = {
    SUMMARY: {
        "usage": ZonneplanSensorEntityDescription(
            key="summary_data.usage.value",
            name="Current usage",
            native_unit_of_measurement=UnitOfPower.WATT,
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
            native_unit_of_measurement=PERCENTAGE,
        ),
        "current_tariff_group": ZonneplanSensorEntityDescription(
            key="summary_data.usage.type",
            name="Current tariff group",
        ),
        "current_tariff": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.24.electricity_price",
            name="Current electricity tariff",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=True,
            attributes=[
                Attribute(
                    key="summary_data.price_per_hour",
                    label="forecast",
                )
            ],
        ),
        "current_tariff_gas": ZonneplanSensorEntityDescription(
            key="summary_data.gas_price",
            name="Current gas tariff",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfVolume.CUBIC_METERS}",
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=True,
            none_value_behaviour=NONE_USE_PREVIOUS,
            daily_update_hour=6,
        ),
        "next_tariff_gas": ZonneplanSensorEntityDescription(
            key="summary_data.gas_price_next",
            name="Next gas tariff",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfVolume.CUBIC_METERS}",
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=True,
            none_value_behaviour=NONE_USE_PREVIOUS,
            daily_update_hour=6,
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
        "forcast_tariff_1": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.25.electricity_price",
            name="Forecast tariff hour 1",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        ),
        "forcast_tariff_2": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.26.electricity_price",
            name="Forecast tariff hour 2",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        ),
        "forcast_tariff_3": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.27.electricity_price",
            name="Forecast tariff hour 3",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        ),
        "forcast_tariff_4": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.28.electricity_price",
            name="Forecast tariff hour 4",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        ),
        "forcast_tariff_5": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.29.electricity_price",
            name="Forecast tariff hour 5",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        ),
        "forcast_tariff_6": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.30.electricity_price",
            name="Forecast tariff hour 6",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        ),
        "forcast_tariff_7": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.31.electricity_price",
            name="Forecast tariff hour 7",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        ),
        "forcast_tariff_8": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.32.electricity_price",
            name="Forecast tariff hour 8",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
        ),
        "forcast_tariff_group_1": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.25.tariff_group",
            name="Forecast tariff group hour 1",
            icon="mdi:cash",
        ),
        "forcast_tariff_group_2": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.26.tariff_group",
            name="Forecast tariff group hour 2",
        ),
        "forcast_tariff_group_3": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.27.tariff_group",
            name="Forecast tariff group hour 3",
        ),
        "forcast_tariff_group_4": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.28.tariff_group",
            name="Forecast tariff group hour 4",
        ),
        "forcast_tariff_group_5": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.29.tariff_group",
            name="Forecast tariff group hour 5",
        ),
        "forcast_tariff_group_6": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.30.tariff_group",
            name="Forecast tariff group hour 6",
        ),
        "forcast_tariff_group_7": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.31.tariff_group",
            name="Forecast tariff group hour 7",
        ),
        "forcast_tariff_group_8": ZonneplanSensorEntityDescription(
            key="summary_data.price_per_hour.32.tariff_group",
            name="Forecast tariff group hour 8",
        ),
    },
    PV_INSTALL: {
        "install": {
            "total_power_measured": ZonneplanSensorEntityDescription(
                key="pv_data.contracts.{install_index}.meta.total_power_measured",
                name="Yield total",
                native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                value_factor=0.001,
                device_class=SensorDeviceClass.ENERGY,
                icon="mdi:solar-power",
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.TOTAL_INCREASING,
            ),
            "last_measured_power_value": ZonneplanSensorEntityDescription(
                key="pv_data.contracts.{install_index}.meta.last_measured_power_value",
                name="Last measured value",
                native_unit_of_measurement=UnitOfPower.WATT,
                device_class=SensorDeviceClass.POWER,
                icon="mdi:solar-power",
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.MEASUREMENT,
            ),
            "first_measured_at": ZonneplanSensorEntityDescription(
                key="pv_data.contracts.{install_index}.meta.first_measured_at",
                name="First measured",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:calendar-clock",
            ),
            "last_measured_at": ZonneplanSensorEntityDescription(
                key="pv_data.contracts.{install_index}.meta.last_measured_at",
                name="Last measured",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:calendar-clock",
                entity_registry_enabled_default=True,
            ),
            "total_earned": ZonneplanSensorEntityDescription(
                key="pv_data.contracts.{install_index}.meta.total_earned",
                name="Powerplay total",
                value_factor=0.0000001,
                device_class=SensorDeviceClass.MONETARY,
                native_unit_of_measurement='EUR',
                state_class=SensorStateClass.TOTAL,
                entity_registry_enabled_default=False,
            ),
            "total_day": ZonneplanSensorEntityDescription(
                key="pv_data.contracts.{install_index}.meta.total_day",
                name="Powerplay today",
                value_factor=0.0000001,
                device_class=SensorDeviceClass.MONETARY,
                native_unit_of_measurement='EUR',
                state_class=SensorStateClass.TOTAL,
                last_reset_key="pv_data.measurement_groups.0.date",
                entity_registry_enabled_default=False,
            ),
        },
        "totals": {
            "total_today": ZonneplanSensorEntityDescription(
                key="pv_data.measurement_groups.0.total",
                name="Yield today",
                native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
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
                key="electricity_data.measurement_groups.0.totals.d",
                name="Electricity consumption today",
                native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                value_factor=0.001,
                device_class=SensorDeviceClass.ENERGY,
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.TOTAL_INCREASING,
            ),
            "electricity_total_today_returned": ZonneplanSensorEntityDescription(
                key="electricity_data.measurement_groups.0.totals.p",
                name="Electricity returned today",
                native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                value_factor=0.001,
                device_class=SensorDeviceClass.ENERGY,
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.TOTAL_INCREASING,
            ),
            "electricity_delivery_costs_incl_tax": ZonneplanSensorEntityDescription(
                key="electricity_data.measurement_groups.0.meta.delivery_costs_incl_tax",
                name="Electricity delivery costs today",
                value_factor=0.0000001,
                device_class=SensorDeviceClass.MONETARY,
                native_unit_of_measurement='EUR',
                entity_registry_enabled_default=False,
                state_class=SensorStateClass.TOTAL,
                last_reset_key="electricity_data.measurement_groups.0.date",
            ),
            "electricity_production_costs_incl_tax": ZonneplanSensorEntityDescription(
                key="electricity_data.measurement_groups.0.meta.production_costs_incl_tax",
                name="Electricity production costs today",
                value_factor=0.0000001,
                device_class=SensorDeviceClass.MONETARY,
                native_unit_of_measurement='EUR',
                entity_registry_enabled_default=False,
                state_class=SensorStateClass.TOTAL,
                last_reset_key="electricity_data.measurement_groups.0.date",
                none_value_behaviour=NONE_IS_ZERO,
            ),
            "gas_total_today": ZonneplanSensorEntityDescription(
                key="gas_data.measurement_groups.0.total",
                name="Gas consumption today",
                native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
                value_factor=0.001,
                device_class=SensorDeviceClass.GAS,
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.TOTAL_INCREASING,
            ),
            "gas_delivery_costs_incl_tax": ZonneplanSensorEntityDescription(
                key="gas_data.measurement_groups.0.meta.delivery_costs_incl_tax",
                name="Gas delivery costs today",
                value_factor=0.0000001,
                device_class=SensorDeviceClass.MONETARY,
                native_unit_of_measurement='EUR',
                entity_registry_enabled_default=False,
                state_class=SensorStateClass.TOTAL,
                last_reset_key="gas_data.measurement_groups.0.date",
            ),
        },
        "install": {
            "electricity_last_measured_delivery_value": ZonneplanSensorEntityDescription(
                key="electricity_data.contracts.{install_index}.meta.electricity_last_measured_delivery_value",
                name="Electricity consumption",
                native_unit_of_measurement=UnitOfPower.WATT,
                device_class=SensorDeviceClass.POWER,
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.MEASUREMENT,
                none_value_behaviour=NONE_IS_ZERO,
            ),
            "electricity_last_measured_production_value": ZonneplanSensorEntityDescription(
                key="electricity_data.contracts.{install_index}.meta.electricity_last_measured_production_value",
                name="Electricity production",
                native_unit_of_measurement=UnitOfPower.WATT,
                device_class=SensorDeviceClass.POWER,
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.MEASUREMENT,
                none_value_behaviour=NONE_IS_ZERO,
            ),
            "electricity_last_measured_average_value": ZonneplanSensorEntityDescription(
                key="electricity_data.contracts.{install_index}.meta.electricity_last_measured_average_value",
                name="Electricity average",
                native_unit_of_measurement=UnitOfPower.WATT,
                device_class=SensorDeviceClass.POWER,
                entity_registry_enabled_default=True,
                state_class=SensorStateClass.MEASUREMENT,
                none_value_behaviour=NONE_IS_ZERO,
            ),
            "electricity_first_measured_at": ZonneplanSensorEntityDescription(
                key="electricity_data.contracts.{install_index}.meta.electricity_first_measured_at",
                name="Electricity first measured",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:calendar-clock",
            ),
            "electricity_last_measured_at": ZonneplanSensorEntityDescription(
                key="electricity_data.contracts.{install_index}.meta.electricity_last_measured_at",
                name="Electricity last measured",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:calendar-clock",
                entity_registry_enabled_default=True,
            ),
            "electricity_last_measured_production_at": ZonneplanSensorEntityDescription(
                key="electricity_data.contracts.{install_index}.meta.electricity_last_measured_production_at",
                name="Electricity last measured production",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:calendar-clock",
                entity_registry_enabled_default=True,
            ),
            "gas_first_measured_at": ZonneplanSensorEntityDescription(
                key="gas_data.contracts.{install_index}.meta.gas_first_measured_at",
                name="Gas first measured",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:calendar-clock",
            ),
            "gas_last_measured_at": ZonneplanSensorEntityDescription(
                key="gas_data.contracts.{install_index}.meta.gas_last_measured_at",
                name="Gas last measured",
                device_class=SensorDeviceClass.TIMESTAMP,
                icon="mdi:calendar-clock",
                entity_registry_enabled_default=True,
            ),
            "dsmr_version": ZonneplanSensorEntityDescription(
                key="electricity_data.contracts.{install_index}.meta.dsmr_version",
                name="Dsmr version",
                icon="mdi:meter-electric",
            ),
        },
    },
    BATTERY: {
        "battery_state": ZonneplanSensorEntityDescription(
            key="battery_data.contracts.{install_index}.meta.battery_state",
            name="Battery state",
            entity_registry_enabled_default=True,
        ),
        "battery_control_mode": ZonneplanSensorEntityDescription(
            key="battery_control_mode.control_mode",
            name="Battery control mode",
            entity_registry_enabled_default=True,
        ),
        "state_of_charge": ZonneplanSensorEntityDescription(
            key="battery_data.contracts.{install_index}.meta.state_of_charge",
            name="Percentage",
            device_class=SensorDeviceClass.BATTERY,
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=True,
            value_factor=0.1,
            native_unit_of_measurement=PERCENTAGE,
        ),
        "power_ac": ZonneplanSensorEntityDescription(
            key="battery_data.contracts.{install_index}.meta.power_ac",
            name="Power",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        "inverter_state": ZonneplanSensorEntityDescription(
            key="battery_data.contracts.{install_index}.meta.inverter_state",
            name="Inverter state",
        ),
        "manual_control_state": ZonneplanSensorEntityDescription(
            key="battery_data.contracts.{install_index}.meta.manual_control_state",
            name="Manual control state",
        ),
        "total_earned": ZonneplanSensorEntityDescription(
            key="battery_data.contracts.{install_index}.meta.total_earned",
            name="Total",
            value_factor=0.0000001,
            device_class=SensorDeviceClass.MONETARY,
            native_unit_of_measurement='EUR',
            state_class=SensorStateClass.TOTAL,
            entity_registry_enabled_default=True,
        ),
        "result_this_year": ZonneplanSensorEntityDescription(
            key="battery_data.contracts.{install_index}.charts.this_year.total_result",
            name="Result this year",
            device_class=SensorDeviceClass.MONETARY,
            native_unit_of_measurement='EUR',
            state_class=SensorStateClass.TOTAL,
            entity_registry_enabled_default=True,
            attributes=[
                Attribute(
                    key="battery_data.contracts.{install_index}.charts.this_year.year",
                    label="year",
                ),
                Attribute(
                    key="battery_data.contracts.{install_index}.charts.this_year.total_delivery_kwh",
                    label="total_delivery_kwh",
                ),
                Attribute(
                    key="battery_data.contracts.{install_index}.charts.this_year.total_production_kwh",
                    label="total_production_kwh",
                ),
                Attribute(
                    key="battery_data.contracts.{install_index}.charts.this_year.months",
                    label="months",
                ),
            ],
        ),
        "result_last_year": ZonneplanSensorEntityDescription(
            key="battery_data.contracts.{install_index}.charts.last_year.total_result",
            name="Result last year",
            device_class=SensorDeviceClass.MONETARY,
            native_unit_of_measurement='EUR',
            state_class=SensorStateClass.TOTAL,
            entity_registry_enabled_default=True,
            attributes=[
                Attribute(
                    key="battery_data.contracts.{install_index}.charts.last_year.year",
                    label="year",
                ),
                Attribute(
                    key="battery_data.contracts.{install_index}.charts.last_year.total_delivery_kwh",
                    label="total_delivery_kwh",
                ),
                Attribute(
                    key="battery_data.contracts.{install_index}.charts.last_year.total_production_kwh",
                    label="total_production_kwh",
                ),
                Attribute(
                    key="battery_data.contracts.{install_index}.charts.last_year.months",
                    label="months",
                ),
            ],
        ),
        "total_day": ZonneplanSensorEntityDescription(
            key="battery_data.contracts.{install_index}.meta.total_day",
            name="Today",
            value_factor=0.0000001,
            device_class=SensorDeviceClass.MONETARY,
            native_unit_of_measurement='EUR',
            state_class=SensorStateClass.TOTAL,
            last_reset_key="battery_data.measurement_groups.0.date",
            entity_registry_enabled_default=True,
        ),
        "average_day": ZonneplanSensorEntityDescription(
            key="battery_data.contracts.{install_index}.meta.average_day",
            name="Average day",
            value_factor=0.0000001,
            device_class=SensorDeviceClass.MONETARY,
            native_unit_of_measurement='EUR',
            state_class=SensorStateClass.TOTAL,
            last_reset_key="battery_data.measurement_groups.0.date",
            entity_registry_enabled_default=True,
        ),
        "result_this_month": ZonneplanSensorEntityDescription(
            key="battery_data.contracts.{install_index}.charts.this_month.total_result",
            name="Result this month",
            device_class=SensorDeviceClass.MONETARY,
            native_unit_of_measurement='EUR',
            state_class=SensorStateClass.TOTAL,
            entity_registry_enabled_default=True,
            attributes=[
                Attribute(
                    key="battery_data.contracts.{install_index}.charts.this_month.month",
                    label="month",
                ),
                Attribute(
                    key="battery_data.contracts.{install_index}.charts.this_month.total_delivery_kwh",
                    label="total_delivery_kwh",
                ),
                Attribute(
                    key="battery_data.contracts.{install_index}.charts.this_month.total_production_kwh",
                    label="total_production_kwh",
                ),
                Attribute(
                    key="battery_data.contracts.{install_index}.charts.this_month.days",
                    label="days",
                ),
            ],
        ),
        "result_last_month": ZonneplanSensorEntityDescription(
            key="battery_data.contracts.{install_index}.charts.last_month.total_result",
            name="Result last month",
            device_class=SensorDeviceClass.MONETARY,
            native_unit_of_measurement='EUR',
            state_class=SensorStateClass.TOTAL,
            entity_registry_enabled_default=True,
            attributes=[
                Attribute(
                    key="battery_data.contracts.{install_index}.charts.last_month.month",
                    label="month",
                ),
                Attribute(
                    key="battery_data.contracts.{install_index}.charts.last_month.total_delivery_kwh",
                    label="total_delivery_kwh",
                ),
                Attribute(
                    key="battery_data.contracts.{install_index}.charts.last_month.total_production_kwh",
                    label="total_production_kwh",
                ),
                Attribute(
                    key="battery_data.contracts.{install_index}.charts.last_month.days",
                    label="days",
                ),
            ],
        ),
        "delivery_day": ZonneplanSensorEntityDescription(
            key="battery_data.contracts.{install_index}.meta.delivery_day",
            name="Delivery today",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            value_factor=0.001,
            device_class=SensorDeviceClass.ENERGY,
            entity_registry_enabled_default=True,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        "production_day": ZonneplanSensorEntityDescription(
            key="battery_data.contracts.{install_index}.meta.production_day",
            name="Production today",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            value_factor=0.001,
            device_class=SensorDeviceClass.ENERGY,
            entity_registry_enabled_default=True,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        "first_measured_at": ZonneplanSensorEntityDescription(
            key="battery_data.contracts.{install_index}.meta.first_measured_at",
            name="First measured",
            device_class=SensorDeviceClass.TIMESTAMP,
            icon="mdi:calendar-clock",
        ),
        "last_measured_at": ZonneplanSensorEntityDescription(
            key="battery_data.contracts.{install_index}.meta.last_measured_at",
            name="Last measured",
            device_class=SensorDeviceClass.TIMESTAMP,
            icon="mdi:calendar-clock",
            entity_registry_enabled_default=True,
        ),
        "cycle_count": ZonneplanSensorEntityDescription(
            key="battery_data.contracts.{install_index}.meta.cycle_count",
            name="Battery cycles",
            icon="mdi:battery-sync",
            entity_registry_enabled_default=True,
            state_class=SensorStateClass.TOTAL,
        ),
    },
    CHARGE_POINT: {
        "state": ZonneplanSensorEntityDescription(
            key="charge_point_data.state.state",
            name="Charge point state",
            entity_registry_enabled_default=True,
            attributes=[
                Attribute(
                    key="charge_point_data.state",
                    label="state",
                ),
                Attribute(
                    key="charge_point_data.charge_schedules",
                    label="charge schedules",
                ),
            ],
        ),
        "power_actual": ZonneplanSensorEntityDescription(
            key="charge_point_data.state.power_actual",
            name="Charge point power",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        "energy_delivered_session": ZonneplanSensorEntityDescription(
            key="charge_point_data.state.energy_delivered_session",
            name="Charge point energy delivered session",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            value_factor=0.001,
            device_class=SensorDeviceClass.ENERGY,
            entity_registry_enabled_default=True,
            state_class=SensorStateClass.TOTAL_INCREASING,
        ),
        "session_charging_cost_total": ZonneplanSensorEntityDescription(
            key="charge_point_data.meta.session_charging_cost_total",
            name="Charge point session cost",
            value_factor=0.0000001,
            icon="mdi:cash",
            native_unit_of_measurement='EUR',
            entity_registry_enabled_default=True,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        "charging_cost_total": ZonneplanSensorEntityDescription(
            key="charge_point_data.meta.charging_cost_total",
            name="Charge point cost total",
            value_factor=0.0000001,
            icon="mdi:cash",
            native_unit_of_measurement='EUR',
            entity_registry_enabled_default=True,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        "session_flex_result": ZonneplanSensorEntityDescription(
            key="charge_point_data.meta.session_flex_result",
            name="Charge point session flex result",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement='EUR',
            state_class=SensorStateClass.TOTAL_INCREASING,
            entity_registry_enabled_default=True,
            none_value_behaviour=NONE_IS_ZERO,
        ),
        "session_average_cost_in_cents": ZonneplanSensorEntityDescription(
            key="charge_point_data.meta.session_average_cost_in_cents",
            name="Charge point session average costs",
            icon="mdi:cash",
            value_factor=0.0000001,
            native_unit_of_measurement=f"{CURRENCY_EURO}/{UnitOfEnergy.KILO_WATT_HOUR}",
            state_class=SensorStateClass.MEASUREMENT,
            entity_registry_enabled_default=True,
        ),
        "charge_schedules.start_time": ZonneplanSensorEntityDescription(
            key="charge_point_data.charge_schedules.0.start_time",
            name="Charge point next schedule start",
            device_class=SensorDeviceClass.TIMESTAMP,
            icon="mdi:calendar-clock",
            entity_registry_enabled_default=True,
        ),
        "charge_schedules.end_time": ZonneplanSensorEntityDescription(
            key="charge_point_data.charge_schedules.0.end_time",
            name="Charge point next schedule end",
            device_class=SensorDeviceClass.TIMESTAMP,
            icon="mdi:calendar-clock",
            entity_registry_enabled_default=True,
        ),
        "dynamic_load_balancing_health": ZonneplanSensorEntityDescription(
            key="charge_point_data.state.dynamic_load_balancing_health",
            name="Charge point dynamic load balancing health",
        ),
        "start_mode": ZonneplanSensorEntityDescription(
            key="charge_point_data.state.start_mode",
            name="Charge point start mode",
        ),
        "dynamic_charging_user_constraints.desired_distance_in_kilometers": ZonneplanSensorEntityDescription(
            key="charge_point_data.state.dynamic_charging_user_constraints.desired_distance_in_kilometers",
            name="Charge point dynamic load desired distance",
            native_unit_of_measurement=UnitOfLength.KILOMETERS,
            entity_registry_enabled_default=True,
        ),
        "dynamic_charging_user_constraints.desired_end_time": ZonneplanSensorEntityDescription(
            key="charge_point_data.state.dynamic_charging_user_constraints.desired_end_time",
            name="Charge point dynamic load desired end time",
            device_class=SensorDeviceClass.TIMESTAMP,
            icon="mdi:calendar-clock",
            entity_registry_enabled_default=True,
        ),
        "charge_point_session.start_time": ZonneplanSensorEntityDescription(
            key="charge_point_data.state.charge_point_session.start_time",
            name="Charge point session start time",
            device_class=SensorDeviceClass.TIMESTAMP,
            icon="mdi:calendar-clock",
            entity_registry_enabled_default=True,
        ),
        "charge_point_session.charged_distance_in_kilometers": ZonneplanSensorEntityDescription(
            key="charge_point_data.state.charge_point_session.charged_distance_in_kilometers",
            name="Charge point session charged distance",
            native_unit_of_measurement=UnitOfLength.KILOMETERS,
            entity_registry_enabled_default=True,
        ),
    },
}

BINARY_SENSORS_TYPES: dict[str, list[ZonneplanBinarySensorEntityDescription]] = {
    BATTERY: {
        "dynamic_charging_enabled": ZonneplanBinarySensorEntityDescription(
            key="battery_data.contracts.{install_index}.meta.dynamic_charging_enabled",
            name="Dynamic charging enabled",
            entity_registry_enabled_default=True,
        ),
        "dynamic_load_balancing_enabled": ZonneplanBinarySensorEntityDescription(
            key="battery_data.contracts.{install_index}.meta.dynamic_load_balancing_enabled",
            name="Dynamic load balancing overload enabled",
            entity_registry_enabled_default=True,
        ),
        "dynamic_load_balancing_overload_active": ZonneplanBinarySensorEntityDescription(
            key="battery_data.contracts.{install_index}.meta.dynamic_load_balancing_overload_active",
            name="Dynamic load balancing overload active",
            entity_registry_enabled_default=True,
        ),
        "manual_control_enabled": ZonneplanBinarySensorEntityDescription(
            key="battery_data.contracts.{install_index}.meta.manual_control_enabled",
            name="Manual control enabled",
            entity_registry_enabled_default=True,
        ),
        "self_consumption_enabled": ZonneplanBinarySensorEntityDescription(
            key="battery_data.contracts.{install_index}.meta.self_consumption_enabled",
            name="Self consumption enabled",
            entity_registry_enabled_default=True,
        ),
        "home_optimization_enabled": ZonneplanBinarySensorEntityDescription(
            key="battery_data.contracts.{install_index}.meta.home_optimization_enabled",
            name="Home optimization enabled",
            entity_registry_enabled_default=True,
        ),
        "home_optimization_active": ZonneplanBinarySensorEntityDescription(
            key="battery_data.contracts.{install_index}.meta.home_optimization_active",
            name="Home optimization active",
            entity_registry_enabled_default=True,
        ),
        "grid_congestion_active": ZonneplanBinarySensorEntityDescription(
            key="battery_data.contracts.{install_index}.meta.grid_congestion_active",
            name="Grid congestion active",
            entity_registry_enabled_default=True,
        ),
    },
    PV_INSTALL: {
        "dynamic_control_enabled": ZonneplanBinarySensorEntityDescription(
            key="pv_data.contracts.{install_index}.meta.dynamic_control_enabled",
            name="Powerplay enabled",
            entity_registry_enabled_default=False,
        ),
        "power_limit_active": ZonneplanBinarySensorEntityDescription(
            key="pv_data.contracts.{install_index}.meta.power_limit_active",
            name="Power limit active",
            entity_registry_enabled_default=False,
        ),
    },
    CHARGE_POINT: {
        "connectivity_state": ZonneplanBinarySensorEntityDescription(
            key="charge_point_data.state.connectivity_state",
            name="Charge point connectivity state",
            entity_registry_enabled_default=True,
        ),
        "can_charge": ZonneplanBinarySensorEntityDescription(
            key="charge_point_data.state.can_charge",
            name="Charge point can charge",
            entity_registry_enabled_default=True,
        ),
        "can_schedule": ZonneplanBinarySensorEntityDescription(
            key="charge_point_data.state.can_schedule",
            name="Charge point can schedule",
            entity_registry_enabled_default=True,
        ),
        "charging_manually": ZonneplanBinarySensorEntityDescription(
            key="charge_point_data.state.charging_manually",
            name="Charge point charging manually",
            entity_registry_enabled_default=True,
        ),
        "charging_automatically": ZonneplanBinarySensorEntityDescription(
            key="charge_point_data.state.charging_automatically",
            name="Charge point charging automatically",
            entity_registry_enabled_default=True,
        ),
        "plug_and_charge": ZonneplanBinarySensorEntityDescription(
            key="charge_point_data.state.plug_and_charge",
            name="Charge point plug and charge",
            entity_registry_enabled_default=True,
        ),
        "overload_protection_active": ZonneplanBinarySensorEntityDescription(
            key="charge_point_data.state.overload_protection_active",
            name="Charge point overload protection active",
        ),
        "dynamic_charging_enabled": ZonneplanBinarySensorEntityDescription(
            key="charge_point_data.state.dynamic_charging_enabled",
            name="Charge point dynamic charging enabled",
            entity_registry_enabled_default=True,
        ),
        "dynamic_charging_flex_enabled": ZonneplanBinarySensorEntityDescription(
            key="charge_point_data.state.dynamic_charging_flex_enabled",
            name="Charge point dynamic charging flex enabled",
            entity_registry_enabled_default=True,
        ),
        "dynamic_charging_flex_suppressed": ZonneplanBinarySensorEntityDescription(
            key="charge_point_data.state.dynamic_charging_flex_suppressed",
            name="Charge point dynamic charging flex suppressed",
        ),
    }
}

BUTTON_TYPES: dict[str, list[ZonneplanButtonEntityDescription]] = {
    CHARGE_POINT: {
        "start": ZonneplanButtonEntityDescription(
            key="charge_point.start",
            name="Start charge",
        ),
        "stop": ZonneplanButtonEntityDescription(
            key="charge_point.stop",
            name="Stop charge",
        ),
    },
    BATTERY: {
        "enable_self_consumption": ZonneplanButtonEntityDescription(
            key="battery.enable_self_consumption",
            name="Enable self consumption",
        ),
        "enable_dynamic_charging": ZonneplanButtonEntityDescription(
            key="battery.enable_dynamic_charging",
            name="Enable powerplay",
        ),
        "enable_home_optimization": ZonneplanButtonEntityDescription(
            key="battery.enable_home_optimization",
            name="Enable Home optimization",
        ),
    }
}
