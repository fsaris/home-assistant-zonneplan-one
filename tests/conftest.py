"""Fixtures for the Zonneplan tests."""

from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any
from unittest.mock import PropertyMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.zonneplan_one.const import DOMAIN

from .common import connections_from_fixture, mock_api

# Just after the last measurement in the default fixture. The integration judges gas meters and
# contract end dates relative to now, so the clock has to match the captured data.
NOW = datetime(2025, 12, 22, 18, 0, tzinfo=UTC)
DEFAULT_FIXTURE = "connections_battery_charge_point_control.json"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(request: pytest.FixtureRequest) -> None:
    """
    Let Home Assistant load the integration from custom_components, in tests that use `hass`.

    The integration depends on recorder, which has to start before the `hass` fixture.
    """
    if "hass" in request.fixturenames:
        request.getfixturevalue("recorder_mock")
        request.getfixturevalue("enable_custom_integrations")


@pytest.fixture
def entity_registry_enabled_by_default() -> Generator[None]:
    """Enable the sensors that are disabled by default, so their state can be checked."""
    with patch("homeassistant.helpers.entity.Entity.entity_registry_enabled_default", new_callable=PropertyMock, return_value=True):
        yield


@pytest.fixture(autouse=True)
def frozen_time(freezer: Any) -> None:
    freezer.move_to(NOW)


@pytest.fixture
def config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id=DOMAIN,
        title="user@example.com",
        data={
            "auth_implementation": DOMAIN,
            "email": "user@example.com",
            "token": {
                "access_token": "test-access-token",
                "refresh_token": "test-refresh-token",
                "token_type": "Bearer",
                "expires_at": NOW.timestamp() + 3600,
            },
        },
    )


@pytest.fixture
def connections() -> dict[str, dict[str, Any]]:
    return connections_from_fixture(DEFAULT_FIXTURE)


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    config_entry: MockConfigEntry,
    connections: dict[str, dict[str, Any]],
) -> MockConfigEntry:
    """Set up the integration against the captured responses of `connections`."""
    mock_api(aioclient_mock, connections, NOW)
    config_entry.add_to_hass(hass)
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
    return config_entry
