"""Zonneplan account DataUpdateCoordinator"""

from datetime import timedelta
from http import HTTPStatus

import logging
from aiohttp.client_exceptions import ClientResponseError

from homeassistant.core import (
    HomeAssistant
)
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from .zonneplan_data_update_coordinator import ZonneplanDataUpdateCoordinator
from ..api import AsyncConfigEntryAuth
from ..const import DOMAIN
from ..zonneplan_api.types import ZonneplanAccountsData

_LOGGER = logging.getLogger(__name__)


class AccountDataUpdateCoordinator(ZonneplanDataUpdateCoordinator):

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

    async def _async_update_data(self) -> dict:
        """Fetch the latest account status."""
        try:
            accounts = await self.api.async_get_user_accounts()
            if not accounts:
                raise UpdateFailed(retry_after=60)

            # todo: trigger integration reload on account changes
            return self.process_contracts(accounts)

        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise e

    def process_contracts(self, accounts: ZonneplanAccountsData) -> dict:
        contracts = {}
        for address_group in accounts.get("address_groups") or []:
            for connection in address_group.get("connections") or []:
                if len(connection["contracts"]) == 0:
                    continue

                if connection["uuid"] not in contracts:
                    contracts[connection["uuid"]] = {}

                for contract in connection["contracts"]:
                    if contract["type"] not in contracts[connection["uuid"]]:
                        contracts[connection["uuid"]][contract["type"]] = []
                    contracts[connection["uuid"]][contract["type"]].append(contract)

        _LOGGER.debug("Contracts: %s", contracts)

        return contracts
