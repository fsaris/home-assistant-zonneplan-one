"""Tests for the charge point controls: buttons, dynamic charging and the vehicle select."""

from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientResponseError
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed, mock_restore_cache
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.zonneplan_one.api import ZonneplanRateLimitError
from custom_components.zonneplan_one.const import DOMAIN
from custom_components.zonneplan_one.coordinators.charge_point_data_coordinator import ChargePointDataUpdateCoordinator

from .common import CHARGE_POINT_UUID, CONNECTION_UUID, entity_id_for, mock_api, posted_actions, refresh_coordinators
from .conftest import NOW

ACTIONS = f"/charge-points/{CHARGE_POINT_UUID}/actions"
DYNAMIC_SESSION = f"{ACTIONS}/start_dynamic_charging_session"
PERCENTAGE_KEY = f"{CHARGE_POINT_UUID}_dynamic_charging_user_constraints.desired_additional_battery_percentage"
KILOMETERS_KEY = f"{CHARGE_POINT_UUID}_dynamic_charging_user_constraints.desired_distance_in_kilometers"
END_TIME_KEY = f"{CHARGE_POINT_UUID}_dynamic_charging_user_constraints.desired_end_time"
VEHICLE_KEY = f"{CHARGE_POINT_UUID}_selected_vehicle"
VEHICLES = [
    {"uuid": "vehicle-1", "label": "Car one", "consumption_wh_per_km": 200, "battery_capacity_useable_wh": 60000},
    {"uuid": "vehicle-2", "label": "Car two", "consumption_wh_per_km": 150, "battery_capacity_useable_wh": 30000},
]
# In the API time zone, which is an hour ahead of the frozen UTC clock in December.
END_TIME = NOW + timedelta(hours=2)
END_TIME_API = "2025-12-22 21:00:00"


@pytest.fixture
def connections(connections: dict[str, Any]) -> dict[str, Any]:
    connections[CONNECTION_UUID]["vehicles"] = VEHICLES
    return connections


