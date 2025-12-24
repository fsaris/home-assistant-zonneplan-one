"""Zonneplan DataUpdateCoordinator"""
from collections.abc import Callable
from datetime import date, datetime, timedelta
from http import HTTPStatus
from typing import Any

import logging
import homeassistant.util.dt as dt_util
import json
import inspect
import os
from aiohttp.client_exceptions import ClientResponseError

from homeassistant.core import (
    HassJob,
    HomeAssistant
)
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import AsyncConfigEntryAuth
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

BATTERY_CHART_UPDATE_INTERVAL = timedelta(hours=12)


def get_gas_price_from_summary(summary):
    if "price_per_hour" not in summary:
        return None

    for hour in summary["price_per_hour"]:
        if "gas_price" in hour:
            return hour["gas_price"]

    return None


def get_next_gas_price_from_summary(summary):
    if "price_per_hour" not in summary:
        return None

    first_price_found = False
    for hour in summary["price_per_hour"]:
        if "gas_price" in hour:
            if first_price_found:
                return hour["gas_price"]
            else:
                first_price_found = True

    return None


def _merge_battery_charts(
        existing_battery_data: dict | None, new_battery_data: dict | None
) -> None:
    """Carry over previously fetched charts when the API returns 304."""
    if not existing_battery_data or not new_battery_data:
        return

    existing_contracts = {
        contract.get("uuid"): contract
        for contract in existing_battery_data.get("contracts", [])
        if contract.get("uuid")
    }

    for contract in new_battery_data.get("contracts", []):
        contract_uuid = contract.get("uuid")
        if not contract_uuid or contract.get("charts"):
            continue

        previous_contract = existing_contracts.get(contract_uuid)
        if previous_contract and previous_contract.get("charts"):
            contract["charts"] = previous_contract["charts"]


def _get_battery_contract(
        battery_data: dict | None, contract_uuid: str
) -> dict | None:
    if not battery_data:
        return None

    for contract in battery_data.get("contracts", []):
        if contract.get("uuid") == contract_uuid:
            return contract
    return None


def _get_chart_group(chart_data: Any) -> dict | None:
    if not chart_data:
        return None

    if isinstance(chart_data, dict):
        data = chart_data.get("data")
        if isinstance(data, list) and data:
            return data[0]
        return None

    if isinstance(chart_data, list) and chart_data:
        return chart_data[0]

    return None


