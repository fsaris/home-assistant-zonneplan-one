"""ZonneplanAPI."""

import base64
import hashlib
import logging
import secrets
from http import HTTPStatus

import aiohttp

from ..const import VERSION

APP_VERSION = "5.10.1"
AUTHORIZE_CHALLENGE_URI = "https://app-api.zonneplan.nl/oauth/authorize-challenge"
OAUTH2_TOKEN_URI = "https://app-api.zonneplan.nl/oauth/token"  # noqa: S105

_LOGGER = logging.getLogger(__name__)


def _generate_pkce_pair() -> tuple[str, str]:
    """Generate a fresh (code_verifier, code_challenge) pair for one login attempt."""
    verifier = secrets.token_urlsafe(96)[:128]
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


class ZonneplanApi:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._request_headers = {
            "content-type": "application/json;charset=utf-8",
            "x-app-version": APP_VERSION,
            "x-app-environment": "production",
            "x-ha-integration": VERSION,
        }

    async def async_request_otp(self, email: str, source_name: str) -> tuple[str, str] | None:
        """Start the auth challenge (step 1). Returns (auth_session, code_verifier) or None."""
        code_verifier, code_challenge = _generate_pkce_pair()

        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with (
                aiohttp.ClientSession(timeout=timeout) as session,
                session.post(
                    AUTHORIZE_CHALLENGE_URI,
                    json={
                        "response_type": "code",
                        "email": email,
                        "code_challenge": code_challenge,
                        "code_challenge_method": "S256",
                        "source_name": source_name[:255],
                    },
                    headers=dict(self._request_headers),
                ) as response,
            ):
                # HTTP 403 with otp_required is the *expected* success path here,
                # so don't let raise_for_status() treat it as an error.
                if response.status != HTTPStatus.FORBIDDEN:
                    response.raise_for_status()

                _LOGGER.debug(
                    "ZonneplanAPI authorize-challenge status: %s (%s)",
                    response.status,
                    response,
                )
                response_json = await response.json()
                _LOGGER.debug("ZonneplanAPI authorize-challenge response body received")

        except TimeoutError:
            _LOGGER.exception("Timeout calling ZonneplanAPI to request OTP")
            return None

        except aiohttp.ClientResponseError as err:
            _LOGGER.exception(
                "HTTP error calling ZonneplanAPI to request OTP: %s %s",
                err.status,
                err.message,
            )
            return None

        except aiohttp.ClientError:
            _LOGGER.exception("Client error calling ZonneplanAPI to request OTP")
            return None

        if not response_json.get("otp_required") or "auth_session" not in response_json:
            _LOGGER.error("Unexpected ZonneplanAPI authorize-challenge response: %s", response_json)
            return None

        return response_json["auth_session"], code_verifier

    async def async_submit_otp(self, auth_session: str, otp: str, code_verifier: str) -> dict | None:
        """Submit the emailed OTP (step 2) and exchange the code for tokens (step 3)."""
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with (
                aiohttp.ClientSession(timeout=timeout) as session,
                session.post(
                    AUTHORIZE_CHALLENGE_URI,
                    json={"auth_session": auth_session, "otp": otp},
                    headers=dict(self._request_headers),
                ) as response,
            ):
                response.raise_for_status()
                _LOGGER.debug(
                    "ZonneplanAPI authorize-challenge (otp) status: %s (%s)",
                    response.status,
                    response,
                )
                response_json = await response.json()
                _LOGGER.debug("ZonneplanAPI authorize-challenge (otp) response body received")

        except TimeoutError:
            _LOGGER.exception("Timeout calling ZonneplanAPI to submit OTP")
            return None

        except aiohttp.ClientResponseError as err:
            _LOGGER.exception(
                "HTTP error calling ZonneplanAPI to submit OTP (likely wrong/expired code): %s %s",
                err.status,
                err.message,
            )
            return None

        except aiohttp.ClientError:
            _LOGGER.exception("Client error calling ZonneplanAPI to submit OTP")
            return None

        authorization_code = response_json.get("authorization_code")
        if not authorization_code:
            _LOGGER.error("Unexpected ZonneplanAPI authorize-challenge (otp) response: %s", response_json)
            return None

        grant_params = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "code_verifier": code_verifier,
        }
        return await self._async_request_new_token(grant_params)

    async def async_refresh_token(self, token: dict) -> dict:
        grant_params = {
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"],
        }
        return await self._async_request_new_token(grant_params)

    async def _async_request_new_token(self, grant_params: dict[str, str]) -> dict:
        _LOGGER.debug("Requesting new OAuth token using grant type %s", grant_params.get("grant_type"))

        timeout = aiohttp.ClientTimeout(total=30)
        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.post(
                OAUTH2_TOKEN_URI,
                headers=dict(self._request_headers),
                json=grant_params,
                allow_redirects=True,
            ) as response,
        ):
            _LOGGER.debug("ZonneplanAPI oAuth Token response header: %s", response.headers)
            _LOGGER.debug("ZonneplanAPI oAuth Token response status: %s", response.status)

            response.raise_for_status()
            _LOGGER.info("ZonneplanAPI oAuth Token get json from response")
            response_json = await response.json()
            _LOGGER.debug("ZonneplanAPI oAuth Token response body received")

        return response_json
