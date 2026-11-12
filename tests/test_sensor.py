"""Tests that sensors show the values from the API responses."""

from datetime import datetime
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.zonneplan_one.electricity_market_prices import epex_price_from_tax_excluded_amount, tax_excluded_amount_to_eur_kwh

from .common import BATTERY_UUID, CHARGE_POINT_UUID, CONNECTION_UUID, entity_id_for, load_fixture, mock_api, price_chart, refresh_coordinators
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


def _captured_price(name: str, start: str) -> int:
    prices = load_fixture(name)["data"]["chart"]["series"]["prices"]
    return next(price["price_tax_included"]["amount"] for price in prices if price["start_date"] == start)


async def test_current_return_and_epex_prices(hass: HomeAssistant) -> None:
    chart = price_chart("prices_electricity_quarter_hourly.json", NOW)
    prices = chart["chart"]["series"]["prices"]
    current = next(price for price in prices if datetime.fromisoformat(price["start_date"]) <= NOW < datetime.fromisoformat(price["end_date"]))
    current_index = prices.index(current)
    next_quarter = prices[current_index + 1] if current_index + 1 < len(prices) else None

    return_state = _state(hass, f"{CONNECTION}_current_return_price")
    epex_state = _state(hass, f"{CONNECTION}_current_epex_price")

    base = tax_excluded_amount_to_eur_kwh(current["price_tax_excluded"]["amount"])
    assert float(return_state.state) == pytest.approx(base)
    assert float(epex_state.state) == pytest.approx(epex_price_from_tax_excluded_amount(current["price_tax_excluded"]["amount"]))
    assert return_state.attributes["bonus_active"] is False
    if next_quarter:
        assert return_state.attributes["next_quarter"] == pytest.approx(tax_excluded_amount_to_eur_kwh(next_quarter["price_tax_excluded"]["amount"]))
        assert epex_state.attributes["next_quarter"] == pytest.approx(epex_price_from_tax_excluded_amount(next_quarter["price_tax_excluded"]["amount"]))


async def test_current_tariff_is_the_price_of_the_current_hour(hass: HomeAssistant) -> None:
    # The captured chart is moved to the frozen day, so its 18:00 UTC price is the current one.
    state = _state(hass, f"{CONNECTION}_current_electricity_tariff")

    assert float(state.state) == pytest.approx(_captured_price("prices_electricity_hourly.json", "2026-11-08T18:00:00+00:00") * 0.0000001)
    assert len(state.attributes["forecast"]) == len(load_fixture("prices_electricity_hourly.json")["data"]["chart"]["series"]["prices"])


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


@pytest.mark.parametrize(
    "measured_at",
    [
        pytest.param("2025-12-22T18:00:00.000000Z", id="iso_string"),
        pytest.param(1766426400000, id="milliseconds"),
        pytest.param(1766426400000000, id="microseconds"),
    ],
)
async def test_timestamps_are_read_in_every_format(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    setup_integration: MockConfigEntry,
    connections: dict[str, Any],
    measured_at: str | int,
) -> None:
    summary = connections[CONNECTION]["summary_data"]
    summary["usage"]["measured_at"] = measured_at
    aioclient_mock.clear_requests()
    mock_api(aioclient_mock, connections, NOW)

    await setup_integration.runtime_data.coordinators[CONNECTION].electricity.async_refresh()
    await hass.async_block_till_done()

    assert _state(hass, f"{CONNECTION}_usage_measured_at").state == "2025-12-22T18:00:00+00:00"
