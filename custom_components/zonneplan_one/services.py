"""Zonneplan integration services."""

import logging
from datetime import datetime

import homeassistant.util.dt as dt_util
import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError

from .const import (
    DOMAIN,
    ELECTRICITY,
    GAS,
)

SERVICE_FETCH_STATISTICS = "fetch_statistics"
_ATTR_ENDPOINT = "endpoint"
_ATTR_START_DATE = "start_date"
_ATTR_CONNECTION_UUID = "connection_uuid"
_DATE_FORMATS = ("%Y%m%d", "%Y-%m-%d")

SERVICE_FETCH_STATISTICS_SCHEMA = vol.Schema(
    {
        vol.Required(_ATTR_ENDPOINT): vol.In([ELECTRICITY, GAS]),
        vol.Required(_ATTR_START_DATE): str,
        vol.Optional(_ATTR_CONNECTION_UUID): str,
    }
)

_LOGGER = logging.getLogger(__name__)


@callback
def async_setup_fetch_statistics_service(hass: HomeAssistant) -> None:
    """Register the fetch_statistics service if not already registered."""
    if hass.services.has_service(DOMAIN, SERVICE_FETCH_STATISTICS):
        return

    async def handle_fetch_statistics(call: ServiceCall) -> ServiceResponse:
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
                    hass.async_create_task(conn_coordinators.p1_electricity.async_backfill_statistics(start_date))
                elif endpoint == GAS and conn_coordinators.p1_gas is not None:
                    hass.async_create_task(conn_coordinators.p1_gas.async_backfill_statistics(start_date))

        return {"result": "Check notifications for progress."}

    hass.services.async_register(
        DOMAIN,
        SERVICE_FETCH_STATISTICS,
        handle_fetch_statistics,
        schema=SERVICE_FETCH_STATISTICS_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
