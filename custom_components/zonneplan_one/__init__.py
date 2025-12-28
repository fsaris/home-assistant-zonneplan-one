"""The Zonneplan integration."""
import logging

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    aiohttp_client,
    config_entry_oauth2_flow,
)

from . import api, config_flow
from .const import (
    DOMAIN,
    GAS,
    ELECTRICITY,
    PV_INSTALL,
    P1_ELECTRICITY,
    P1_INSTALL,
    P1_GAS,
    CHARGE_POINT,
    BATTERY,
    BATTERY_CHARTS,
    BATTERY_CONTROL,
    ELECTRICITY_HOME_CONSUMPTION
)
from .coordinators.account_data_coordinator import AccountDataUpdateCoordinator, ZonneplanConfigEntry
from .coordinators.summary_data_coordinator import SummaryDataUpdateCoordinator
from .coordinators.pv_data_coordinator import PvDataUpdateCoordinator
from .coordinators.electricity_data_coordinator import ElectricityDataUpdateCoordinator
from .coordinators.gas_data_coordinator import GasDataUpdateCoordinator
from .coordinators.charge_point_data_coordinator import ChargePointDataUpdateCoordinator
from .coordinators.battery_data_coordinator import BatteryDataUpdateCoordinator
from .coordinators.battery_charts_data_coordinator import BatteryChartsDataUpdateCoordinator
from .coordinators.battery_control_data_coordinator import BatteryControlDataUpdateCoordinator
from .coordinators.electricity_home_consumption_data_coordinator import ElectricityHomeConsumptionDataUpdateCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.BUTTON, Platform.NUMBER, Platform.SELECT]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Zonneplan component."""
    hass.data.setdefault(DOMAIN, {})

    config_flow.ZonneplanLoginFlowHandler.async_register_implementation(
        hass,
        api.ZonneplanOAuth2Implementation(
            api.AsyncConfigEntryAuth(aiohttp_client.async_get_clientsession(hass))
        ),
    )

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ZonneplanConfigEntry):
    """Set up Zonneplan from a config entry."""

    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass, entry
        )
    )

    session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)
    zonneplan_api = api.AsyncConfigEntryAuth(
        aiohttp_client.async_get_clientsession(hass), session
    )

    account_coordinator = AccountDataUpdateCoordinator(hass, zonneplan_api)
    await account_coordinator.async_config_entry_first_refresh()

    entry.runtime_data = account_coordinator

    for address_group in account_coordinator.address_groups:
        for connection in address_group.get("connections") or []:
            if len(connection["contracts"]) == 0:
                continue

            contracts = {}
            for contract in connection["contracts"]:
                if contract["type"] not in contracts:
                    contracts[contract["type"]] = []
                contracts[contract["type"]].append(contract)

            if ELECTRICITY in contracts:
                account_coordinator.add_coordinator(
                    connection["uuid"],
                    ELECTRICITY,
                    SummaryDataUpdateCoordinator(hass, zonneplan_api, address_group["uuid"], connection["uuid"], contracts[ELECTRICITY][0])
                )

            if GAS in contracts:
                account_coordinator.add_coordinator(
                    connection["uuid"],
                    GAS,
                    SummaryDataUpdateCoordinator(hass, zonneplan_api, address_group["uuid"], connection["uuid"], contracts[GAS][0])
                )

            if PV_INSTALL in contracts:
                account_coordinator.add_coordinator(
                    connection["uuid"],
                    PV_INSTALL,
                    PvDataUpdateCoordinator(hass, zonneplan_api, address_group["uuid"], connection["uuid"], contracts[PV_INSTALL])
                )

            if P1_INSTALL in contracts:
                account_coordinator.add_coordinator(
                    connection["uuid"],
                    P1_ELECTRICITY,
                    ElectricityDataUpdateCoordinator(hass, zonneplan_api, address_group["uuid"], connection["uuid"], contracts[P1_INSTALL])
                )
                account_coordinator.add_coordinator(
                    connection["uuid"],
                    P1_GAS, GasDataUpdateCoordinator(hass, zonneplan_api, address_group["uuid"], connection["uuid"], contracts[P1_INSTALL])
                )

            if CHARGE_POINT in contracts:
                account_coordinator.add_coordinator(
                    connection["uuid"],
                    CHARGE_POINT,
                    ChargePointDataUpdateCoordinator(hass, zonneplan_api, address_group["uuid"], connection["uuid"], contracts[CHARGE_POINT][0])
                )

            if BATTERY in contracts:
                account_coordinator.add_coordinator(
                    connection["uuid"],
                    BATTERY,
                    BatteryDataUpdateCoordinator(hass, zonneplan_api, address_group["uuid"], connection["uuid"], contracts[BATTERY][0])
                )
                account_coordinator.add_coordinator(
                    connection["uuid"],
                    BATTERY_CHARTS,
                    BatteryChartsDataUpdateCoordinator(hass, zonneplan_api, address_group["uuid"], connection["uuid"], contracts[BATTERY][0])
                )
                account_coordinator.add_coordinator(
                    connection["uuid"],
                    BATTERY_CONTROL,
                    BatteryControlDataUpdateCoordinator(hass, zonneplan_api, address_group["uuid"], connection["uuid"], contracts[BATTERY][0])
                )
                account_coordinator.add_coordinator(
                    connection["uuid"],
                    ELECTRICITY_HOME_CONSUMPTION,
                    ElectricityHomeConsumptionDataUpdateCoordinator(hass, zonneplan_api, address_group["uuid"], connection["uuid"], contracts[BATTERY][0])
                )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True