@pytest.fixture
async def coordinator(
    entity_registry_enabled_by_default: None,  # noqa: ARG001
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> ChargePointDataUpdateCoordinator:
    await refresh_coordinators(hass, setup_integration)
    return setup_integration.runtime_data.coordinators[CONNECTION_UUID].charge_point_installation


def _patch_state(coordinator: ChargePointDataUpdateCoordinator, **state: Any) -> None:
    coordinator.data["state"].update(state)
    coordinator.async_update_listeners()


def _constraints(coordinator: ChargePointDataUpdateCoordinator, **constraints: Any) -> None:
    coordinator.data["state"]["dynamic_charging_user_constraints"].update(constraints)


async def _press(hass: HomeAssistant, key: str) -> None:
    await hass.services.async_call("button", "press", {"entity_id": entity_id_for(hass, "button", f"{CHARGE_POINT_UUID}_{key}")}, blocking=True)
    await hass.async_block_till_done()


async def _set_number(hass: HomeAssistant, unique_id: str, value: float) -> None:
    await hass.services.async_call("number", "set_value", {"entity_id": entity_id_for(hass, "number", unique_id), "value": value}, blocking=True)
    await hass.async_block_till_done()


async def _set_end_time(hass: HomeAssistant, value: Any) -> None:
    await hass.services.async_call("datetime", "set_value", {"entity_id": entity_id_for(hass, "datetime", END_TIME_KEY), "datetime": value}, blocking=True)
    await hass.async_block_till_done()


@pytest.mark.parametrize(
    ("key", "state", "expected_actions"),
    [
        pytest.param("start", {"state": "VehicleDetected"}, ["start_boost"], id="start"),
        pytest.param("stop", {"state": "Charging"}, ["stop_charging"], id="stop"),
        pytest.param("continue_auto_charging", {"dynamic_charging_flex_suppressed": True}, ["unsuppress_always_flex"], id="continue_auto"),
        pytest.param(
            "reset_dynamic_charge",
            {"dynamic_charging_user_constraints": {"desired_end_time": "2025-12-22T21:00:00+01:00"}},
            ["stop_dynamic_charging_session", "reset_schedule"],
            id="reset",
        ),
    ],
)
async def test_button_posts_its_action(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    coordinator: ChargePointDataUpdateCoordinator,
    key: str,
    state: dict[str, Any],
    expected_actions: list[str],
) -> None:
    _patch_state(coordinator, **state)

    await _press(hass, key)

    assert [path for path, _ in posted_actions(aioclient_mock)] == [f"{ACTIONS}/{action}" for action in expected_actions]


@pytest.mark.parametrize(
    ("key", "state", "available"),
    [
        ("start", {"state": "VehicleDetected"}, True),
        ("start", {"state": "Standby"}, False),
        ("stop", {"state": "Charging"}, True),
        ("stop", {"state": "VehicleDetected"}, False),
        ("continue_auto_charging", {"dynamic_charging_flex_suppressed": True}, True),
        ("continue_auto_charging", {"dynamic_charging_flex_suppressed": False}, False),
        ("start", {"state": "VehicleDetected", "connectivity_state": False}, False),
        ("start", {"state": "VehicleDetected", "processing": True}, False),
    ],
)
async def test_button_availability_follows_the_charging_state(
    hass: HomeAssistant,
    coordinator: ChargePointDataUpdateCoordinator,
    key: str,
    state: dict[str, Any],
    available: bool,  # noqa: FBT001
) -> None:
    _patch_state(coordinator, **state)

    current = hass.states.get(entity_id_for(hass, "button", f"{CHARGE_POINT_UUID}_{key}"))

    assert (current.state != STATE_UNAVAILABLE) is available


async def test_unavailable_button_posts_nothing(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, coordinator: ChargePointDataUpdateCoordinator
) -> None:
    _patch_state(coordinator, state="Standby")

    await _press(hass, "start")

    assert posted_actions(aioclient_mock) == []


async def test_action_refetches_state_and_clears_processing(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    coordinator: ChargePointDataUpdateCoordinator,
) -> None:
    await coordinator.async_stop_charge()
    await hass.async_block_till_done()

    assert posted_actions(aioclient_mock) == [(f"{ACTIONS}/stop_charging", {})]
    assert "processing" not in coordinator.data["state"]


async def test_action_retries_after_10_seconds_while_the_api_is_still_processing(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    coordinator: ChargePointDataUpdateCoordinator,
    connections: dict[str, Any],
    freezer: Any,
) -> None:
    processing = connections[CONNECTION_UUID]["charge_point_data"]
    processing["state"]["processing"] = True
    aioclient_mock.clear_requests()
    mock_api(aioclient_mock, connections, NOW)

    await coordinator.async_stop_charge()
    await hass.async_block_till_done()
    assert coordinator.data["state"]["processing"] is True

    del processing["state"]["processing"]
    aioclient_mock.clear_requests()
    mock_api(aioclient_mock, connections, NOW)
    freezer.tick(timedelta(seconds=11))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert "processing" not in coordinator.data["state"]


async def test_dynamic_charge_with_percentage(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, coordinator: ChargePointDataUpdateCoordinator) -> None:
    _constraints(coordinator, desired_end_time=END_TIME.isoformat())

    await _set_number(hass, PERCENTAGE_KEY, 50)

    assert posted_actions(aioclient_mock) == [
        (
            DYNAMIC_SESSION,
            {
                "user_constraints": {"desired_end_time": END_TIME_API, "unit": "percentage", "value": 500},
                "vehicle": {"vehicle_uuid": "vehicle-1"},
            },
        )
    ]


async def test_dynamic_charge_with_kilometers(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, coordinator: ChargePointDataUpdateCoordinator) -> None:
    _constraints(coordinator, desired_end_time=END_TIME.isoformat())

    await _set_number(hass, KILOMETERS_KEY, 120)

    assert posted_actions(aioclient_mock)[0][1]["user_constraints"] == {"desired_end_time": END_TIME_API, "unit": "kilometers", "value": 120}


async def test_setting_end_time_starts_the_session(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, coordinator: ChargePointDataUpdateCoordinator
) -> None:
    _constraints(coordinator, desired_distance_in_kilometers=120)

    await _set_end_time(hass, END_TIME)

    assert posted_actions(aioclient_mock)[0][1]["user_constraints"] == {"desired_end_time": END_TIME_API, "unit": "kilometers", "value": 120}


@pytest.mark.parametrize(
    ("edited_unit", "expected"),
    [
        pytest.param("percentage", {"unit": "percentage", "value": 500}, id="percentage_edited_last"),
        pytest.param("kilometers", {"unit": "kilometers", "value": 120}, id="kilometers_edited_last"),
        pytest.param(None, {"unit": "kilometers", "value": 120}, id="nothing_edited_prefers_kilometers"),
    ],
)
async def test_dynamic_charge_uses_the_unit_edited_last(
    aioclient_mock: AiohttpClientMocker,
    coordinator: ChargePointDataUpdateCoordinator,
    edited_unit: str | None,
    expected: dict[str, Any],
) -> None:
    _constraints(coordinator, desired_end_time=END_TIME.isoformat(), desired_distance_in_kilometers=120, desired_additional_battery_percentage=500)

    await coordinator.async_dynamic_charge(edited_unit)

    user_constraints = posted_actions(aioclient_mock)[0][1]["user_constraints"]
    assert {key: user_constraints[key] for key in ("unit", "value")} == expected


@pytest.mark.parametrize(
    "constraints",
    [
        pytest.param({"desired_additional_battery_percentage": 500}, id="no_end_time"),
        pytest.param({"desired_end_time": (NOW + timedelta(minutes=14)).isoformat(), "desired_additional_battery_percentage": 500}, id="end_time_too_soon"),
        pytest.param({"desired_end_time": (NOW - timedelta(hours=1)).isoformat(), "desired_additional_battery_percentage": 500}, id="end_time_passed"),
        pytest.param({"desired_end_time": END_TIME.isoformat()}, id="no_amount"),
    ],
)
async def test_incomplete_dynamic_charge_posts_nothing(
    aioclient_mock: AiohttpClientMocker,
    coordinator: ChargePointDataUpdateCoordinator,
    constraints: dict[str, Any],
) -> None:
    _constraints(coordinator, **constraints)

    await coordinator.async_dynamic_charge()

    assert posted_actions(aioclient_mock) == []


async def test_end_time_too_close_is_refused(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, coordinator: ChargePointDataUpdateCoordinator) -> None:
    _constraints(coordinator, desired_distance_in_kilometers=120)

    with pytest.raises(ValueError, match="too close"):
        await _set_end_time(hass, NOW + timedelta(minutes=5))

    assert posted_actions(aioclient_mock) == []


async def test_reset_continues_when_there_is_no_session_to_stop(coordinator: ChargePointDataUpdateCoordinator) -> None:
    rejected = ClientResponseError(MagicMock(), (), status=422)

    with patch.object(coordinator.api, "async_post", AsyncMock(side_effect=[rejected, {"ok": True}])) as post:
        await coordinator.async_reset_dynamic_charge()

    assert [call.args[1] for call in post.call_args_list] == [f"{ACTIONS}/stop_dynamic_charging_session", f"{ACTIONS}/reset_schedule"]


async def test_reset_stops_on_rate_limit(coordinator: ChargePointDataUpdateCoordinator) -> None:
    limited = ZonneplanRateLimitError(MagicMock(), (), status=429)

    with patch.object(coordinator.api, "async_post", AsyncMock(side_effect=limited)) as post, pytest.raises(ZonneplanRateLimitError):
        await coordinator.async_reset_dynamic_charge()

    assert post.call_count == 1


async def test_vehicle_select_defaults_to_the_first_vehicle(hass: HomeAssistant, coordinator: ChargePointDataUpdateCoordinator) -> None:
    state = hass.states.get(entity_id_for(hass, "select", VEHICLE_KEY))

    assert state.state == "Car one"
    assert state.attributes["options"] == ["Car one", "Car two"]
    assert coordinator.selected_vehicle_uuid == "vehicle-1"


async def test_selected_vehicle_sets_the_kilometer_limit(hass: HomeAssistant, coordinator: ChargePointDataUpdateCoordinator) -> None:
    number = entity_id_for(hass, "number", KILOMETERS_KEY)
    assert hass.states.get(number).attributes["max"] == 300  # noqa: PLR2004

    await hass.services.async_call("select", "select_option", {"entity_id": entity_id_for(hass, "select", VEHICLE_KEY), "option": "Car two"}, blocking=True)
    await hass.async_block_till_done()

    assert coordinator.selected_vehicle_uuid == "vehicle-2"
    assert hass.states.get(number).attributes["max"] == 200  # noqa: PLR2004


@pytest.mark.parametrize(
    "vehicle",
    [
        pytest.param(None, id="unknown_vehicle"),
        pytest.param({"uuid": "vehicle-1", "consumption_wh_per_km": 0, "battery_capacity_useable_wh": 60000}, id="no_consumption"),
        pytest.param({"uuid": "vehicle-1", "consumption_wh_per_km": 200}, id="no_capacity"),
    ],
)
async def test_kilometer_limit_needs_complete_vehicle_specs(coordinator: ChargePointDataUpdateCoordinator, vehicle: dict[str, Any] | None) -> None:
    coordinator.vehicles = [vehicle] if vehicle else []

    assert coordinator.get_max_desired_kilometers() is None


async def test_vehicle_select_restores_the_previous_choice(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    connections: dict[str, Any],
) -> None:
    config_entry.add_to_hass(hass)
    entry = er.async_get(hass).async_get_or_create("select", DOMAIN, VEHICLE_KEY, config_entry=config_entry)
    mock_restore_cache(hass, [State(entry.entity_id, "Car two")])
    mock_api(aioclient_mock, connections, NOW)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    await refresh_coordinators(hass, config_entry)

    assert hass.states.get(entry.entity_id).state == "Car two"
