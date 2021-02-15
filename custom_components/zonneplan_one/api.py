"""API for Zonneplan bound to Home Assistant OAuth."""
from typing import Any
from aiohttp import ClientSession

import logging

from homeassistant.helpers import config_entry_oauth2_flow
from .zonneplan_api.api import ZonneplanApi

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class AsyncConfigEntryAuth(ZonneplanApi):
    def __init__(
        self,
        websession: ClientSession,
        oauth_session: config_entry_oauth2_flow.OAuth2Session = None,
    ):
        """Initialize Zonneplan auth."""
        super().__init__(websession)
        self._oauth_session = oauth_session

    async def async_get_access_token(self) -> str:
        """Return a valid access token."""
        if not self._oauth_session.valid_token:
            await self._oauth_session.async_ensure_token_valid()

        return self._oauth_session.token["access_token"]

    async def async_get_user_accounts(self) -> dict:
        response = await self._oauth_session.async_request(
            "GET",
            "https://app-api.zonneplan.nl/user-accounts/me",
            # headers=self._request_headers,
        )

        _LOGGER.debug("ZonneplanAPI response header: %s", response.headers)
        _LOGGER.debug("ZonneplanAPI response status: %s", response.status)

        response.raise_for_status()

        response_json = await response.json()

        _LOGGER.debug("ZonneplanAPI response body  : %s", response_json)

        return response_json["data"]

    async def async_get_live_data(self, connection_uuid: str) -> dict:
        response = await self._oauth_session.async_request(
            "GET",
            "https://app-api.zonneplan.nl/connections/"
            + connection_uuid
            + "/pv_installation/charts/live",
            # headers=self._request_headers,
        )

        _LOGGER.debug("ZonneplanAPI response header: %s", response.headers)
        _LOGGER.debug("ZonneplanAPI response status: %s", response.status)

        response.raise_for_status()

        response_json = await response.json()

        _LOGGER.debug("ZonneplanAPI response body  : %s", response_json)

        return response_json["data"][0]


class ZonneplanOAuth2Implementation(
    config_entry_oauth2_flow.AbstractOAuth2Implementation
):
    def __init__(self, api: ZonneplanApi) -> None:
        self._api = api

    @property
    def name(self) -> str:
        """Name of the implementation."""
        return "Zonneplan"

    @property
    def domain(self) -> str:
        """Domain that is providing the implementation."""
        return DOMAIN

    async def async_request_temp_pass(self, email: str) -> str:
        return await self._api.async_request_temp_pass(email)

    async def async_resolve_external_data(self, external_data: Any) -> dict:
        """Resolve external data to tokens."""
        return await self._api.async_get_temp_pass(
            external_data["email"], external_data["uuid"]
        )

    async def _async_refresh_token(self, token: dict) -> dict:
        """Refresh a token."""
        return await self._api.async_refresh_token(token)

    async def async_generate_authorize_url(self, flow_id: str) -> str:
        """Generate a url for the user to authorize."""
        return ""