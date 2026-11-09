"""Tests for how every coordinator handles API errors and unchanged data."""

import copy
import re
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.zonneplan_one.const import GAS_NEXT_PRICE_HOUR, get_gas_hour
from custom_components.zonneplan_one.coordinators.account_data_coordinator import ConnectionCoordinators
from custom_components.zonneplan_one.coordinators.battery_charts_data_coordinator import _parse_day_chart, _parse_month_chart

from .common import API, BATTERY_UUID, CHARGE_POINT_UUID, CONNECTION_UUID, entity_id_for, load_fixture, mock_api, refresh_coordinators
from .conftest import NOW

GAS_UUID = "gas-contract"
PV_UUID = "pv-contract"
CONNECTION_API = f"{API}/connections/{CONNECTION_UUID}"
ENDPOINTS = {
    "electricity": f"{CONNECTION_API}/summary$",
    "electricity_prices": f"{API}/api/consumer-prices/charts/electricity",
    "gas_prices": f"{API}/api/consumer-prices/charts/gas-daily",
    "p1_electricity": f"{CONNECTION_API}/electricity-delivered$",
    "p1_gas": f"{CONNECTION_API}/gas$",
    "pv_installation": f"{CONNECTION_API}/pv-installation$",
    "electricity_home_consumption": f"{CONNECTION_API}/electricity-home-consumption$",
    "charge_point_installation": f"{CONNECTION_API}/charge-points/{CHARGE_POINT_UUID}$",
    "home_battery_installation": f"{CONNECTION_API}/home-battery-installation/{BATTERY_UUID}$",
    "battery_control": f"{API}/api/contracts/{BATTERY_UUID}/home-battery/control-mode",
    "battery_charts": f"{API}/contracts/{BATTERY_UUID}/home_battery_installation/charts/",
}


@pytest.fixture
def connections(connections: dict[str, Any]) -> dict[str, Any]:
    """Give the default connection every contract type, so that every coordinator exists."""
    connection = connections[CONNECTION_UUID]
    connection["gas"] = [{"uuid": GAS_UUID, "label": "Gas", "type": "gas", "start_date": "2024-01-01T00:00:00.000000Z", "end_date": None, "meta": {}}]
    connection["p1_installation"][0]["meta"]["gas_last_measured_at"] = NOW.isoformat()
    connection["gas_data"] = {"measurement_groups": [], "contracts": []}

    powerplay = load_fixture("connections_powerplay_pv.json")
    source = next(item for item in powerplay.values() if item.get("pv_installation"))
    contract = copy.deepcopy(source["pv_installation"][0])
    contract["uuid"] = PV_UUID
    contract["end_date"] = None
    connection["pv_installation"] = [contract]
    connection["pv_data"] = source["pv_data"]
    return connections


@pytest.fixture
async def coordinators(hass: HomeAssistant, setup_integration: MockConfigEntry) -> ConnectionCoordinators:
    await refresh_coordinators(hass, setup_integration)
    return setup_integration.runtime_data.coordinators[CONNECTION_UUID]


