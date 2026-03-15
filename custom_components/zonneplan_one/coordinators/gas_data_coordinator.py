import logging
from datetime import datetime, timedelta
from http import HTTPStatus

import homeassistant.util.dt as dt_util
from aiohttp.client_exceptions import ClientResponseError
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.debounce import Debouncer

from ..api import AsyncConfigEntryAuth
from ..const import DOMAIN
from ..zonneplan_api.types import ZonneplanContract
from .statistics import GasStatisticsService
from .zonneplan_data_update_coordinator import ZonneplanDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class GasDataUpdateCoordinator(ZonneplanDataUpdateCoordinator):
    """Zonneplan p1 gas data update coordinator."""

    hass: HomeAssistant
    api: AsyncConfigEntryAuth
    address_uuid: str
    connection_uuid: str
    contracts: list[ZonneplanContract]
    _statistics_service: GasStatisticsService

    def __init__(
        self,
        hass: HomeAssistant,
        api: AsyncConfigEntryAuth,
        address_uuid: str,
        connection_uuid: str,
        contracts: list[ZonneplanContract],
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
        self.contracts = contracts
        self._zonneplan_api_time_zone = dt_util.get_time_zone("Europe/Amsterdam")

        self._statistics_service = GasStatisticsService(
            hass=hass,
            api=self.api,
            connection_uuid=self.connection_uuid,
            gas_id=self.statistics_id,
            first_measured_at=self.first_measured_at,
        )

    async def _async_update_data(self) -> dict:
        """Fetch the latest status."""
        try:
            gas = await self.api.async_get(self.connection_uuid, "/gas")

        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise
        else:
            _LOGGER.debug("Update gas data: %s", gas)
            if gas:
                await self._statistics_service.process_payload(gas)

            return gas or self.data

    @property
    def statistics_id(self) -> str:
        return f"{DOMAIN}:gas_{self.connection_uuid.replace('-', '_')}"

    @property
    def first_measured_at(self) -> datetime | None:
        first_contract = self.contracts[0] if self.contracts else {}
        first_measured_at = (first_contract.get("meta") or {}).get("gas_first_measured_at")
        parsed = dt_util.parse_datetime(first_measured_at) if first_measured_at else None

        return parsed or None
