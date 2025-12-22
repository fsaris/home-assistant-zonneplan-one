"""API for Zonneplan bound to Home Assistant OAuth."""
from typing import Any
from datetime import date
from aiohttp import ClientSession

import logging

from .zonneplan_api.types import ZonneplanAccountsData
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

        self._etags = {}

    async def async_get_access_token(self) -> str:
        """Return a valid access token."""
        if not self._oauth_session.valid_token:
            await self._oauth_session.async_ensure_token_valid()

        return self._oauth_session.token["access_token"]

    async def async_get_user_accounts(self) -> ZonneplanAccountsData | None:
        return await self._async_get("user-accounts/me")

    async def async_get(self, connection_uuid: str, path: str) -> dict | None:
        return await self._async_get("connections/" + connection_uuid + path)

    async def async_get_battery_chart(
            self, contract_uuid: str, chart: str, chart_date: date
    ) -> dict | None:
        """Get battery chart data for the given contract and date."""
        chart_date_str = chart_date.isoformat()
        return await self._async_get(
            f"contracts/{contract_uuid}/home_battery_installation/charts/{chart}?date={chart_date_str}"
        )

    async def async_get_battery_control_mode(
            self, contract_uuid: str
    ) -> dict | None:
        """Get battery control mode"""
        return await self._async_get(
            f"api/contracts/{contract_uuid}/home-battery/control-mode"
        )

    async def async_get_battery_home_optimization(
            self, contract_uuid: str
    ) -> dict | None:
        """Get battery control mode"""
        return await self._async_get(
            f"api/contracts/{contract_uuid}/home-battery/control-mode/home_optimization"
        )

    async def _async_get(self, path: str) -> dict | None:
        _LOGGER.info("fetch: %s", path)

        headers = self._request_headers
        url = "https://app-api.zonneplan.nl/" + path

        if url in self._etags and self._etags[url]:
            headers["If-None-Match"] = self._etags[url]

        _LOGGER.debug("ZonneplanAPI request header: %s", headers)
        response = await self._oauth_session.async_request(
            "GET",
            url,
            headers=headers,
        )

        _LOGGER.debug("ZonneplanAPI response header: %s", response.headers)
        _LOGGER.debug("ZonneplanAPI response status: %s", response.status)

        if response.status == 304:
            return None

        response.raise_for_status()

        response_json = await response.json()

        _LOGGER.debug("ZonneplanAPI response body: %s", response_json)

        self._etags[url] = response.headers.get("ETag")

        return response_json["data"]

    async def async_post(self, connection_uuid: str, path: str, params=None) -> dict:
        if params is None:
            params = {}
        _LOGGER.info("POST: %s?%s", path, params)

        response = await self._oauth_session.async_request(
            "POST",
            "https://app-api.zonneplan.nl/connections/" + connection_uuid + path,
            json=params,
            headers=self._request_headers,
        )

        _LOGGER.debug("ZonneplanAPI response header: %s", response.headers)
        _LOGGER.debug("ZonneplanAPI response status: %s", response.status)

        response.raise_for_status()

        # 204 No Content successful response
        if response.status == 204:
            return {'ok': True}

        response_json = await response.json()

        _LOGGER.debug("ZonneplanAPI response body: %s", response_json)

        return response_json


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
        token = await self._api.async_get_temp_pass(
            external_data["email"], external_data["uuid"]
        )
        if not token:
            _LOGGER.error("Could not get token")
            raise Exception("Could not get token")

        return token

    async def _async_refresh_token(self, token: dict) -> dict:
        """Refresh a token."""
        new_token = await self._api.async_refresh_token(token)

        if not new_token:
            raise Exception("Could not get new token")

        return new_token

    async def async_generate_authorize_url(self, flow_id: str) -> str:
        """Generate a url for the user to authorize."""
        return ""
