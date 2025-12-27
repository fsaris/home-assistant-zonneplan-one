"""The Zonneplan integration."""
import logging

from homeassistant.config_entries import ConfigEntry
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
from .coordinators.account_data_coordinator import AccountDataUpdateCoordinator
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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Zonneplan from a config entry."""

    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass, entry
        )
    )

    session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)
    zonneplanApi = api.AsyncConfigEntryAuth(
        aiohttp_client.async_get_clientsession(hass), session
    )

    accountCoordinator = AccountDataUpdateCoordinator(hass, zonneplanApi)
    await accountCoordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "api": zonneplanApi,
        "accountCoordinator": accountCoordinator,
        "connections": {},
    }

    for address_group in accountCoordinator.address_groups:
        for connection in address_group.get("connections") or []:
            if len(connection["contracts"]) == 0:
                continue

            contracts = {}
            for contract in connection["contracts"]:
                if contract["type"] not in contracts:
                    contracts[contract["type"]] = []
                contracts[contract["type"]].append(contract)

            coordinators = {}
            if ELECTRICITY in contracts:
                coordinators[ELECTRICITY] = SummaryDataUpdateCoordinator(hass, zonneplanApi, address_group["uuid"], connection["uuid"],
                                                                         contracts[ELECTRICITY][0])

            if GAS in contracts:
                coordinators[GAS] = SummaryDataUpdateCoordinator(hass, zonneplanApi, address_group["uuid"], connection["uuid"], contracts[GAS][0])

            if PV_INSTALL in contracts:
                coordinators[PV_INSTALL] = PvDataUpdateCoordinator(hass, zonneplanApi, address_group["uuid"], connection["uuid"], contracts[PV_INSTALL])

            if P1_INSTALL in contracts:
                coordinators[P1_ELECTRICITY] = ElectricityDataUpdateCoordinator(hass, zonneplanApi, address_group["uuid"], connection["uuid"],
                                                                                contracts[P1_INSTALL])
                coordinators[P1_GAS] = GasDataUpdateCoordinator(hass, zonneplanApi, address_group["uuid"], connection["uuid"], contracts[P1_INSTALL])

            if CHARGE_POINT in contracts:
                coordinators[CHARGE_POINT] = ChargePointDataUpdateCoordinator(hass, zonneplanApi, address_group["uuid"], connection["uuid"],
                                                                              contracts[CHARGE_POINT][0])

            if BATTERY in contracts:
                coordinators[BATTERY] = BatteryDataUpdateCoordinator(hass, zonneplanApi, address_group["uuid"], connection["uuid"], contracts[BATTERY][0])
                coordinators[BATTERY_CHARTS] = BatteryChartsDataUpdateCoordinator(hass, zonneplanApi, address_group["uuid"], connection["uuid"],
                                                                                  contracts[BATTERY][0])
                coordinators[BATTERY_CONTROL] = BatteryControlDataUpdateCoordinator(hass, zonneplanApi, address_group["uuid"], connection["uuid"],
                                                                                    contracts[BATTERY][0])
                coordinators[ELECTRICITY_HOME_CONSUMPTION] = ElectricityHomeConsumptionDataUpdateCoordinator(hass, zonneplanApi, address_group["uuid"],
                                                                                                             connection["uuid"], contracts[BATTERY][0])

            if coordinators:
                hass.data[DOMAIN][entry.entry_id]["connections"][connection["uuid"]] = coordinators

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
