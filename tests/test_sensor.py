"""Tests that sensors show the values from the API responses."""

from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from .common import BATTERY_UUID, CHARGE_POINT_UUID, CONNECTION_UUID, entity_id_for, load_fixture, mock_api, refresh_coordinators
from .conftest import NOW

CONNECTION = CONNECTION_UUID
BATTERY = BATTERY_UUID
CHARGE_POINT = CHARGE_POINT_UUID


@pytest.fixture(autouse=True)
async def refreshed_integration(entity_registry_enabled_by_default: None, hass: HomeAssistant, setup_integration: MockConfigEntry) -> None:  # noqa: ARG001
    await refresh_coordinators(hass, setup_integration)


def _state(hass: HomeAssistant, unique_id: str) -> Any:
    state = hass.states.get(entity_id_for(hass, "sensor", unique_id))
    assert state, f"sensor {unique_id} has no state"
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
