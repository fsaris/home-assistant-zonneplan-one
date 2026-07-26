import logging
from datetime import timedelta
from http import HTTPStatus

import homeassistant.util.dt as dt_util
from aiohttp.client_exceptions import ClientResponseError
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.debounce import Debouncer

from ..api import AsyncConfigEntryAuth
from ..const import DOMAIN
from ..zonneplan_api.types import ZonneplanContract
from .zonneplan_data_update_coordinator import ZonneplanDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class EnergySupplyCostsDataUpdateCoordinator(ZonneplanDataUpdateCoordinator):
    """
    Zonneplan energy supply costs data update coordinator.

    Unlike the other coordinators this one is address scoped instead of connection
    scoped, and it asks for a single explicit day (today in the Zonneplan API time
    zone). These are the battery-filtered costs the app shows on its daily overview;
    the `/electricity-home-consumption` payload only carries them per month/year.
    """

    hass: HomeAssistant
    api: AsyncConfigEntryAuth
    contract: ZonneplanContract
    address_uuid: str
    organization_uuid: str

    def __init__(
        self,
        hass: HomeAssistant,
        api: AsyncConfigEntryAuth,
        address_uuid: str,
        connection_uuid: str,
        organization_uuid: str,
        contract: ZonneplanContract,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=300),
            request_refresh_debouncer=Debouncer(hass, _LOGGER, cooldown=60, immediate=False),
        )

        self.api: AsyncConfigEntryAuth = api
        self.address_uuid = address_uuid
        self.connection_uuid = connection_uuid
        self.organization_uuid = organization_uuid
        self.contract = contract
        self._zonneplan_api_time_zone = dt_util.get_time_zone("Europe/Amsterdam")

    async def _async_update_data(self) -> dict:
        """Fetch the latest status."""
        start_of_today = dt_util.now(self._zonneplan_api_time_zone).replace(hour=0, minute=0, second=0, microsecond=0)

        try:
            costs = await self.api.async_get_energy_supply_costs(
                self.organization_uuid,
                self.address_uuid,
                start_of_today.date(),
                start_of_today.date(),
            )

        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise
        else:
            _LOGGER.debug("Energy supply costs data: %s", costs)

            if not costs:
                return self.data

            # The response carries no date of its own, so stamp the day it covers to
            # give the daily cost sensors a last_reset.
            return {"date": start_of_today.isoformat(), **costs}
