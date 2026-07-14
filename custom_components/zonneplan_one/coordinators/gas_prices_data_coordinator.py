import logging
from datetime import datetime, timedelta
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


def get_prices_by_date_and_hour(prices: dict) -> dict:
    zonneplan_api_time_zone = dt_util.get_time_zone("Europe/Amsterdam")

    price_by_hour = {}
    for price_data in get_price_series_from_chart_data(prices):
        start_datetime = dt_util.parse_datetime(price_data["start_date"]).astimezone(zonneplan_api_time_zone)
        if start_datetime:
            price_by_hour[start_datetime.strftime("%Y-%m-%d %H")] = price_data
    return price_by_hour


def get_price_series_from_chart_data(data: dict) -> list[dict]:
    return data.get("chart", {}).get("series", {}).get("prices", [])


class GasPricesDataUpdateCoordinator(ZonneplanDataUpdateCoordinator):
    """Zonneplan gas prices data update coordinator."""

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
            update_interval=timedelta(minutes=60),
            request_refresh_debouncer=Debouncer(hass, _LOGGER, cooldown=60, immediate=False),
        )

        self.api: AsyncConfigEntryAuth = api
        self.address_uuid = address_uuid
        self.connection_uuid = connection_uuid
        self.contract = contract

        self._unsub_hour_update = None

    async def _async_update_data(self) -> dict:
        """Fetch the latest status."""
        try:
            data = {}
            gas_daily = await self.api.async_get_consumer_prices("gas-daily")
            if gas_daily:
                data["gas_prices"] = get_prices_by_date_and_hour(gas_daily)
                data["forecast"] = get_price_series_from_chart_data(gas_daily)

                if not self._unsub_hour_update:
                    self._schedule_hourly_listener_update()

        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise
        else:
            _LOGGER.debug("Gas prices data: %s", data)

            return data

    async def async_shutdown(self) -> None:
        """Cancel any scheduled call, and ignore new runs."""
        await super().async_shutdown()
        if self._unsub_hour_update:
            self._unsub_hour_update()
            self._unsub_hour_update = None

    def _schedule_hourly_listener_update(self) -> None:
        """Schedule hourly sensor (listeners) update."""
        if self._unsub_hour_update:
            self._unsub_hour_update()

        now = dt_util.utcnow()
        next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        @callback
        def _handle(_: datetime) -> None:
            _LOGGER.debug("Next hour: refresh sensor data")

            self.async_update_listeners()
            self._schedule_hourly_listener_update()

        self._unsub_hour_update = async_track_point_in_utc_time(self.hass, _handle, next_hour)
