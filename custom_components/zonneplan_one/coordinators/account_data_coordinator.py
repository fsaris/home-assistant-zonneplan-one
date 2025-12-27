"""Zonneplan account DataUpdateCoordinator"""

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
from ..zonneplan_api.types import ZonneplanAccountsData, ZonneplanAddressGroup

_LOGGER = logging.getLogger(__name__)


class AccountDataUpdateCoordinator(ZonneplanDataUpdateCoordinator):

    data: list[ZonneplanAddressGroup]|None

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
            request_refresh_debouncer=Debouncer(
                hass,
                _LOGGER,
                cooldown=60,
                immediate=False
            )
        )
        self.update_interval = timedelta(minutes=60)
        self.api: AsyncConfigEntryAuth = api

    async def _async_update_data(self) -> list[ZonneplanAddressGroup]:
        """Fetch the latest account status."""
        try:
            accounts = await self.api.async_get_user_accounts()
            if not accounts:
                raise UpdateFailed(retry_after=60)

            _LOGGER.debug("Accounts: %s", accounts)

            # todo: trigger integration reload on account changes
            return accounts.get("address_groups")

        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise e

    @property
    def address_groups(self) -> list[ZonneplanAddressGroup]:

        return self.data