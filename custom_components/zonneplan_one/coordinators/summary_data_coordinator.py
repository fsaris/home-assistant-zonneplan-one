import logging
from datetime import datetime, timedelta
from http import HTTPStatus

import homeassistant.util.dt as dt_util
from aiohttp.client_exceptions import ClientResponseError
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.event import async_track_point_in_utc_time

from zonneplan_one.api import AsyncConfigEntryAuth
from zonneplan_one.const import DOMAIN
from zonneplan_one.zonneplan_api.types import ZonneplanContract

from .zonneplan_data_update_coordinator import ZonneplanDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


def get_price_per_hour_by_date(summary: dict) -> dict:
    prices = {}
    if "price_per_hour" not in summary:
        return prices

    for hour in summary["price_per_hour"]:
        date = dt_util.parse_datetime(hour["datetime"])
        if date:
            prices[date.strftime("%Y-%m-%d %H")] = hour

    return prices


def get_gas_price_from_summary(summary: dict) -> str | None:
    if "price_per_hour" not in summary:
        return None

    for hour in summary["price_per_hour"]:
        if "gas_price" in hour:
            return hour["gas_price"]

    return None


def get_next_gas_price_from_summary(summary: dict) -> str | None:
    if "price_per_hour" not in summary:
        return None

    first_price_found = False
    for hour in summary["price_per_hour"]:
        if "gas_price" in hour:
            if first_price_found:
                return hour["gas_price"]
            first_price_found = True

    return None


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

        self._unsub_hour_update = None

    async def _async_update_data(self) -> dict:
        """Fetch the latest status."""
        try:
            summary = await self.api.async_get(self.connection_uuid, "/summary")
            if summary:
                summary["gas_price"] = get_gas_price_from_summary(summary)
                summary["gas_price_next"] = get_next_gas_price_from_summary(summary)
                summary["price_per_date_and_hour"] = get_price_per_hour_by_date(summary)

                if not self._unsub_hour_update:
                    self._schedule_hourly_listener_update()

        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise
        else:
            _LOGGER.debug("Summary data: %s", summary)

            return summary if summary else self.data

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
