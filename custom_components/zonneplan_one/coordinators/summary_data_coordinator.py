import logging
from datetime import UTC, datetime, timedelta
from http import HTTPStatus

import homeassistant.util.dt as dt_util
from aiohttp.client_exceptions import ClientResponseError
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.event import async_track_point_in_utc_time

from ..api import AsyncConfigEntryAuth
from ..const import DOMAIN
from ..zonneplan_api.types import ZonneplanContract
from .zonneplan_data_update_coordinator import ZonneplanDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def get_price_per_hour_by_date(prices: list[dict]) -> dict:
    price_by_hour = {}
    for price_info in prices:
        price_by_hour[price_info["datetime"].strftime("%Y-%m-%d %H")] = price_info
    return price_by_hour


def get_price_per_quarter_hour(data: dict) -> dict:
    price_by_quarter_hour = {}
    price_series = get_price_series_from_chart_data(data)
    for price_data in price_series:
        dt = dt_util.parse_datetime(price_data["start_date"])
        quarter_dt = dt.replace(minute=(dt.minute // 15) * 15, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")
        price_by_quarter_hour[quarter_dt] = price_data
    return price_by_quarter_hour


def get_energy_price(data: dict, dt: datetime | None = None) -> int | None:
    if dt is None:
        dt = datetime.now(UTC)
    price = None
    price_series = get_price_series_from_chart_data(data)
    for price_data in price_series:
        start_datetime = dt_util.parse_datetime(price_data["start_date"])
        end_datetime = dt_util.parse_datetime(price_data["end_date"])
        if start_datetime <= dt < end_datetime:
            price = price_data["price_tax_included"]["amount"]
            break
    return price


def get_price_series_from_chart_data(data: dict) -> list[dict]:
    return data.get("chart", {}).get("series", {}).get("prices", [])


def prepare_prices(data: dict) -> list[dict]:
    prices = []
    price_series = get_price_series_from_chart_data(data)
    for price_data in price_series:
        start_datetime = dt_util.parse_datetime(price_data["start_date"])
        price = price_data["price_tax_included"]["amount"]
        price_excl_tax = price_data["price_tax_excluded"]["amount"]

        price_info = {
            "datetime": start_datetime,
            "electricity_price": price,
            "electricity_price_excl_tax": price_excl_tax,
        }
        sustainability_score = price_data.get("sustainability_score", {}).get("permille", 0)
        tariff_group = price_data.get("tariff_group", "")
        price_info["sustainability_score"] = sustainability_score
        price_info["tariff_group"] = tariff_group

        prices.append(price_info)

    return prices


class SummaryDataUpdateCoordinator(ZonneplanDataUpdateCoordinator):
    """Zonneplan summary data update coordinator."""

    hass: HomeAssistant
    api: AsyncConfigEntryAuth
    contract: ZonneplanContract
    address_uuid: str

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
            update_interval=timedelta(minutes=15),
            request_refresh_debouncer=Debouncer(hass, _LOGGER, cooldown=60, immediate=False),
        )

        self.api: AsyncConfigEntryAuth = api
        self.address_uuid = address_uuid
        self.connection_uuid = connection_uuid
        self.contract = contract

        self._unsub_quarter_hour_update = None

    async def _async_update_data(self) -> dict:
        """Fetch the latest status."""
        try:
            summary = await self.api.async_get(self.connection_uuid, "/summary") or self.data
            hourly = await self.api.async_get_consumer_prices("electricity-hourly") or self.data.get("hourly")
            quarter_hourly = await self.api.async_get_consumer_prices("electricity-quarter-hourly") or self.data.get("quarter_hourly")
            gas_daily = await self.api.async_get_consumer_prices("gas-daily") or self.data.get("gas_daily")
            if hourly:
                summary["hourly"] = hourly
                legacy_hourly_electricity_prices = prepare_prices(hourly)
                summary["legacy_price_per_hour"] = legacy_hourly_electricity_prices
                summary["price_per_date_and_hour"] = get_price_per_hour_by_date(legacy_hourly_electricity_prices)
                summary["price_per_hour"] = get_price_series_from_chart_data(hourly)
            if quarter_hourly:
                summary["quarter_hourly"] = quarter_hourly
                summary["price_per_date_and_quarter_hour"] = get_price_per_quarter_hour(quarter_hourly)
                summary["price_per_quarter_hour"] = get_price_series_from_chart_data(quarter_hourly)
            if gas_daily:
                summary["gas_daily"] = gas_daily
                summary["gas_price"] = get_energy_price(gas_daily)
                summary["gas_price_next"] = get_energy_price(gas_daily, datetime.now(UTC) + timedelta(days=1))

            if not self._unsub_quarter_hour_update:
                self._schedule_quarter_hourly_listener_update()

        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise
        else:
            _LOGGER.debug("Summary data: %s", summary)

            return summary or self.data

    async def async_shutdown(self) -> None:
        """Cancel any scheduled call, and ignore new runs."""
        await super().async_shutdown()
        if self._unsub_quarter_hour_update:
            self._unsub_quarter_hour_update()
            self._unsub_quarter_hour_update = None

    def _schedule_quarter_hourly_listener_update(self) -> None:
        """Schedule quarter hourly sensor (listeners) update."""
        if self._unsub_quarter_hour_update:
            self._unsub_quarter_hour_update()

        now = dt_util.utcnow()
        next_hour = now.replace(minute=(now.minute // 15) * 15, second=0, microsecond=0) + timedelta(minutes=15)

        @callback
        def _handle(_: datetime) -> None:
            _LOGGER.debug("Next hour: refresh sensor data")

            self.async_update_listeners()
            self._schedule_quarter_hourly_listener_update()

        self._unsub_quarter_hour_update = async_track_point_in_utc_time(self.hass, _handle, next_hour)
