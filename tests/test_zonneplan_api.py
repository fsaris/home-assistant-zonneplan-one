"""Tests for the login requests, which use their own aiohttp session instead of Home Assistant's."""

import base64
import hashlib
from typing import Any, Self
from unittest.mock import MagicMock, patch

import aiohttp
import pytest

from custom_components.zonneplan_one.zonneplan_api.api import AUTHORIZE_CHALLENGE_URI, OAUTH2_TOKEN_URI, ZonneplanApi

CLIENT_SESSION = "custom_components.zonneplan_one.zonneplan_api.api.aiohttp.ClientSession"


class FakeResponse:
    def __init__(self, status: int = 200, body: Any = None) -> None:
        self.status = status
        self.headers = {}
        self._body = body

    async def json(self) -> Any:
        return self._body

    def raise_for_status(self) -> None:
        if self.status >= 400:  # noqa: PLR2004
            raise aiohttp.ClientResponseError(MagicMock(), (), status=self.status, message="error")

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None


class FakeSession:
    """Answer POST requests in order; an exception in the list is raised instead."""

    def __init__(self, *responses: FakeResponse | Exception) -> None:
        self.responses = list(responses)
        self.requests: list[tuple[str, dict[str, Any]]] = []

    def __call__(self, **_: object) -> "FakeSession":
        return self

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.requests.append((url, kwargs["json"]))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _api() -> ZonneplanApi:
    return ZonneplanApi(MagicMock())


CHALLENGE = FakeResponse(403, {"otp_required": True, "auth_session": "auth-session"})


async def test_request_otp_treats_403_as_success_and_sends_a_matching_challenge() -> None:
    session = FakeSession(CHALLENGE)

    with patch(CLIENT_SESSION, session):
        auth_session, verifier = await _api().async_request_otp("user@example.com", "Home Assistant")

    url, body = session.requests[0]
    assert url == AUTHORIZE_CHALLENGE_URI
    assert auth_session == "auth-session"
    assert body["email"] == "user@example.com"
    assert body["response_type"] == "code"
    assert body["code_challenge_method"] == "S256"
    assert body["code_challenge"] == base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


async def test_request_otp_limits_the_source_name() -> None:
    session = FakeSession(CHALLENGE)

    with patch(CLIENT_SESSION, session):
        await _api().async_request_otp("user@example.com", "x" * 300)

    assert len(session.requests[0][1]["source_name"]) == 255  # noqa: PLR2004


@pytest.mark.parametrize(
    "response",
    [
        pytest.param(FakeResponse(200, {"otp_required": False}), id="otp_not_required"),
        pytest.param(FakeResponse(403, {"otp_required": True}), id="no_auth_session"),
        pytest.param(FakeResponse(500), id="server_error"),
        pytest.param(TimeoutError(), id="timeout"),
        pytest.param(aiohttp.ClientConnectionError(), id="connection_error"),
    ],
)
async def test_request_otp_returns_none_on_failure(response: Any) -> None:
    with patch(CLIENT_SESSION, FakeSession(response)):
        assert await _api().async_request_otp("user@example.com", "Home Assistant") is None


async def test_submit_otp_exchanges_the_code_for_a_token() -> None:
    token = {"access_token": "access"}
    session = FakeSession(FakeResponse(200, {"authorization_code": "code"}), FakeResponse(200, token))

    with patch(CLIENT_SESSION, session):
        assert await _api().async_submit_otp("auth-session", "123456", "verifier") == token

    assert session.requests == [
        (AUTHORIZE_CHALLENGE_URI, {"auth_session": "auth-session", "otp": "123456"}),
        (OAUTH2_TOKEN_URI, {"grant_type": "authorization_code", "code": "code", "code_verifier": "verifier"}),
    ]


@pytest.mark.parametrize(
    "response",
    [
        pytest.param(FakeResponse(400), id="wrong_code"),
        pytest.param(FakeResponse(200, {}), id="no_authorization_code"),
        pytest.param(TimeoutError(), id="timeout"),
        pytest.param(aiohttp.ClientConnectionError(), id="connection_error"),
    ],
)
async def test_submit_otp_returns_none_on_failure(response: Any) -> None:
    session = FakeSession(response)

    with patch(CLIENT_SESSION, session):
        assert await _api().async_submit_otp("auth-session", "000000", "verifier") is None

    assert len(session.requests) == 1


async def test_refresh_token_sends_the_refresh_grant() -> None:
    token = {"access_token": "new"}
    session = FakeSession(FakeResponse(200, token))

    with patch(CLIENT_SESSION, session):
        assert await _api().async_refresh_token({"refresh_token": "refresh"}) == token

    assert session.requests == [(OAUTH2_TOKEN_URI, {"grant_type": "refresh_token", "refresh_token": "refresh"})]


async def test_refresh_token_error_is_raised() -> None:
    with patch(CLIENT_SESSION, FakeSession(FakeResponse(401))), pytest.raises(aiohttp.ClientResponseError):
        await _api().async_refresh_token({"refresh_token": "refresh"})
