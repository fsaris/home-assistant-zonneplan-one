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
                data["gas_daily"] = gas_daily
                data["gas_price"] = get_energy_price(gas_daily)
                data["gas_price_next"] = get_energy_price(gas_daily, datetime.now(UTC) + timedelta(days=1))

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