def _respond_with(aioclient_mock: AiohttpClientMocker, connections: dict[str, Any], name: str, status: int) -> None:
    """Make one coordinator's endpoint answer with `status`, keeping the others working."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(re.compile(ENDPOINTS[name]), status=status)
    mock_api(aioclient_mock, connections, NOW)


def test_every_coordinator_has_an_endpoint() -> None:
    assert set(ENDPOINTS) == set(ConnectionCoordinators.__dataclass_fields__) - {"gas"}


@pytest.mark.parametrize("name", ENDPOINTS)
async def test_every_coordinator_has_data_after_setup(coordinators: ConnectionCoordinators, name: str) -> None:
    coordinator = getattr(coordinators, name)

    assert coordinator.last_update_success
    assert coordinator.data is not None


@pytest.mark.parametrize("name", ENDPOINTS)
async def test_unauthorized_starts_reauth(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    coordinators: ConnectionCoordinators,
    connections: dict[str, Any],
    name: str,
) -> None:
    _respond_with(aioclient_mock, connections, name, 401)

    coordinator = getattr(coordinators, name)
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert not coordinator.last_update_success
    assert [flow["context"]["source"] for flow in hass.config_entries.flow.async_progress()] == ["reauth"]


@pytest.mark.parametrize("name", ENDPOINTS)
async def test_server_error_fails_the_update_without_reauth(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    coordinators: ConnectionCoordinators,
    connections: dict[str, Any],
    name: str,
) -> None:
    _respond_with(aioclient_mock, connections, name, 500)

    coordinator = getattr(coordinators, name)
    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert not coordinator.last_update_success
    assert hass.config_entries.flow.async_progress() == []


@pytest.mark.parametrize("name", ENDPOINTS)
async def test_not_modified_keeps_the_data(
    aioclient_mock: AiohttpClientMocker,
    coordinators: ConnectionCoordinators,
    connections: dict[str, Any],
    name: str,
) -> None:
    coordinator = getattr(coordinators, name)
    before = copy.deepcopy(coordinator.data)
    assert before
    _respond_with(aioclient_mock, connections, name, 304)

    await coordinator.async_refresh()

    assert coordinator.last_update_success
    # Compared here rather than with ==, which would diff the whole payload on failure.
    unchanged = coordinator.data == before
    assert unchanged


def _quiet_listener(coordinator: Any, schedule: str) -> MagicMock:
    """Stop the coordinator's polling, which also updates listeners, and restart its price schedule 7.5 minutes into the quarter."""
    coordinator.update_interval = None
    coordinator._unschedule_refresh()
    listener = MagicMock()
    coordinator.async_add_listener(listener)
    getattr(coordinator, schedule)()
    return listener


SCHEDULES = [
    pytest.param("electricity_prices", "_schedule_quarter_hourly_listener_update", timedelta(minutes=15), id="electricity_every_quarter"),
    pytest.param("gas_prices", "_schedule_hourly_listener_update", timedelta(hours=1), id="gas_every_hour"),
]
# Not on a boundary, to show that the schedule follows the clock and not the time of the last update.
MID_QUARTER = NOW + timedelta(minutes=7, seconds=30)
FIRST_BOUNDARY = {"electricity_prices": NOW + timedelta(minutes=15), "gas_prices": NOW + timedelta(hours=1)}


def _price_requests(aioclient_mock: AiohttpClientMocker) -> int:
    """Count price requests only: the coordinators of the other endpoints keep polling."""
    return sum("consumer-prices" in str(url) for _, url, _, _ in aioclient_mock.mock_calls)


def _move_to(hass: HomeAssistant, freezer: Any, moment: datetime) -> None:
    freezer.move_to(moment)
    async_fire_time_changed(hass, moment)


@pytest.mark.parametrize(("name", "schedule", "step"), SCHEDULES)
async def test_sensors_update_on_every_price_boundary_without_an_api_call(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    coordinators: ConnectionCoordinators,
    freezer: Any,
    name: str,
    schedule: str,
    step: timedelta,
) -> None:
    freezer.move_to(MID_QUARTER)
    listener = _quiet_listener(getattr(coordinators, name), schedule)
    requests_before = _price_requests(aioclient_mock)
    boundary = FIRST_BOUNDARY[name]

    _move_to(hass, freezer, boundary - timedelta(seconds=1))
    await hass.async_block_till_done()
    listener.assert_not_called()

    _move_to(hass, freezer, boundary)
    await hass.async_block_till_done()
    assert listener.call_count == 1

    # It schedules itself again, and only for the next boundary.
    _move_to(hass, freezer, boundary + step - timedelta(seconds=1))
    await hass.async_block_till_done()
    assert listener.call_count == 1

    _move_to(hass, freezer, boundary + step)
    await hass.async_block_till_done()
    assert listener.call_count == 2  # noqa: PLR2004
    assert _price_requests(aioclient_mock) == requests_before


