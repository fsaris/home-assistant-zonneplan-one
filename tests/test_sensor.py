"""Tests that sensors show the values from the API responses."""

from dataclasses import fields
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.zonneplan_one.const import DOMAIN

from .common import load_fixture, mock_api
from .conftest import NOW

CONNECTION = "00000000-0000-4000-8000-000000000019"
BATTERY = "00000000-0000-4000-8000-000000000029"
CHARGE_POINT = "00000000-0000-4000-8000-000000000027"


@pytest.fixture(autouse=True)
async def refreshed_integration(entity_registry_enabled_by_default: None, hass: HomeAssistant, setup_integration: MockConfigEntry) -> None:  # noqa: ARG001
    """
    Refresh every coordinator once more after setup.

    A coordinator's first refresh starts when its first entity subscribes. Mocked responses are
    instant, so it finishes before the other entities subscribe, and those would stay unknown.
    """
    for connection in setup_integration.runtime_data.coordinators.values():
        for field in fields(connection):
            if coordinator := getattr(connection, field.name):
                await coordinator.async_refresh()
    await hass.async_block_till_done()


def _state(hass: HomeAssistant, unique_id: str) -> Any:
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, unique_id)
    assert entity_id, f"no sensor with unique id {unique_id}"
    state = hass.states.get(entity_id)
    assert state, f"{entity_id} has no state"
    return state


@pytest.mark.parametrize(
    ("unique_id", "expected"),
    [
        pytest.param(f"{CONNECTION}_usage", "2764", id="summary"),
        pytest.param(f"{BATTERY}_state_of_charge", "7.0", id="value_factor"),
        pytest.param(f"{BATTERY}_battery_state", "Operative", id="battery_text"),
        pytest.param(f"{CHARGE_POINT}_state", "Standby", id="charge_point"),
    ],
)
async def test_sensor_values(hass: HomeAssistant, unique_id: str, expected: str) -> None:
    assert _state(hass, unique_id).state == expected


async def test_current_tariff_is_the_price_of_the_current_hour(hass: HomeAssistant) -> None:
    # The frozen clock is 18:00 UTC, so the 19th hour of the synthetic chart that starts at 00:00 UTC.
    state = _state(hass, f"{CONNECTION}_current_electricity_tariff")

    assert float(state.state) == pytest.approx((2000000 + 18 * 100) * 0.0000001)
    assert len(state.attributes["forecast"]) == 48  # noqa: PLR2004


@pytest.mark.parametrize(
    ("fixture_name", "expected"),
    [
        pytest.param("summary_with_usage.json", "662", id="with_usage"),
        pytest.param("summary_without_usage.json", "0", id="without_usage"),
    ],
)
async def test_usage_follows_the_summary_response(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: MockConfigEntry,
    connections: dict[str, Any],
    fixture_name: str,
    expected: str,
) -> None:
    connections[CONNECTION]["summary_data"] = load_fixture(fixture_name)
    aioclient_mock.clear_requests()
    mock_api(aioclient_mock, connections, NOW)

    await setup_integration.runtime_data.coordinators[CONNECTION].electricity.async_refresh()
    await hass.async_block_till_done()

    assert _state(hass, f"{CONNECTION}_usage").state == expected
