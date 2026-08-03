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
from ..const import DOMAIN, ZONNEPLAN_API_TIME_ZONE
from ..zonneplan_api.types import ZonneplanContract
from .zonneplan_data_update_coordinator import ZonneplanDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def get_price_per_hour_by_date(prices: list[dict]) -> dict:
    price_by_hour = {}
    for price_info in prices:
        price_by_hour[price_info["start_date"].strftime("%Y-%m-%d %H")] = price_info
    return price_by_hour


def get_price_per_quarter_hour(price_series: list[dict]) -> dict:
    price_by_quarter_hour = {}
    for price_data in price_series:
        dt = price_data["start_date"]
        quarter_dt = dt.replace(minute=(dt.minute // 15) * 15, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M")
        price_by_quarter_hour[quarter_dt] = price_data
    return price_by_quarter_hour


def get_energy_price(data: dict, dt: datetime | None = None) -> int | None:
    if dt is None:
        dt = datetime.now(UTC)
    price = None
    price_series = get_price_series_from_chart_data(data)
    for price_data in price_series:
        start_datetime = price_data["start_date"]
        end_datetime = price_data["end_date"]
        if start_datetime <= dt < end_datetime:
            price = price_data["price_tax_included"]["amount"]
            break
    return price


def get_price_series_from_chart_data(data: dict) -> list[dict]:
    prices = data.get("chart", {}).get("series", {}).get("prices", [])
    date_fields = ["start_date", "end_date"]

    return [
        {
            **price_data,
            **{field: dt_util.parse_datetime(price_data[field]).astimezone(ZONNEPLAN_API_TIME_ZONE) for field in date_fields if price_data.get(field)},
        }
        for price_data in prices
    ]


def filter_and_sort_today(data: list[dict]) -> list[dict]:
    today = dt_util.now(ZONNEPLAN_API_TIME_ZONE).date()

    todays_items = [item for item in data if item["start_date"].date() == today]

    return sorted(todays_items, key=lambda item: item["price_tax_included"]["amount"])


def prepare_legacy_prices(price_series: list[dict]) -> list[dict]:
    prices = []
    for price_data in price_series:
        start_date = price_data["start_date"]
        price = price_data["price_tax_included"]["amount"]
        price_excl_tax = price_data["price_tax_excluded"]["amount"]

        price_info = {
            "start_date": start_date,
            "datetime": start_date.astimezone(UTC).isoformat(),
            "electricity_price": price,
            "electricity_price_excl_tax": price_excl_tax,
        }
        sustainability_score = price_data.get("sustainability_score", {}).get("permille", 0)
        tariff_group = price_data.get("tariff_group", "")
        price_info["sustainability_score"] = sustainability_score
        price_info["tariff_group"] = tariff_group

        prices.append(price_info)

    return prices


class ElectricityPricesDataUpdateCoordinator(ZonneplanDataUpdateCoordinator):
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
            price_data = self.data or {}

            hourly = await self.api.async_get_consumer_prices("electricity-hourly") or price_data.get("hourly")
            quarter_hourly = await self.api.async_get_consumer_prices("electricity-quarter-hourly") or price_data.get("quarter_hourly")

            if hourly:
                price_data["hourly"] = hourly
                price_series = get_price_series_from_chart_data(hourly)
                legacy_hourly_electricity_prices = prepare_legacy_prices(price_series)
                price_data["legacy_price_per_hour"] = legacy_hourly_electricity_prices
                price_data["price_per_date_and_hour"] = get_price_per_hour_by_date(legacy_hourly_electricity_prices)
                price_data["price_per_hour"] = price_series
                price_data["todays_prices_per_hour_ordered"] = filter_and_sort_today(price_series)
            if quarter_hourly:
                price_data["quarter_hourly"] = quarter_hourly
                price_series = get_price_series_from_chart_data(quarter_hourly)
                price_data["price_per_date_and_quarter_hour"] = get_price_per_quarter_hour(price_series)
                price_data["price_per_quarter_hour"] = price_series
                price_data["todays_prices_per_quarter_hour_ordered"] = filter_and_sort_today(price_series)

            if not self._unsub_quarter_hour_update:
                self._schedule_quarter_hourly_listener_update()

        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise
        else:
            _LOGGER.debug("Electricity price data: %s", price_data)

            return price_data

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
