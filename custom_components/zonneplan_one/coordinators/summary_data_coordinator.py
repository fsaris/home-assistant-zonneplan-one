from datetime import timedelta
from http import HTTPStatus

import logging
from aiohttp.client_exceptions import ClientResponseError

from homeassistant.core import (
    HomeAssistant
)
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from .zonneplan_data_update_coordinator import ZonneplanDataUpdateCoordinator
from ..api import AsyncConfigEntryAuth
from ..const import DOMAIN
from ..zonneplan_api.types import ZonneplanContract

_LOGGER = logging.getLogger(__name__)


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

class SummaryDataUpdateCoordinator(ZonneplanDataUpdateCoordinator):
    """Zonneplan summary data update coordinator"""

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
            request_refresh_debouncer=Debouncer(
                hass,
                _LOGGER,
                cooldown=60,
                immediate=False
            )
        )

        self.api: AsyncConfigEntryAuth = api
        self.address_uuid = address_uuid
        self.connection_uuid = connection_uuid
        self.contract = contract


    async def _async_update_data(self) -> dict:
        """Fetch the latest status."""
        try:

            summary = await self.api.async_get(self.connection_uuid, "/summary")
            if not summary:
                raise UpdateFailed(retry_after=60)

            summary["gas_price"] = get_gas_price_from_summary(summary)
            summary["gas_price_next"] = get_next_gas_price_from_summary(summary)

            _LOGGER.debug("Summary data: %s", summary)

            return summary

        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise e