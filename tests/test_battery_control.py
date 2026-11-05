"""Tests for the battery controls: control mode, power limits and the backup reserve."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.zonneplan_one.coordinators.battery_control_data_coordinator import BatteryControlDataUpdateCoordinator

from .common import BATTERY_UUID, CONNECTION_UUID, entity_id_for, posted_actions, refresh_coordinators

ACTIONS = f"/home-battery-installation/{BATTERY_UUID}/actions"
MODE_KEY = f"{BATTERY_UUID}_control_mode"
CHARGE_KEY = f"{BATTERY_UUID}_max_desired_charge_power_watts"
DISCHARGE_KEY = f"{BATTERY_UUID}_max_desired_discharge_power_watts"
RESERVE_KEY = f"{BATTERY_UUID}_reserve_discharge_cutoff_wh"


@pytest.fixture
def connections(connections: dict[str, Any]) -> dict[str, Any]:
    meta = connections[CONNECTION_UUID]["battery_data"]["contracts"][0]["meta"]
    meta["backup_power_capable"] = True
    meta["backup_power_usable_capacity_wh"] = 5000
    meta["reserve_discharge_cutoff_wh"] = 1000
    return connections


@pytest.fixture
async def coordinator(
    entity_registry_enabled_by_default: None,  # noqa: ARG001
    hass: HomeAssistant,
    setup_integration: MockConfigEntry,
) -> BatteryControlDataUpdateCoordinator:
    await refresh_coordinators(hass, setup_integration)
    return setup_integration.runtime_data.coordinators[CONNECTION_UUID].battery_control


def _set_modes(coordinator: BatteryControlDataUpdateCoordinator, **enabled: bool) -> None:
    for mode, value in enabled.items():
        coordinator.data["battery_control_mode"]["modes"][mode]["enabled"] = value


async def _select(hass: HomeAssistant, option: str) -> None:
    await hass.services.async_call("select", "select_option", {"entity_id": entity_id_for(hass, "select", MODE_KEY), "option": option}, blocking=True)
    await hass.async_block_till_done()


async def _set_number(hass: HomeAssistant, unique_id: str, value: float) -> None:
    await hass.services.async_call("number", "set_value", {"entity_id": entity_id_for(hass, "number", unique_id), "value": value}, blocking=True)
    await hass.async_block_till_done()


@pytest.mark.usefixtures("coordinator")
async def test_mode_select_shows_the_current_mode_and_available_options(hass: HomeAssistant) -> None:
    state = hass.states.get(entity_id_for(hass, "select", MODE_KEY))

    assert state.state == "home_optimization"
    assert state.attributes["options"] == ["dynamic_charging", "home_optimization", "self_consumption"]


async def test_unavailable_mode_is_not_an_option(hass: HomeAssistant, coordinator: BatteryControlDataUpdateCoordinator) -> None:
    coordinator.data["battery_control_mode"]["modes"]["self_consumption"]["available"] = False
    coordinator.async_update_listeners()

    assert "self_consumption" not in hass.states.get(entity_id_for(hass, "select", MODE_KEY)).attributes["options"]


@pytest.mark.parametrize(
    ("option", "enabled", "expected"),
    [
        pytest.param(
            "self_consumption", {"home_optimization": True}, ["enable_self_consumption", "disable_home_optimization"], id="self_consumption_from_optimization"
        ),
        pytest.param("self_consumption", {"home_optimization": False}, ["enable_self_consumption"], id="self_consumption_only"),
        pytest.param(
            "dynamic_charging",
            {"home_optimization": True, "self_consumption": True},
            ["disable_home_optimization", "disable_self_consumption"],
            id="dynamic_from_both",
        ),
        pytest.param("dynamic_charging", {"home_optimization": False, "self_consumption": False}, [], id="dynamic_already_active"),
        pytest.param("home_optimization", {"self_consumption": False}, ["enable_home_optimization"], id="optimization"),
        pytest.param(
            "home_optimization", {"self_consumption": True}, ["enable_home_optimization", "disable_self_consumption"], id="optimization_from_self_consumption"
        ),
    ],
)
async def test_selecting_a_mode_posts_the_needed_actions(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    coordinator: BatteryControlDataUpdateCoordinator,
    option: str,
    enabled: dict[str, bool],
    expected: list[str],
) -> None:
    _set_modes(coordinator, **enabled)

    await _select(hass, option)

    assert [path for path, _ in posted_actions(aioclient_mock)] == [f"{ACTIONS}/{action}" for action in expected]


async def test_home_optimization_sends_the_current_power_limits(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    coordinator: BatteryControlDataUpdateCoordinator,
) -> None:
    await _select(hass, "home_optimization")

    assert coordinator.is_mode_enabled("home_optimization")
    assert posted_actions(aioclient_mock)[0][1] == {"max_desired_charge_power_w": 1000, "max_desired_discharge_power_w": 1000}


async def test_home_optimization_without_limits_sends_no_params(aioclient_mock: AiohttpClientMocker, coordinator: BatteryControlDataUpdateCoordinator) -> None:
    coordinator.data["battery_home_optimization"]["max_desired_charge_power_watts"] = None
    coordinator.data["battery_home_optimization"]["max_desired_discharge_power_watts"] = None

    await coordinator.async_enable_home_optimization()

    assert posted_actions(aioclient_mock) == [(f"{ACTIONS}/enable_home_optimization", {})]


async def test_home_optimization_with_one_limit_is_skipped(aioclient_mock: AiohttpClientMocker, coordinator: BatteryControlDataUpdateCoordinator) -> None:
    coordinator.data["battery_home_optimization"]["max_desired_discharge_power_watts"] = None

    await coordinator.async_enable_home_optimization()

    assert posted_actions(aioclient_mock) == []


async def test_home_optimization_stores_the_limits_the_api_accepted(coordinator: BatteryControlDataUpdateCoordinator) -> None:
    response = {"max_desired_charge_power_w": 800, "max_desired_discharge_power_w": 900}
    with (
        patch.object(coordinator.api, "async_post", AsyncMock(return_value=response)),
        patch.object(coordinator.api, "async_get_battery_control_mode", AsyncMock(return_value=None)),
        patch.object(coordinator.api, "async_get_battery_home_optimization", AsyncMock(return_value=None)),
    ):
        await coordinator.async_enable_home_optimization()

    assert coordinator.data["battery_home_optimization"]["max_desired_charge_power_watts"] == 800  # noqa: PLR2004
    assert coordinator.data["battery_home_optimization"]["max_desired_discharge_power_watts"] == 900  # noqa: PLR2004


async def test_processing_is_cleared_when_the_mode_did_not_change(coordinator: BatteryControlDataUpdateCoordinator) -> None:
    coordinator.data["battery_control_mode"]["processing"] = True

    with (
        patch.object(coordinator.api, "async_get_battery_control_mode", AsyncMock(return_value=None)),
        patch.object(coordinator.api, "async_get_battery_home_optimization", AsyncMock(return_value=None)),
    ):
        await coordinator.async_fetch_battery_control_mode()

    assert coordinator.data["battery_control_mode"]["processing"] is False


@pytest.mark.usefixtures("coordinator")
async def test_power_number_uses_the_limits_from_the_api(hass: HomeAssistant) -> None:
    state = hass.states.get(entity_id_for(hass, "number", CHARGE_KEY))

    assert float(state.state) == 1000  # noqa: PLR2004
    assert state.attributes["min"] == 0
    assert state.attributes["max"] == 10000  # noqa: PLR2004


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        pytest.param(CHARGE_KEY, {"max_desired_charge_power_w": 750, "max_desired_discharge_power_w": 1000}, id="charge"),
        pytest.param(DISCHARGE_KEY, {"max_desired_charge_power_w": 1000, "max_desired_discharge_power_w": 750}, id="discharge"),
    ],
)
@pytest.mark.usefixtures("coordinator")
async def test_setting_a_power_limit_enables_optimization_with_it(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    key: str,
    expected: dict[str, int],
) -> None:
    await _set_number(hass, key, 750)

    assert posted_actions(aioclient_mock)[0] == (f"{ACTIONS}/enable_home_optimization", expected)


async def test_power_numbers_are_only_available_in_home_optimization(hass: HomeAssistant, coordinator: BatteryControlDataUpdateCoordinator) -> None:
    coordinator.data["battery_control_mode"]["control_mode"] = "self_consumption"
    coordinator.async_update_listeners()

    assert hass.states.get(entity_id_for(hass, "number", CHARGE_KEY)).state == STATE_UNAVAILABLE


@pytest.mark.usefixtures("coordinator")
async def test_reserve_number_uses_the_usable_capacity_as_limit(hass: HomeAssistant) -> None:
    state = hass.states.get(entity_id_for(hass, "number", RESERVE_KEY))

    assert float(state.state) == 1000  # noqa: PLR2004
    assert state.attributes["max"] == 5000  # noqa: PLR2004


@pytest.mark.usefixtures("coordinator")
async def test_setting_the_reserve_posts_it(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    await _set_number(hass, RESERVE_KEY, 2000)

    assert posted_actions(aioclient_mock) == [(f"{ACTIONS}/set_backup_power_reserved_state_of_charge", {"reserved_state_of_charge_wh": 2000})]


async def test_reserve_number_needs_a_backup_capable_battery(hass: HomeAssistant, coordinator: BatteryControlDataUpdateCoordinator) -> None:
    battery = coordinator.config_entry.runtime_data.coordinators[CONNECTION_UUID].home_battery_installation
    battery.data["contracts"][0]["meta"]["backup_power_capable"] = False
    battery.async_update_listeners()

    assert hass.states.get(entity_id_for(hass, "number", RESERVE_KEY)).state == STATE_UNAVAILABLE