@pytest.mark.parametrize(("name", "schedule", "step"), SCHEDULES)
async def test_shutdown_stops_the_price_schedule(
    hass: HomeAssistant,
    coordinators: ConnectionCoordinators,
    freezer: Any,
    name: str,
    schedule: str,
    step: timedelta,
) -> None:
    coordinator = getattr(coordinators, name)
    listener = _quiet_listener(coordinator, schedule)

    await coordinator.async_shutdown()
    _move_to(hass, freezer, NOW + step)
    await hass.async_block_till_done()

    listener.assert_not_called()


async def test_gas_prices_are_indexed_per_hour(coordinators: ConnectionCoordinators) -> None:
    prices = coordinators.gas_prices.data["gas_prices"]
    captured = load_fixture("prices_gas_daily.json")["data"]["chart"]["series"]["prices"]

    assert prices[get_gas_hour("current")]["price_tax_included"]["amount"] == captured[0]["price_tax_included"]["amount"]
    # The captured chart only holds today's price: tomorrow's isn't published yet.
    assert get_gas_hour("next") not in prices


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_gas_sensors_show_todays_price_and_no_next_price_yet(hass: HomeAssistant, coordinators: ConnectionCoordinators) -> None:  # noqa: ARG001
    captured = load_fixture("prices_gas_daily.json")["data"]["chart"]["series"]["prices"]
    current = hass.states.get(entity_id_for(hass, "sensor", f"{CONNECTION_UUID}_current_tariff_gas"))

    assert float(current.state) == pytest.approx(captured[0]["price_tax_included"]["amount"] * 0.0000001)
    assert hass.states.get(entity_id_for(hass, "sensor", f"{CONNECTION_UUID}_next_tariff_gas")).state == "unknown"


async def test_battery_charts_are_parsed_per_period(coordinators: ConnectionCoordinators) -> None:
    charts = coordinators.battery_charts.data

    assert set(charts) == {"this_year", "last_year", "this_month", "last_month"}
    assert charts["this_year"]["year"] == NOW.year
    assert charts["last_year"]["year"] == NOW.year - 1
    assert charts["this_month"]["month"] == "2025-12"
    assert charts["last_month"]["month"] == "2025-11"
    assert charts["this_month"]["total_result"] == pytest.approx(1.0)
    assert charts["this_month"]["total_delivery_kwh"] == pytest.approx(1.0)
    assert charts["this_month"]["total_production_kwh"] == pytest.approx(2.0)


def test_month_chart_groups_values_per_month_in_the_api_time_zone() -> None:
    # 23:30 UTC on the last of November is already December in the Netherlands.
    chart = [{"measurements": [{"measured_at": "2025-11-30T23:30:00Z", "value": 10000000, "meta": {"delivery": 2000}}, {"value": 1}], "total": 0, "meta": {}}]

    parsed = _parse_month_chart(chart, 2025)

    assert parsed["months"] == {"2025-12": {"result": pytest.approx(1.0), "delivery_kwh": pytest.approx(2.0), "production_kwh": 0}}


@pytest.mark.parametrize("parse", [lambda chart: _parse_month_chart(chart, 2025), lambda chart: _parse_day_chart(chart, NOW.date())], ids=["month", "day"])
def test_empty_chart_group_is_ignored(parse: Any) -> None:
    assert parse([{}]) is None


@pytest.mark.parametrize(
    ("now", "current", "following"),
    [
        pytest.param("2025-12-22T18:00:00Z", "2025-12-22", "2025-12-23", id="after_the_daily_change"),
        pytest.param("2025-12-22T02:00:00Z", "2025-12-21", "2025-12-22", id="before_the_daily_change"),
    ],
)
def test_gas_price_day_changes_at_six(freezer: Any, now: str, current: str, following: str) -> None:
    freezer.move_to(now)

    assert get_gas_hour("current") == f"{current} {GAS_NEXT_PRICE_HOUR:02d}"
    assert get_gas_hour("next") == f"{following} {GAS_NEXT_PRICE_HOUR:02d}"
