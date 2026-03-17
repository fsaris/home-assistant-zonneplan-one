"""The Zonneplan integration."""

import logging
from datetime import datetime

import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util
import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import (
    aiohttp_client,
    config_entry_oauth2_flow,
)

from . import api, config_flow
from .const import (
    BATTERY,
    BATTERY_CHARTS,
    BATTERY_CONTROL,
    CHARGE_POINT,
    DOMAIN,
    ELECTRICITY,
    ELECTRICITY_HOME_CONSUMPTION,
    GAS,
    P1_ELECTRICITY,
    P1_GAS,
    P1_INSTALL,
    PV_INSTALL,
)
from .coordinators.account_data_coordinator import (
    AccountDataUpdateCoordinator,
    ZonneplanConfigEntry,
)
from .coordinators.battery_charts_data_coordinator import (
    BatteryChartsDataUpdateCoordinator,
)
from .coordinators.battery_control_data_coordinator import (
    BatteryControlDataUpdateCoordinator,
)
from .coordinators.battery_data_coordinator import BatteryDataUpdateCoordinator
from .coordinators.charge_point_data_coordinator import ChargePointDataUpdateCoordinator
from .coordinators.electricity_data_coordinator import ElectricityDataUpdateCoordinator
from .coordinators.electricity_home_consumption_data_coordinator import (
    ElectricityHomeConsumptionDataUpdateCoordinator,
)
from .coordinators.gas_data_coordinator import GasDataUpdateCoordinator
from .coordinators.pv_data_coordinator import PvDataUpdateCoordinator
from .coordinators.summary_data_coordinator import SummaryDataUpdateCoordinator

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

SERVICE_FETCH_STATISTICS = "fetch_statistics"
_ATTR_ENDPOINT = "endpoint"
_ATTR_START_DATE = "start_date"
_ATTR_CONNECTION_UUID = "connection_uuid"
_DATE_FORMATS = ("%Y%m%d", "%Y-%m-%d")

SERVICE_FETCH_STATISTICS_SCHEMA = vol.Schema(
    {
        vol.Required(_ATTR_ENDPOINT): vol.In([ELECTRICITY, GAS, "pv"]),
        vol.Required(_ATTR_START_DATE): str,
        vol.Optional(_ATTR_CONNECTION_UUID): str,
    }
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(
    hass: HomeAssistant,
    config: dict,  # noqa: ARG001
) -> bool:
    """Set up the Zonneplan component."""
    hass.data.setdefault(DOMAIN, {})

    config_flow.ZonneplanLoginFlowHandler.async_register_implementation(
        hass,
        api.ZonneplanOAuth2Implementation(api.AsyncConfigEntryAuth(aiohttp_client.async_get_clientsession(hass))),
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ZonneplanConfigEntry) -> bool:  # noqa: PLR0912
    """Set up Zonneplan from a config entry."""
    implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(hass, entry)

    session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)
    zonneplan_api = api.AsyncConfigEntryAuth(aiohttp_client.async_get_clientsession(hass), session)

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
                    SummaryDataUpdateCoordinator(
                        hass,
                        zonneplan_api,
                        address_group["uuid"],
                        connection["uuid"],
                        contracts[ELECTRICITY][0],
                    ),
                )

            if GAS in contracts:
                account_coordinator.add_coordinator(
                    connection["uuid"],
                    GAS,
                    SummaryDataUpdateCoordinator(
                        hass,
                        zonneplan_api,
                        address_group["uuid"],
                        connection["uuid"],
                        contracts[GAS][0],
                    ),
                )

            if PV_INSTALL in contracts:
                account_coordinator.add_coordinator(
                    connection["uuid"],
                    PV_INSTALL,
                    PvDataUpdateCoordinator(
                        hass,
                        zonneplan_api,
                        address_group["uuid"],
                        connection["uuid"],
                        contracts[PV_INSTALL],
                    ),
                )

            if P1_INSTALL in contracts:
                account_coordinator.add_coordinator(
                    connection["uuid"],
                    P1_ELECTRICITY,
                    ElectricityDataUpdateCoordinator(
                        hass,
                        zonneplan_api,
                        address_group["uuid"],
                        connection["uuid"],
                        contracts[P1_INSTALL],
                    ),
                )

                gas_meter_registered = False
                for contract in contracts[P1_INSTALL]:
                    if contract.get("meta", {}).get("gas_last_measured_at"):
                        gas_meter_registered = True
                        break

                if gas_meter_registered:
                    account_coordinator.add_coordinator(
                        connection["uuid"],
                        P1_GAS,
                        GasDataUpdateCoordinator(
                            hass,
                            zonneplan_api,
                            address_group["uuid"],
                            connection["uuid"],
                            contracts[P1_INSTALL],
                        ),
                    )

            if CHARGE_POINT in contracts:
                account_coordinator.add_coordinator(
                    connection["uuid"],
                    CHARGE_POINT,
                    ChargePointDataUpdateCoordinator(
                        hass,
                        zonneplan_api,
                        address_group["uuid"],
                        connection["uuid"],
                        contracts[CHARGE_POINT][0],
                    ),
                )

            if BATTERY in contracts:
                account_coordinator.add_coordinator(
                    connection["uuid"],
                    BATTERY,
                    BatteryDataUpdateCoordinator(
                        hass,
                        zonneplan_api,
                        address_group["uuid"],
                        connection["uuid"],
                        contracts[BATTERY][0],
                    ),
                )
                account_coordinator.add_coordinator(
                    connection["uuid"],
                    BATTERY_CHARTS,
                    BatteryChartsDataUpdateCoordinator(
                        hass,
                        zonneplan_api,
                        address_group["uuid"],
                        connection["uuid"],
                        contracts[BATTERY][0],
                    ),
                )
                account_coordinator.add_coordinator(
                    connection["uuid"],
                    BATTERY_CONTROL,
                    BatteryControlDataUpdateCoordinator(
                        hass,
                        zonneplan_api,
                        address_group["uuid"],
                        connection["uuid"],
                        contracts[BATTERY][0],
                    ),
                )
                account_coordinator.add_coordinator(
                    connection["uuid"],
                    ELECTRICITY_HOME_CONSUMPTION,
                    ElectricityHomeConsumptionDataUpdateCoordinator(
                        hass,
                        zonneplan_api,
                        address_group["uuid"],
                        connection["uuid"],
                        contracts[BATTERY][0],
                    ),
                )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_setup_fetch_statistics_service(hass)
    return True


