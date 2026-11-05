"""Tests for setting up and unloading the integration."""

from datetime import timedelta
from typing import Any

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.zonneplan_one.const import DOMAIN

from .common import API, CONNECTION_FIXTURES, connections_from_fixture, mock_api
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
