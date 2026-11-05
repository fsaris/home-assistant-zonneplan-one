"""Helpers for serving anonymized API responses to the integration."""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

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


def price_chart(start: datetime, *, step: timedelta, count: int) -> dict[str, Any]:
    """
    Build a consumer price chart with the price rising 100 per step.

    Synthetic: no real response was captured for this endpoint. The shape follows what
    `get_price_series_from_chart_data` and `prepare_legacy_prices` read.
    """
    return {
        "chart": {
            "series": {
                "prices": [
                    {
                        "start_date": (start + step * index).isoformat(),
                        "end_date": (start + step * (index + 1)).isoformat(),
                        "price_tax_included": {"amount": 2000000 + index * 100},
                        "price_tax_excluded": {"amount": 1000000 + index * 100},
                        "sustainability_score": {"permille": 300},
                        "tariff_group": "normal",
                    }
                    for index in range(count)
                ]
            }
        }
    }


def battery_chart(measured_at: datetime) -> list[dict[str, Any]]:
    """Build a battery chart. Synthetic, see `price_chart`; values are in the API's raw units."""
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
        aioclient_mock.get(f"{base}/charge-points/{contract['uuid']}", json={"data": {"contracts": [charge_point], "vehicles": []}})

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
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    charts = f"{API}/api/consumer-prices/charts"
    aioclient_mock.put(f"{API}/user-accounts/locale", status=204)
    aioclient_mock.get(f"{API}/user-accounts/me", json={"data": accounts or accounts_from_connections(connections)})
    aioclient_mock.get(f"{charts}/electricity-hourly", json={"data": price_chart(start_of_day, step=timedelta(hours=1), count=48)})
    aioclient_mock.get(f"{charts}/electricity-quarter-hourly", json={"data": price_chart(start_of_day, step=timedelta(minutes=15), count=192)})
    aioclient_mock.get(f"{charts}/gas-daily", json={"data": price_chart(start_of_day, step=timedelta(days=1), count=2)})

    for connection_uuid, connection in connections.items():
        mock_connection(aioclient_mock, connection_uuid, connection, now)
