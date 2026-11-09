"""Tests for setting up and unloading the integration."""

from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.zonneplan_one.const import DOMAIN, ELECTRICITY_PRICES, SENSOR_TYPES

from .common import API, CONNECTION_FIXTURES, CONNECTION_UUID, connections_from_fixture, mock_api
from .conftest import NOW


def _entity_ids_for(hass: HomeAssistant, entry: MockConfigEntry) -> set[str]:
    return {entity.entity_id for entity in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)}


async def test_setup_and_unload(hass: HomeAssistant, setup_integration: MockConfigEntry) -> None:
    assert setup_integration.state is ConfigEntryState.LOADED
    assert _entity_ids_for(hass, setup_integration)
    account_coordinator = setup_integration.runtime_data

    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()

    assert setup_integration.state is ConfigEntryState.NOT_LOADED
    assert account_coordinator.coordinators == {}


@pytest.mark.parametrize("fixture_name", CONNECTION_FIXTURES)
async def test_setup_with_every_captured_account(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
    fixture_name: str,
) -> None:
    mock_api(aioclient_mock, connections_from_fixture(fixture_name), NOW)
    config_entry.add_to_hass(hass)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED
    assert _entity_ids_for(hass, config_entry)
    assert [record.getMessage() for record in caplog.records if record.levelname == "ERROR"] == []


