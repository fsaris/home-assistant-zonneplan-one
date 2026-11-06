"""Tests that diagnostics, which users post in public issues, hold no personal data."""

import json
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.zonneplan_one.const import DOMAIN
from custom_components.zonneplan_one.diagnostics import async_get_config_entry_diagnostics

from .common import accounts_from_connections, mock_api
from .conftest import NOW

EAN = "871000000000000001"
METER_IDENTIFIER = "000000000099"
EXTERNAL_CONTRACT_ID = "external-contract-99"
SERIAL = "XX00000000000099"
STREET = "Teststraat"


@pytest.fixture
async def diagnostics(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    connections: dict[str, Any],
) -> str:
    accounts = accounts_from_connections(connections)
    group = accounts["address_groups"][0]
    group["address"] = {"street": STREET}
    for connection in group["connections"]:
        connection["ean"] = EAN
        for contract in connection["contracts"]:
            meta = contract["meta"]
            for key in ("serial_number", "sgn_serial_number", "identifier"):
                if key in meta:
                    meta[key] = SERIAL
            for key in ("electricity_meter_identifier", "gas_meter_identifier"):
                if key in meta:
                    meta[key] = METER_IDENTIFIER
            if "external_contract_id" in meta:
                meta["external_contract_id"] = EXTERNAL_CONTRACT_ID

    mock_api(aioclient_mock, connections, NOW, accounts=accounts)
    config_entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    return json.dumps(await async_get_config_entry_diagnostics(hass, config_entry), default=str)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("user@example.com", id="email"),
        pytest.param(STREET, id="address"),
        pytest.param(SERIAL, id="serial"),
        pytest.param(EAN, id="ean"),
        pytest.param(METER_IDENTIFIER, id="meter_identifier"),
        pytest.param(EXTERNAL_CONTRACT_ID, id="external_contract_id"),
    ],
)
async def test_personal_data_is_redacted(diagnostics: str, value: str) -> None:
    # Not `assert value not in diagnostics`: pytest would diff the whole dump on failure, which takes minutes.
    leaked = value in diagnostics
    assert not leaked