def _async_setup_fetch_statistics_service(hass: HomeAssistant) -> None:
    """Register the fetch_statistics service if not already registered."""
    if hass.services.has_service(DOMAIN, SERVICE_FETCH_STATISTICS):
        return

    async def handle_fetch_statistics(call: ServiceCall) -> None:
        """Handle the fetch_statistics service call."""
        endpoint: str = call.data[_ATTR_ENDPOINT]
        start_date_str: str = call.data[_ATTR_START_DATE]
        connection_uuid_filter: str | None = call.data.get(_ATTR_CONNECTION_UUID)

        amsterdam_tz = dt_util.get_time_zone("Europe/Amsterdam")
        start_date: datetime | None = None
        for fmt in _DATE_FORMATS:
            try:
                start_date = datetime.strptime(start_date_str, fmt).replace(tzinfo=amsterdam_tz)
                break
            except ValueError:
                continue

        if start_date is None:
            msg = f"Invalid start_date '{start_date_str}'. Use YYYYMMDD or YYYY-MM-DD."
            raise ServiceValidationError(msg)

        if connection_uuid_filter:
            connection_uuid_filter = connection_uuid_filter.replace("_", "-")

        _LOGGER.info(
            "Fetch_statistics called: endpoint=%s, start_date=%s, connection_uuid=%s",
            endpoint,
            start_date,
            connection_uuid_filter,
        )

        for loaded_entry in hass.config_entries.async_entries(DOMAIN):
            if loaded_entry.state is not ConfigEntryState.LOADED:
                continue
            account_coordinator = loaded_entry.runtime_data
            for uuid, conn_coordinators in account_coordinator.coordinators.items():
                if connection_uuid_filter and uuid != connection_uuid_filter:
                    continue
                if endpoint == ELECTRICITY and conn_coordinators.p1_electricity is not None:
                    await conn_coordinators.p1_electricity.async_backfill_statistics(start_date)
                elif endpoint == GAS and conn_coordinators.p1_gas is not None:
                    await conn_coordinators.p1_gas.async_backfill_statistics(start_date)
                elif endpoint == "pv" and conn_coordinators.pv_installation is not None:
                    await conn_coordinators.pv_installation.async_backfill_statistics(start_date)

    hass.services.async_register(
        DOMAIN,
        SERVICE_FETCH_STATISTICS,
        handle_fetch_statistics,
        schema=SERVICE_FETCH_STATISTICS_SCHEMA,
    )


async def async_unload_entry(hass: HomeAssistant, entry: ZonneplanConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entry.runtime_data.coordinators.clear()

    # Remove the domain service when no more entries remain loaded
    remaining = [
        e for e in hass.config_entries.async_entries(DOMAIN) if e.entry_id != entry.entry_id and e.state is ConfigEntryState.LOADED
    ]
    if not remaining:
        hass.services.async_remove(DOMAIN, SERVICE_FETCH_STATISTICS)

    return unload_ok