async def test_unauthorized_starts_reauth(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    aioclient_mock.put(f"{API}/user-accounts/locale", status=204)
    aioclient_mock.get(f"{API}/user-accounts/me", status=401)
    config_entry.add_to_hass(hass)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    assert [flow["context"]["source"] for flow in hass.config_entries.flow.async_progress()] == ["reauth"]


async def test_server_error_retries_setup(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    aioclient_mock.put(f"{API}/user-accounts/locale", status=204)
    aioclient_mock.get(f"{API}/user-accounts/me", status=500)
    config_entry.add_to_hass(hass)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_no_sensor_unavailable_after_setup(hass: HomeAssistant, setup_integration: MockConfigEntry) -> None:
    # Only sensors: buttons are unavailable on purpose, depending on the charging state.
    sensors = [entity_id for entity_id in _entity_ids_for(hass, setup_integration) if entity_id.startswith("sensor.")]

    assert sensors
    assert [entity_id for entity_id in sensors if (state := hass.states.get(entity_id)) and state.state == STATE_UNAVAILABLE] == []


async def _setup_with(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, entry: MockConfigEntry, connections: dict[str, Any]) -> Any:
    mock_api(aioclient_mock, connections, NOW)
    entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    return next(iter(entry.runtime_data.coordinators.values()))


def _battery_connection(connections: dict[str, Any]) -> dict[str, Any]:
    return next(connection for connection in connections.values() if connection.get("home_battery_installation"))


async def test_ended_contract_gets_no_coordinator(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    connections: dict[str, Any],
) -> None:
    _battery_connection(connections)["home_battery_installation"][0]["end_date"] = (NOW - timedelta(days=1)).isoformat()

    coordinators = await _setup_with(hass, aioclient_mock, config_entry, connections)

    assert coordinators.home_battery_installation is None
    assert coordinators.charge_point_installation is not None


async def test_contract_ending_later_keeps_its_coordinator(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    connections: dict[str, Any],
) -> None:
    _battery_connection(connections)["home_battery_installation"][0]["end_date"] = (NOW + timedelta(days=1)).isoformat()

    coordinators = await _setup_with(hass, aioclient_mock, config_entry, connections)

    assert coordinators.home_battery_installation is not None


@pytest.mark.parametrize(
    ("age", "expect_gas"),
    [
        (timedelta(days=6), True),
        (timedelta(days=8), False),
    ],
)
async def test_gas_meter_only_used_when_measured_within_a_week(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    connections: dict[str, Any],
    age: timedelta,
    expect_gas: bool,  # noqa: FBT001
) -> None:
    _battery_connection(connections)["p1_installation"][0]["meta"]["gas_last_measured_at"] = (NOW - age).isoformat()

    coordinators = await _setup_with(hass, aioclient_mock, config_entry, connections)

    assert (coordinators.p1_gas is not None) is expect_gas


async def test_empty_account_response_retries_setup(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    aioclient_mock.put(f"{API}/user-accounts/locale", status=204)
    aioclient_mock.get(f"{API}/user-accounts/me", json={"data": {}})
    config_entry.add_to_hass(hass)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_expired_token_is_refreshed_during_setup(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    connections: dict[str, Any],
) -> None:
    token = {**config_entry.data["token"], "expires_at": NOW.timestamp() - 60}
    entry = MockConfigEntry(domain=DOMAIN, unique_id=DOMAIN, data={**config_entry.data, "token": token})
    new_token = {"access_token": "new-access-token", "refresh_token": "new-refresh-token", "token_type": "Bearer", "expires_in": 3600}

    with patch("custom_components.zonneplan_one.zonneplan_api.api.ZonneplanApi.async_refresh_token", AsyncMock(return_value=new_token)) as refresh:
        mock_api(aioclient_mock, connections, NOW)
        entry.add_to_hass(hass)
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    refresh.assert_awaited()
    assert entry.data["token"]["access_token"] == "new-access-token"
    assert entry.data["token"]["expires_at"] > NOW.timestamp()


async def test_entries_without_contracts_get_no_coordinators(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
) -> None:
    accounts = {"address_groups": [{"uuid": "group", "connections": [{"uuid": "empty", "contracts": []}]}]}
    mock_api(aioclient_mock, {}, NOW, accounts=accounts)
    config_entry.add_to_hass(hass)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.LOADED
    assert config_entry.runtime_data.coordinators == {}


async def test_unknown_coordinator_type_is_logged(
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    setup_integration.runtime_data.add_coordinator("connection", "not-a-type", MagicMock())
    await hass.async_block_till_done()

    assert "Unknown coordinator type not-a-type" in caplog.text


@pytest.mark.parametrize(
    "bad_field",
    ["end_date", "gas_last_measured_at"],
)
async def test_unparsable_date_does_not_break_setup(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    connections: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
    bad_field: str,
) -> None:
    contract = _battery_connection(connections)["p1_installation"][0]
    if bad_field == "end_date":
        contract["end_date"] = "2025-13-45T00:00:00Z"
    else:
        contract["meta"][bad_field] = "2025-13-45T00:00:00Z"

    await _setup_with(hass, aioclient_mock, config_entry, connections)

    assert config_entry.state is ConfigEntryState.LOADED
    assert f"Could not parse {bad_field}" in caplog.text


async def test_obsolete_device_without_entities_is_removed(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    connections: dict[str, Any],
) -> None:
    config_entry.add_to_hass(hass)
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(config_entry_id=config_entry.entry_id, identifiers={(DOMAIN, "obsolete")})
    mock_api(aioclient_mock, connections, NOW)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert device_registry.async_get(device.id) is None


async def test_renamed_sensor_keeps_its_entity(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    connections: dict[str, Any],
) -> None:
    config_entry.add_to_hass(hass)
    registry = er.async_get(hass)
    old = registry.async_get_or_create("sensor", DOMAIN, f"{CONNECTION_UUID}_current_tariff", config_entry=config_entry, suggested_object_id="my_tariff")
    mock_api(aioclient_mock, connections, NOW)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert registry.async_get(old.entity_id).unique_id == f"{CONNECTION_UUID}_current_electricity_tariff"
    assert registry.async_get_entity_id("sensor", DOMAIN, f"{CONNECTION_UUID}_current_tariff") is None


async def test_sensor_moves_from_another_connection(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    connections: dict[str, Any],
) -> None:
    """A contract can move between connections of an account, and its price sensors should follow."""
    other = next(uuid for uuid in connections if uuid != CONNECTION_UUID)
    connections[other]["gas"] = [
        {"uuid": "gas-contract", "label": "Gas", "type": "gas", "start_date": "2024-01-01T00:00:00.000000Z", "end_date": None, "meta": {}}
    ]
    config_entry.add_to_hass(hass)
    registry = er.async_get(hass)
    old = registry.async_get_or_create("sensor", DOMAIN, f"{other}_current_tariff_group", config_entry=config_entry, suggested_object_id="my_tariff_group")
    mock_api(aioclient_mock, connections, NOW)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert registry.async_get(old.entity_id).unique_id == f"{CONNECTION_UUID}_current_tariff_group"


async def test_typo_in_forecast_sensor_is_migrated(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    connections: dict[str, Any],
) -> None:
    key = next(key for key in SENSOR_TYPES[ELECTRICITY_PRICES] if key.startswith("forecast_"))
    misspelled = key.replace("forecast_", "forcast_")
    config_entry.add_to_hass(hass)
    registry = er.async_get(hass)
    old = registry.async_get_or_create("sensor", DOMAIN, f"{CONNECTION_UUID}_{misspelled}", config_entry=config_entry, suggested_object_id="my_forecast")
    mock_api(aioclient_mock, connections, NOW)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert registry.async_get(old.entity_id).unique_id == f"{CONNECTION_UUID}_{key}"


async def test_existing_new_sensor_blocks_migration(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    connections: dict[str, Any],
) -> None:
    config_entry.add_to_hass(hass)
    registry = er.async_get(hass)
    old = registry.async_get_or_create("sensor", DOMAIN, f"{CONNECTION_UUID}_current_tariff", config_entry=config_entry, suggested_object_id="old_tariff")
    new = registry.async_get_or_create(
        "sensor", DOMAIN, f"{CONNECTION_UUID}_current_electricity_tariff", config_entry=config_entry, suggested_object_id="new_tariff"
    )
    mock_api(aioclient_mock, connections, NOW)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert registry.async_get(old.entity_id).unique_id == f"{CONNECTION_UUID}_current_tariff"
    assert registry.async_get(new.entity_id).unique_id == f"{CONNECTION_UUID}_current_electricity_tariff"