class ZonneplanUpdateCoordinator(DataUpdateCoordinator):
    """Zonneplan status update coordinator"""

    def __init__(
            self,
            hass: HomeAssistant,
            api: AsyncConfigEntryAuth,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=300),
            request_refresh_debouncer=Debouncer(
                hass,
                _LOGGER,
                cooldown=60,
                immediate=False
            )
        )
        self.last_accounts_update: datetime | None = None
        self.data: dict = {}
        self.api: AsyncConfigEntryAuth = api
        self._delayed_fetch_charge_point: Callable[[], None] | None = None

        self._test_file = None
        self._last_battery_chart_fetch: dict[str, datetime] = {}

    async def _async_update_data(self) -> dict:
        """Fetch the latest status."""
        try:
            return await self._fetch_data()
        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise e

    async def _fetch_data(self) -> dict:

        if self._test_file:
            script_directory = os.path.dirname(os.path.abspath(
                inspect.getfile(inspect.currentframe())))
            f = open(script_directory + '/tests/' + self._test_file)
            result = json.load(f)

            _LOGGER.debug("TEST Result %s", result)

            return result

        result = self.data
        accounts = None

        _LOGGER.info("_async_update_data: start")
        # Get all info of all connections (part of your account info)
        if not result or not self.last_accounts_update or self.last_accounts_update < dt_util.now() - timedelta(minutes=59):
            accounts = await self.api.async_get_user_accounts()
            if not accounts and not result:
                return result
        else:
            _LOGGER.debug("Last time accounts are fetched: %s, next time to fetch: %s", self.last_accounts_update,
                          self.last_accounts_update + timedelta(minutes=59))

        if accounts:
            self.last_accounts_update = dt_util.now()
            _LOGGER.info("_async_update_data: parse addresses")
            # Flatten all found connections
            for address_group in accounts.get("address_groups") or []:
                for connection in address_group.get("connections") or []:
                    if connection["uuid"] not in result:
                        result[connection["uuid"]] = {
                            "uuid": connection["uuid"],
                            "pv_data": {},
                            "electricity_data": {},
                            "gas_data": {},
                            "summary_data": {},
                            "charge_point_data": {},
                            "battery_data": {},
                        }

                    # Remove known contracts
                    if "pv_installation" in result[connection["uuid"]]:
                        del result[connection["uuid"]]["pv_installation"]
                    if "p1_installation" in result[connection["uuid"]]:
                        del result[connection["uuid"]]["p1_installation"]
                    if "charge_point_installation" in result[connection["uuid"]]:
                        del result[connection["uuid"]]["charge_point_installation"]
                    if "home_battery_installation" in result[connection["uuid"]]:
                        del result[connection["uuid"]]["home_battery_installation"]

                    for contract in connection["contracts"]:
                        if contract["type"] not in result[connection["uuid"]]:
                            result[connection["uuid"]][contract["type"]] = []
                        result[connection["uuid"]][contract["type"]].append(contract)

        _LOGGER.info("_async_update_data: fetch live data")

        # Update last live data for each connection
        summary_retrieved = False
        for uuid, connection in result.items():

            if "pv_installation" in connection:
                pv_data = await self.api.async_get(
                    uuid, "/pv-installation"
                )
                if pv_data:
                    result[uuid]["pv_data"] = pv_data

            if "p1_installation" in connection:
                electricity = await self.api.async_get(uuid, "/electricity-delivered")
                if electricity:
                    result[uuid]["electricity_data"] = electricity
                gas = await self.api.async_get(uuid, "/gas")
                if gas:
                    result[uuid]["gas_data"] = gas

            # Electricity summary also contains gas data - only need to retrieve summary once
            # Prevent duplicate sensors being setup if there is also an electricity contract
            if (
                    "electricity" in connection or "gas" in connection
            ) and not summary_retrieved:
                summary_retrieved = True
                summary = await self.api.async_get(uuid, "/summary")
                if summary:
                    result[uuid]["summary_data"] = summary
                    result[uuid]["summary_data"]["gas_price"] = get_gas_price_from_summary(summary)
                    result[uuid]["summary_data"]["gas_price_next"] = get_next_gas_price_from_summary(summary)

            if "charge_point_installation" in connection:
                charge_point = await self._async_get_charge_point_data(uuid, connection["charge_point_installation"][0]["uuid"])
                if charge_point:
                    result[uuid]["charge_point_data"] = charge_point["contracts"][0]

            if "home_battery_installation" in connection:
                existing_battery_data = connection.get("battery_data")
                battery_data = await self.api.async_get(uuid, "/home-battery-installation/" + connection["home_battery_installation"][0]["uuid"])
                if battery_data:
                    _merge_battery_charts(existing_battery_data, battery_data)
                    result[uuid]["battery_data"] = battery_data
                await self._async_enrich_battery_charts(
                    result[uuid].get("battery_data"),
                    existing_battery_data,
                )
                battery_control_mode = await self.api.async_get_battery_control_mode(connection["home_battery_installation"][0]["uuid"])
                if battery_control_mode:
                    result[uuid]["battery_control_mode"] = battery_control_mode

                battery_home_optimization = await self.api.async_get_battery_home_optimization(connection["home_battery_installation"][0]["uuid"])
                if battery_home_optimization:
                    result[uuid]["battery_home_optimization"] = battery_home_optimization

                electricity_home_consumption = await self.api.async_get(uuid, "/electricity-home-consumption")
                if electricity_home_consumption:
                    result[uuid]["electricity_home_consumption"] = electricity_home_consumption
                    # result[uuid]["electricity_home_consumption"]["today"] = electricity_home_consumption["measurement_groups"][2]["measurements"][-1]
                    

        _LOGGER.info("_async_update_data: done")
        _LOGGER.debug("Result %s", result)

        return result

    async def _async_enrich_battery_charts(
            self, battery_data: dict | None, existing_battery_data: dict | None = None
    ) -> None:
        """Fetch and attach chart data for battery contracts."""
        if not battery_data or not battery_data.get("contracts"):
            return

        today = dt_util.now().date()
        current_year_date = date(today.year, 1, 1)
        last_year_date = date(today.year - 1, 1, 1)
        current_month_date = today.replace(day=1)
        last_month_date = (current_month_date - timedelta(days=1)).replace(day=1)

        for contract in battery_data.get("contracts", []):
            contract_uuid = contract.get("uuid")
            if not contract_uuid:
                continue

            existing_charts = (
                    contract.get("charts")
                    or self._get_existing_battery_charts(existing_battery_data, contract_uuid)
                    or {}
            )
            charts = dict(existing_charts)

            if not self._should_refresh_battery_charts(contract_uuid):
                if existing_charts:
                    contract["charts"] = existing_charts
                continue

            fetched = False

            months_this_year = await self.api.async_get_battery_chart(
                contract_uuid, "months", current_year_date
            )
            if months_this_year and (
                    parsed := self._parse_month_chart(months_this_year, current_year_date.year)
            ):
                charts["this_year"] = parsed
                fetched = True

            months_last_year = await self.api.async_get_battery_chart(
                contract_uuid, "months", last_year_date
            )
            if months_last_year and (
                    parsed := self._parse_month_chart(months_last_year, last_year_date.year)
            ):
                charts["last_year"] = parsed
                fetched = True

            days_this_month = await self.api.async_get_battery_chart(
                contract_uuid, "days", current_month_date
            )
            if days_this_month and (
                    parsed := self._parse_day_chart(days_this_month, current_month_date)
            ):
                charts["this_month"] = parsed
                fetched = True

            days_last_month = await self.api.async_get_battery_chart(
                contract_uuid, "days", last_month_date
            )
            if days_last_month and (
                    parsed := self._parse_day_chart(days_last_month, last_month_date)
            ):
                charts["last_month"] = parsed
                fetched = True

            if charts:
                contract["charts"] = charts
            self._last_battery_chart_fetch[contract_uuid] = dt_util.now()

            if not fetched and existing_charts:
                contract["charts"] = existing_charts

    def _get_existing_battery_charts(
            self, battery_data: dict | None, contract_uuid: str
    ) -> dict | None:
        contract = _get_battery_contract(battery_data, contract_uuid)
        if contract:
            return contract.get("charts")
        return None

    def _should_refresh_battery_charts(self, contract_uuid: str) -> bool:
        """Throttle chart refreshes to a few times per day."""
        last_fetch = self._last_battery_chart_fetch.get(contract_uuid)
        if not last_fetch:
            return True

        return last_fetch < dt_util.now() - BATTERY_CHART_UPDATE_INTERVAL

    def _parse_month_chart(self, chart_data: Any, year: int) -> dict | None:
        group = _get_chart_group(chart_data)
        if not group:
            return None

        measurements = group.get("measurements") or []
        meta = group.get("meta") or {}

        months: dict[str, Any] = {}
        tz_ams = dt_util.get_time_zone("Europe/Amsterdam")
        for measurement in measurements:
            measured_at = measurement.get("measured_at")
            dt_value = dt_util.parse_datetime(measured_at) if measured_at else None
            if not dt_value:
                continue

            dt_value = dt_util.as_utc(dt_value).astimezone(tz_ams)

            month_key = dt_value.date().strftime("%Y-%m")
            months[month_key] = {
                "result": (measurement.get("value") or 0) * 0.0000001,
                "delivery_kwh": (measurement.get("meta", {}).get("delivery") or 0) * 0.001,
                "production_kwh": (measurement.get("meta", {}).get("production") or 0) * 0.001,
            }

        return {
            "year": year,
            "total_result": (group.get("total") or 0) * 0.0000001,
            "total_delivery_kwh": (meta.get("delivery") or 0) * 0.001,
            "total_production_kwh": (meta.get("production") or 0) * 0.001,
            "months": months,
        }

    def _parse_day_chart(self, chart_data: Any, month_date: date) -> dict | None:
        group = _get_chart_group(chart_data)
        if not group:
            return None

        measurements = group.get("measurements") or []
        meta = group.get("meta") or {}

        days: dict[str, Any] = {}
        tz_ams = dt_util.get_time_zone("Europe/Amsterdam")
        for measurement in measurements:
            measured_at = measurement.get("measured_at")
            dt_value = dt_util.parse_datetime(measured_at) if measured_at else None
            if not dt_value:
                continue

            dt_value = dt_util.as_utc(dt_value).astimezone(tz_ams)

            day_key = dt_value.date().isoformat()
            days[day_key] = {
                "result": (measurement.get("value") or 0) * 0.0000001,
                "delivery_kwh": (measurement.get("meta", {}).get("delivery") or 0) * 0.001,
                "production_kwh": (measurement.get("meta", {}).get("production") or 0) * 0.001,
            }

        return {
            "month": month_date.strftime("%Y-%m"),
            "total_result": (group.get("total") or 0) * 0.0000001,
            "total_delivery_kwh": (meta.get("delivery") or 0) * 0.001,
            "total_production_kwh": (meta.get("production") or 0) * 0.001,
            "days": days,
        }

    @property
    def connections(self) -> dict:
        return self.data

    def get_connection_value(self, connection_uuid: str, value_path: str):
        if connection_uuid not in self.data:
            return None

        keys = value_path.split(".")
        rv = self.data[connection_uuid]
        for key in keys:
            if rv is None:
                _LOGGER.info("No value for %s part (%s)", value_path, key)
                return None

            if key.lstrip('-').isdigit():
                key = int(key)
                if not type(rv) is list or (key >=0 and len(rv) <= key) or (key < 0 and -len(rv) > key):
                    _LOGGER.info(
                        "Could not find %d of %s",
                        key,
                        value_path,
                    )
                    _LOGGER.debug(" in %s %s", rv, type(rv))
                    return None

            elif key not in rv:
                _LOGGER.info("Could not find %s of %s", key, value_path)
                _LOGGER.debug("in %s", rv)
                return None
            rv = rv[key]

        return rv

    def set_connection_value(self, connection_uuid: str, value_path: str, value: str | int):
        if connection_uuid not in self.data:
            return

        keys = value_path.split(".")
        rv = self.data[connection_uuid]
        for key in keys[:-1]:
            if rv is None:
                return

            if key.lstrip('-').isdigit():
                key = int(key)
                if not type(rv) is list or (key >= 0 and len(rv) <= key) or (key < 0 and -len(rv) > key):
                    return

            elif key not in rv:
                return

            rv = rv[key]

        last_key = keys[-1]
        if last_key.isdigit():
            last_key = int(last_key)
            if type(rv) is list and len(rv) > last_key:
                rv[last_key] = value
        else:
            rv[last_key] = value

    async def _async_get_charge_point_data(self, connection_uuid: str, charge_point_uuid: str) -> dict:
        return await self.api.async_get(connection_uuid, "/charge-points/" + charge_point_uuid)

    async def async_update_charge_point_data(self, connection_uuid: str, charge_point_uuid: str) -> None:
        charge_point = await self._async_get_charge_point_data(connection_uuid, charge_point_uuid)
        if charge_point:
            self.data[connection_uuid]["charge_point_data"] = charge_point["contracts"][0]
            self.async_update_listeners()

    async def async_start_charge(
            self, connection_uuid: str, charge_point_uuid: str
    ) -> None:
        await self.api.async_post(
            connection_uuid,
            "/charge-points/" + charge_point_uuid + "/actions/start_boost",
        )

        self.data[connection_uuid]["charge_point_data"]["state"]["processing"] = True
        self.async_update_listeners()

        await self.async_fetch_charge_point_data()

    async def async_stop_charge(
            self, connection_uuid: str, charge_point_uuid: str
    ) -> None:
        await self.api.async_post(
            connection_uuid,
            "/charge-points/" + charge_point_uuid + "/actions/stop_charging",
        )

        self.data[connection_uuid]["charge_point_data"]["state"]["processing"] = True

        self.async_update_listeners()

        await self.async_fetch_charge_point_data()

    async def async_enable_self_consumption(
            self, connection_uuid: str, install_index: int, battery_uuid: str
    ) -> None:
        await self.api.async_post(
            connection_uuid,
            "/home-battery-installation/" + battery_uuid + "/actions/enable_self_consumption",
        )

        if self.get_connection_value(connection_uuid, "battery_control_mode.modes.home_optimization.enabled"):
            await self.api.async_post(
                connection_uuid,
                "/home-battery-installation/" + battery_uuid + "/actions/disable_home_optimization",
            )

        self.data[connection_uuid]["battery_control_mode"]["processing"] = True

        self.async_update_listeners()

        await self.async_fetch_battery_control_mode(connection_uuid, battery_uuid)

    async def async_enable_dynamic_charging(
            self, connection_uuid: str, install_index: int, battery_uuid: str
    ) -> None:

        if self.get_connection_value(connection_uuid, "battery_control_mode.modes.home_optimization.enabled"):
            await self.api.async_post(
                connection_uuid,
                "/home-battery-installation/" + battery_uuid + "/actions/disable_home_optimization",
            )
        if self.get_connection_value(connection_uuid, "battery_control_mode.modes.self_consumption.enabled"):
            await self.api.async_post(
                connection_uuid,
                "/home-battery-installation/" + battery_uuid + "/actions/disable_self_consumption",
            )

        self.data[connection_uuid]["battery_control_mode"]["processing"] = True

        self.async_update_listeners()

        await self.async_fetch_battery_control_mode(connection_uuid, battery_uuid)

    async def async_enable_home_optimization(
            self, connection_uuid: str, install_index: int, battery_uuid: str
    ) -> None:
        charge_power = self.get_connection_value(
            connection_uuid, "battery_home_optimization.max_desired_charge_power_watts"
        )
        discharge_power = self.get_connection_value(
            connection_uuid,
            "battery_home_optimization.max_desired_discharge_power_watts",
        )

        if (charge_power is None) ^ (discharge_power is None):
            _LOGGER.info(
                "skipped async_enable_home_optimization as only 1 param is set (need both or none): charge=%s, discharge=%s",
                charge_power,
                discharge_power,
            )
            return

        params = {}
        if charge_power is not None:
            params = {
                "max_desired_charge_power_w": charge_power,
                "max_desired_discharge_power_w": discharge_power,
            }

        _LOGGER.info("async_enable_home_optimization: params %s", params)
        response = await self.api.async_post(
            connection_uuid,
            f"/home-battery-installation/{battery_uuid}/actions/enable_home_optimization",
            params
        )

        _LOGGER.debug("enable_home_optimization response: %s", response)

        if "max_desired_discharge_power_w" in response:
            self.data[connection_uuid]["battery_home_optimization"]["max_desired_discharge_power_watts"] = response["max_desired_discharge_power_w"]
        if "max_desired_charge_power_w" in response:
            self.data[connection_uuid]["battery_home_optimization"]["max_desired_charge_power_watts"] = response["max_desired_charge_power_w"]

        if self.get_connection_value(connection_uuid, "battery_control_mode.modes.self_consumption.enabled"):
            await self.api.async_post(
                connection_uuid,
                f"/home-battery-installation/{battery_uuid}/actions/disable_self_consumption",
            )

        self.data[connection_uuid]["battery_control_mode"]["processing"] = True

        await self.async_fetch_battery_control_mode(connection_uuid, battery_uuid)

    def _processing_charge_point_update(self) -> bool:
        for connection_uuid, connection in self.connections.items():
            processing = self.get_connection_value(connection_uuid, "charge_point_data.state.processing")
            if processing:
                return True

        return False

    async def async_fetch_charge_point_data(self, _now: Any = None):

        if self._delayed_fetch_charge_point:
            self._delayed_fetch_charge_point()
        self._delayed_fetch_charge_point = None

        for connection_uuid, connection in self.connections.items():
            processing = self.get_connection_value(connection_uuid, "charge_point_data.state.processing")
            charge_point_uuid = self.get_connection_value(connection_uuid, "charge_point_data.uuid")
            if processing and charge_point_uuid:
                await self.async_update_charge_point_data(connection_uuid, charge_point_uuid)

        if self._processing_charge_point_update():
            self._delayed_fetch_charge_point = async_call_later(
                self.hass,
                10,
                HassJob(self.async_fetch_charge_point_data, cancel_on_shutdown=True),
            )

    async def async_fetch_battery_control_mode(self, connection_uuid: str, battery_uuid: str):

        battery_control_mode = await self.api.async_get_battery_control_mode(battery_uuid)
        if battery_control_mode:
            self.data[connection_uuid]["battery_control_mode"] = battery_control_mode
            _LOGGER.info("battery_control_mode %s", battery_control_mode)
        else:
            self.data[connection_uuid]["battery_control_mode"]["processing"] = False

        battery_home_optimization = await self.api.async_get_battery_home_optimization(battery_uuid)
        if battery_home_optimization:
            self.data[connection_uuid]["battery_home_optimization"] = battery_home_optimization

        self.async_update_listeners()
