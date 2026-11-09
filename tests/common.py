"""Helpers for serving anonymized API responses to the integration."""

import json
import re
from dataclasses import fields
from datetime import date, datetime
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.zonneplan_one.const import DOMAIN, ZONNEPLAN_API_TIME_ZONE

API = "https://app-api.zonneplan.nl"
FIXTURE_DIR = Path(__file__).parent / "fixtures"
CONTRACT_KEYS = (
    "pv_installation",
    "p1_installation",
    "electricity",
    "gas",
    "charge_point_installation",
    "home_battery_installation",
)
# The connection and contracts of the default fixture, connections_battery_charge_point_control.json.
CONNECTION_UUID = "00000000-0000-4000-8000-000000000019"
BATTERY_UUID = "00000000-0000-4000-8000-000000000029"
CHARGE_POINT_UUID = "00000000-0000-4000-8000-000000000027"
CONNECTION_FIXTURES = sorted(path.name for path in FIXTURE_DIR.glob("connection*.json"))


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURE_DIR / name).read_text())


def connections_from_fixture(name: str) -> dict[str, dict[str, Any]]:
    """Return a captured coordinator dump as {connection uuid: connection data}."""
    data = load_fixture(name)
    # Older dumps hold a single connection, without the uuid level around it.
    return {data["uuid"]: data} if "uuid" in data else data


def accounts_from_connections(connections: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Build the `user-accounts/me` payload that belongs to a coordinator dump."""
    return {
        "user_account": {"uuid": "account", "email": "user@example.com"},
        "address_groups": [
            {
                "uuid": "address-group",
                "connections": [
                    {
                        "uuid": connection_uuid,
                        "contracts": [contract for key in CONTRACT_KEYS for contract in connection.get(key) or []],
                    }
                    for connection_uuid, connection in connections.items()
                ],
            }
        ],
    }


# The price charts were captured on this day, in the API time zone.
PRICE_CHART_DAY = date(2026, 11, 8)


def price_chart(name: str, now: datetime) -> dict[str, Any]:
    """
    Return a captured price chart, moved by whole days so that it holds the prices around `now`.

    Moving by whole days keeps the hours of the captured prices, as long as both days have the
    same UTC offset: the charts are from winter time, and so is the frozen test clock.
    """
    shift = now.astimezone(ZONNEPLAN_API_TIME_ZONE).date() - PRICE_CHART_DAY

    def move(value: Any, key: str = "") -> Any:
        if isinstance(value, dict):
            return {k: move(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [move(item) for item in value]
        if key in {"start_date", "end_date"}:
            return (datetime.fromisoformat(value) + shift).isoformat()
        return value

    return move(load_fixture(name)["data"])


def battery_chart(measured_at: datetime) -> list[dict[str, Any]]:
    """Build a battery chart. Synthetic: no real response was captured. Values are in the API's raw units."""
    return [
        {
            "measurements": [{"measured_at": measured_at.isoformat(), "value": 10000000, "meta": {"delivery": 1000, "production": 2000}}],
            "total": 10000000,
            "meta": {"delivery": 1000, "production": 2000},
        }
    ]


def mock_connection(aioclient_mock: AiohttpClientMocker, connection_uuid: str, connection: dict[str, Any], now: datetime) -> None:
    """Register every endpoint the coordinators of one connection call."""
    base = f"{API}/connections/{connection_uuid}"
    aioclient_mock.get(f"{base}/summary", json={"data": connection.get("summary_data") or {}})
    aioclient_mock.get(f"{base}/electricity-delivered", json={"data": connection.get("electricity_data") or {}})
    aioclient_mock.get(f"{base}/gas", json={"data": connection.get("gas_data") or {}})
    aioclient_mock.get(f"{base}/pv-installation", json={"data": connection.get("pv_data") or {}})
    aioclient_mock.get(f"{base}/electricity-home-consumption", json=load_fixture("home_usage.json"))
    # Statistics backfill: an empty day is valid and keeps these tests off the statistics code paths.
    aioclient_mock.get(re.compile(re.escape(base) + r"/.*/charts/hours\?"), json={"data": {"measurement_groups": []}})

    for contract in connection.get("charge_point_installation") or []:
        # The dump holds the coordinator's value, which is `contracts[0]` of the response.
        charge_point = connection.get("charge_point_data") or contract
        aioclient_mock.get(
            f"{base}/charge-points/{contract['uuid']}", json={"data": {"contracts": [charge_point], "vehicles": connection.get("vehicles") or []}}
        )

    for contract in connection.get("home_battery_installation") or []:
        uuid = contract["uuid"]
        aioclient_mock.get(f"{base}/home-battery-installation/{uuid}", json={"data": connection.get("battery_data") or {}})
        control_mode = connection.get("battery_control_mode") or load_fixture("battery_control_mode.json")["data"]
        optimization = connection.get("battery_home_optimization") or load_fixture("battery_home_optimization.json")["data"]
        aioclient_mock.get(f"{API}/api/contracts/{uuid}/home-battery/control-mode", json={"data": control_mode})
        aioclient_mock.get(f"{API}/api/contracts/{uuid}/home-battery/control-mode/home_optimization", json={"data": optimization})
        aioclient_mock.get(re.compile(rf"{API}/contracts/{uuid}/home_battery_installation/charts/"), json={"data": battery_chart(now)})


def mock_api(aioclient_mock: AiohttpClientMocker, connections: dict[str, dict[str, Any]], now: datetime, accounts: dict[str, Any] | None = None) -> None:
    """Register the account, price and per-connection endpoints."""
    charts = f"{API}/api/consumer-prices/charts"
    aioclient_mock.put(f"{API}/user-accounts/locale", status=204)
    aioclient_mock.post(re.compile(rf"{API}/connections/.*/actions/"), status=204)
    aioclient_mock.get(f"{API}/user-accounts/me", json={"data": accounts or accounts_from_connections(connections)})
    aioclient_mock.get(f"{charts}/electricity-hourly", json={"data": price_chart("prices_electricity_hourly.json", now)})
    aioclient_mock.get(f"{charts}/electricity-quarter-hourly", json={"data": price_chart("prices_electricity_quarter_hourly.json", now)})
    aioclient_mock.get(f"{charts}/gas-daily", json={"data": price_chart("prices_gas_daily.json", now)})

    for connection_uuid, connection in connections.items():
        mock_connection(aioclient_mock, connection_uuid, connection, now)


async def refresh_coordinators(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """
    Refresh every coordinator once more after setup.

    A coordinator's first refresh starts when its first entity subscribes. Mocked responses are
    instant, so it finishes before the other entities subscribe, and those would stay unknown.
    """
    for connection in entry.runtime_data.coordinators.values():
        for field in fields(connection):
            if coordinator := getattr(connection, field.name):
                await coordinator.async_refresh()
    await hass.async_block_till_done()


def entity_id_for(hass: HomeAssistant, platform: str, unique_id: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, unique_id)
    assert entity_id, f"no {platform} entity with unique id {unique_id}"
    return entity_id


def posted_actions(aioclient_mock: AiohttpClientMocker, connection_uuid: str = CONNECTION_UUID) -> list[tuple[str, Any]]:
    """Return the POST requests so far as (path below the connection, json body)."""
    prefix = f"{API}/connections/{connection_uuid}"
    return [(str(url).removeprefix(prefix), data) for method, url, data, _ in aioclient_mock.mock_calls if method.upper() == "POST"]
