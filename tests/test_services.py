"""Tests for the fetch_statistics service."""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zonneplan_one.const import DOMAIN, ZONNEPLAN_API_TIME_ZONE
from custom_components.zonneplan_one.coordinators.electricity_data_coordinator import ElectricityDataUpdateCoordinator
from custom_components.zonneplan_one.coordinators.gas_data_coordinator import GasDataUpdateCoordinator

from .common import CONNECTION_UUID
from .conftest import NOW

SERVICE = "fetch_statistics"
START = datetime(2025, 12, 1, tzinfo=ZONNEPLAN_API_TIME_ZONE)


@pytest.fixture
def connections(connections: dict[str, Any]) -> dict[str, Any]:
    connections[CONNECTION_UUID]["p1_installation"][0]["meta"]["gas_last_measured_at"] = NOW.isoformat()
    connections[CONNECTION_UUID]["gas_data"] = {"measurement_groups": [], "contracts": []}
    return connections


@pytest.fixture
def backfill_electricity() -> Any:
    with patch.object(ElectricityDataUpdateCoordinator, "async_backfill_statistics", AsyncMock()) as mock:
        yield mock


@pytest.fixture
def backfill_gas() -> Any:
    with patch.object(GasDataUpdateCoordinator, "async_backfill_statistics", AsyncMock()) as mock:
        yield mock


async def _call(hass: HomeAssistant, **data: Any) -> Any:
    response = await hass.services.async_call(DOMAIN, SERVICE, data, blocking=True, return_response=True)
    await hass.async_block_till_done()
    return response


@pytest.mark.usefixtures("setup_integration")
async def test_service_is_registered(hass: HomeAssistant) -> None:
    assert hass.services.has_service(DOMAIN, SERVICE)


@pytest.mark.parametrize("start_date", ["20251201", "2025-12-01"])
@pytest.mark.usefixtures("setup_integration", "backfill_gas")
async def test_electricity_backfill_accepts_both_date_formats(hass: HomeAssistant, backfill_electricity: AsyncMock, start_date: str) -> None:
    response = await _call(hass, endpoint="electricity", start_date=start_date)

    assert response == {"result": "Check notifications for progress."}
    backfill_electricity.assert_awaited_once_with(START)


@pytest.mark.usefixtures("setup_integration")
async def test_endpoint_selects_the_coordinator(hass: HomeAssistant, backfill_electricity: AsyncMock, backfill_gas: AsyncMock) -> None:
    await _call(hass, endpoint="gas", start_date="20251201")

    backfill_gas.assert_awaited_once_with(START)
    backfill_electricity.assert_not_awaited()


@pytest.mark.parametrize("start_date", ["2025/12/01", "01-12-2025", "yesterday", "20251345"])
@pytest.mark.usefixtures("setup_integration")
async def test_invalid_date_is_refused(hass: HomeAssistant, backfill_electricity: AsyncMock, start_date: str) -> None:
    with pytest.raises(ServiceValidationError, match="Invalid start_date"):
        await _call(hass, endpoint="electricity", start_date=start_date)

    backfill_electricity.assert_not_awaited()


@pytest.mark.usefixtures("setup_integration")
async def test_unknown_endpoint_is_refused(hass: HomeAssistant) -> None:
    with pytest.raises(vol.Invalid):
        await _call(hass, endpoint="water", start_date="20251201")


@pytest.mark.parametrize(
    ("connection_uuid", "expected_calls"),
    [
        pytest.param(CONNECTION_UUID, 1, id="dashes"),
        pytest.param(CONNECTION_UUID.replace("-", "_"), 1, id="underscores_as_in_statistic_ids"),
        pytest.param("00000000-0000-4000-8000-999999999999", 0, id="other_connection"),
    ],
)
@pytest.mark.usefixtures("setup_integration")
async def test_connection_filter(hass: HomeAssistant, backfill_electricity: AsyncMock, connection_uuid: str, expected_calls: int) -> None:
    await _call(hass, endpoint="electricity", start_date="20251201", connection_uuid=connection_uuid)

    assert backfill_electricity.await_count == expected_calls


async def test_unloaded_entry_is_skipped(hass: HomeAssistant, setup_integration: MockConfigEntry, backfill_electricity: AsyncMock) -> None:
    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    await hass.async_block_till_done()

    await _call(hass, endpoint="electricity", start_date="20251201")

    backfill_electricity.assert_not_awaited()
