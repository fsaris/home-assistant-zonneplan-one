import logging
from datetime import date, datetime, timedelta
from http import HTTPStatus
from typing import Any

import homeassistant.util.dt as dt_util
from aiohttp.client_exceptions import ClientResponseError
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.debounce import Debouncer

from zonneplan_one.api import AsyncConfigEntryAuth
from zonneplan_one.const import DOMAIN
from zonneplan_one.zonneplan_api.types import ZonneplanContract

from .zonneplan_data_update_coordinator import ZonneplanDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def _parse_day_chart(chart_data: Any, month_date: date) -> dict | None:
    group = chart_data[0]
    if not group:
        _LOGGER.warning("No day data in %s", chart_data)
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


def _parse_month_chart(chart_data: Any, year: int) -> dict | None:
    group = chart_data[0]
    if not group:
        _LOGGER.warning("No month data in %s", chart_data)
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


class BatteryChartsDataUpdateCoordinator(ZonneplanDataUpdateCoordinator):
    """Zonneplan battery history data update coordinator."""

    hass: HomeAssistant
    api: AsyncConfigEntryAuth
    address_uuid: str
    connection_uuid: str
    contract: ZonneplanContract

    def __init__(
        self,
        hass: HomeAssistant,
        api: AsyncConfigEntryAuth,
        address_uuid: str,
        connection_uuid: str,
        contract: ZonneplanContract,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=12),
            request_refresh_debouncer=Debouncer(hass, _LOGGER, cooldown=60, immediate=False),
        )

        self.data: dict = {}
        self.api: AsyncConfigEntryAuth = api
        self.address_uuid = address_uuid
        self.connection_uuid = connection_uuid
        self.contract = contract

        self._last_battery_chart_fetch: dict[str, datetime] = {}

    async def _async_update_data(self) -> dict:
        """Fetch the latest status."""
        try:
            charts = await self._async_get_battery_charts(self.data or {})

        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise
        else:
            _LOGGER.debug("Update battery charts data: %s", charts)

            return charts if charts else self.data

    async def _async_get_battery_charts(self, charts: dict) -> dict:
        today = dt_util.now().date()
        current_year_date = date(today.year, 1, 1)
        last_year_date = date(today.year - 1, 1, 1)
        current_month_date = today.replace(day=1)
        last_month_date = (current_month_date - timedelta(days=1)).replace(day=1)

        contract_uuid = self.contract.get("uuid")

        months_this_year = await self.api.async_get_battery_chart(contract_uuid, "months", current_year_date)
        if months_this_year and (parsed := _parse_month_chart(months_this_year, current_year_date.year)):
            charts["this_year"] = parsed

        months_last_year = await self.api.async_get_battery_chart(contract_uuid, "months", last_year_date)
        if months_last_year and (parsed := _parse_month_chart(months_last_year, last_year_date.year)):
            charts["last_year"] = parsed

        days_this_month = await self.api.async_get_battery_chart(contract_uuid, "days", current_month_date)
        if days_this_month and (parsed := _parse_day_chart(days_this_month, current_month_date)):
            charts["this_month"] = parsed

        days_last_month = await self.api.async_get_battery_chart(contract_uuid, "days", last_month_date)
        if days_last_month and (parsed := _parse_day_chart(days_last_month, last_month_date)):
            charts["last_month"] = parsed

        return charts
