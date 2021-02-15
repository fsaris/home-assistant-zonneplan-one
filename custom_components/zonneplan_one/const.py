"""Constants for the Zonneplan ONE integration."""

from homeassistant.const import (
    ENERGY_KILO_WATT_HOUR,
    POWER_WATT,
)

DOMAIN = "zonneplan_one"


"""Available sensors"""
SENSOR_TYPES = {
    "highest_measured_power_value": [
        "connection.contracts.0.meta.highest_measured_power_value",
        "Highest yield",
        POWER_WATT,
        "mdi:solar-power",
        False,
    ],
    "highest_power_measured_at": [
        "connection.contracts.0.meta.highest_power_measured_at",
        "Highest yield at",
        "date_time",
        "mdi:calendar-clock",
        False,
    ],
    "total_power_measured": [
        "connection.contracts.0.meta.total_power_measured",
        "Yield total",
        ENERGY_KILO_WATT_HOUR,
        "mdi:solar-power",
        True,
    ],
    "last_measured_power_value": [
        "connection.contracts.0.meta.last_measured_power_value",
        "Last value",
        POWER_WATT,
        "mdi:solar-power",
        True,
    ],
    "last_measured_at": [
        "connection.contracts.0.meta.last_measured_at",
        "Last measured at",
        "date_time",
        "mdi:calendar-clock",
        True,
    ],
    "total_today": [
        "live_data.total",
        "Yield today",
        ENERGY_KILO_WATT_HOUR,
        "mdi:solar-power",
        True,
    ],
}