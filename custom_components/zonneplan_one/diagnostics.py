from __future__ import annotations
from typing import Any
from dataclasses import fields
from homeassistant.core import HomeAssistant
from homeassistant.components.diagnostics import async_redact_data

from .coordinators.account_data_coordinator import ZonneplanConfigEntry

TO_REDACT = ["address", "organization", "chat", "user_account"]

async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ZonneplanConfigEntry) -> dict[str, dict[Any, Any]]:
    coordinator_data = {}

    for uuid, connection in entry.runtime_data.coordinators.items():
        coordinator_data[uuid] = {}

        for field in fields(connection):
            key = field.name
            coordinator = getattr(connection, field.name)

            if coordinator:
                coordinator_data[uuid][key] = coordinator.data

    return {
        "account_data": async_redact_data(entry.runtime_data.data, TO_REDACT),
        "last_api_responses": async_redact_data(entry.runtime_data.api.diagnostics, TO_REDACT),
        "coordinator_data": coordinator_data
    }
