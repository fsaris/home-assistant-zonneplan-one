"""ZonneplanAPI"""
import asyncio
import aiohttp
import async_timeout
import logging

from ..const import VERSION

APP_VERSION = "4.12.1"
API_VERSION = "v2"
LOGIN_REQUEST_URI = "https://app-api.zonneplan.nl/auth/request"
OAUTH2_TOKEN_URI = "https://app-api.zonneplan.nl/oauth/token"

_LOGGER = logging.getLogger(__name__)


class ZonneplanApi:
    def __init__(self, session: aiohttp.ClientSession):
        self._session = session
        self._request_headers = {
            "content-type": "application/json;charset=utf-8",
            "x-app-version": APP_VERSION,
            "x-api-version": API_VERSION,
            "x-app-environment": "production",
            "x-ha-integration": VERSION,
        }

    async def async_request_temp_pass(self, email: str) -> str:
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with await session.post(
                    LOGIN_REQUEST_URI,
                    json={"email": email},
                    headers=self._request_headers,
                ) as response:

                    response.raise_for_status()
                    _LOGGER.debug("ZonneplanAPI validated status: %s (%s)", response.status, response)

                    # Get Json
                    response_json = await response.json()
                    _LOGGER.debug("ZonneplanAPI response body: %s", response_json)

        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Timeout calling ZonneplanAPI to request login email")
            return None

        _LOGGER.debug("ZonneplanAPI response header: %s", response.headers)
        _LOGGER.debug("ZonneplanAPI response status: %s", response.status)

        return response_json["data"]["uuid"]

    async def async_get_temp_pass(self, email: str, uuid: str):
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    LOGIN_REQUEST_URI + "/" + uuid, headers=self._request_headers
                ) as response:

                    response.raise_for_status()
                    _LOGGER.debug("Temporary password validated status: %s (%s)", response.status, response)

                    response_json = await response.json()
                    _LOGGER.debug("Temporary password response body json: %s", response_json)

        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Timeout calling ZonneplanAPI to request temporary password")
            return None

        _LOGGER.debug("Temporary password response header: %s", response.headers)
        _LOGGER.debug("Temporary password response status: %s", response.status)

        if (
            "data" in response_json
            and "is_activated" in response_json["data"]
            and response_json["data"]["is_activated"]
            and "password" in response_json["data"]
        ):
            grant_params = {
                "grant_type": "one_time_password",
                "email": email,
                "password": response_json["data"]["password"],
            }
            return await self._async_request_new_token(grant_params)

        return None

    async def async_refresh_token(self, token: dict) -> dict:
        grant_params = {
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"],
        }
        return await self._async_request_new_token(grant_params)

    async def _async_request_new_token(self, grant_params):
        _LOGGER.info("_async_request_new_token: %s", grant_params)

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                OAUTH2_TOKEN_URI,
                headers=self._request_headers,
                json=grant_params,
                allow_redirects=True,
            ) as response:

                _LOGGER.debug("ZonneplanAPI oAuth Token response header: %s", response.headers)
                _LOGGER.debug("ZonneplanAPI oAuth Token response status: %s", response.status)

                response.raise_for_status()
                _LOGGER.info("ZonneplanAPI oAuth Token get json from response")
                response_json = await response.json()
                _LOGGER.debug("ZonneplanAPI oAuth Token response body: %s", response_json)

        return response_json
