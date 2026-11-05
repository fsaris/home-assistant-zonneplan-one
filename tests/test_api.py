"""Tests for the API client, using a fake transport so error responses behave like aiohttp's."""

import base64
import hashlib
from datetime import date
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientResponseError

from custom_components.zonneplan_one.api import (
    AsyncConfigEntryAuth,
    ZonneplanApiError,
    ZonneplanOAuth2Implementation,
    ZonneplanRateLimitError,
    _parse_retry_after,
)
from custom_components.zonneplan_one.const import DOMAIN
from custom_components.zonneplan_one.zonneplan_api.api import _generate_pkce_pair

URL = "https://app-api.zonneplan.nl/"


class FakeResponse:
    def __init__(self, status: int = 200, body: Any = None, headers: dict[str, str] | None = None) -> None:
        self.status = status
        self.headers = headers or {}
        self.request_info = MagicMock()
        self.history = ()
        self._body = body

    async def json(self) -> Any:
        return self._body

    async def text(self) -> str:
        return str(self._body)

    def raise_for_status(self) -> None:
        if self.status >= 400:  # noqa: PLR2004
            raise ClientResponseError(self.request_info, (), status=self.status)


def _api(*responses: FakeResponse) -> tuple[AsyncConfigEntryAuth, AsyncMock]:
    oauth_session = MagicMock()
    oauth_session.async_request = AsyncMock(side_effect=responses)
    return AsyncConfigEntryAuth(MagicMock(), oauth_session), oauth_session.async_request


async def test_get_unwraps_data_and_keeps_response_for_diagnostics() -> None:
    api, request = _api(FakeResponse(body={"data": {"a": 1}}))

    assert await api.async_get("connection", "/summary") == {"a": 1}

    assert request.call_args.args == ("GET", f"{URL}connections/connection/summary")
    assert api.diagnostics == {"connections/connection/summary": {"data": {"a": 1}}}


async def test_etag_is_sent_and_not_modified_returns_none() -> None:
    api, request = _api(FakeResponse(body={"data": {}}, headers={"ETag": "tag"}), FakeResponse(status=304))

    await api.async_get("connection", "/summary")
    assert "If-None-Match" not in request.call_args.kwargs["headers"]

    assert await api.async_get("connection", "/summary") is None
    assert request.call_args.kwargs["headers"]["If-None-Match"] == "tag"


async def test_ignore_etag_skips_the_header() -> None:
    api, request = _api(FakeResponse(body={"data": {}}, headers={"ETag": "tag"}), FakeResponse(body={"data": {}}))

    await api.async_get("connection", "/summary")
    await api.async_get("connection", "/summary", ignore_etag=True)

    assert "If-None-Match" not in request.call_args.kwargs["headers"]


async def test_consumer_prices_keep_an_etag_per_contract() -> None:
    """A shared ETag would give the second contract a 304 for data it never received."""
    api, request = _api(FakeResponse(body={"data": {}}, headers={"ETag": "first"}), FakeResponse(body={"data": {}}))

    await api.async_get_consumer_prices("gas-daily", "contract-1")
    await api.async_get_consumer_prices("gas-daily", "contract-2")

    assert "If-None-Match" not in request.call_args.kwargs["headers"]


@pytest.mark.parametrize(
    ("header", "expected"),
    [("30", 30), (None, None), ("Wed, 21 Oct 2026 07:28:00 GMT", None)],
)
def test_parse_retry_after(header: str | None, expected: int | None) -> None:
    assert _parse_retry_after(header) == expected


async def test_get_rate_limit_raises_with_retry_after() -> None:
    api, _ = _api(FakeResponse(status=429, headers={"Retry-After": "30"}))

    with pytest.raises(ZonneplanRateLimitError) as err:
        await api.async_get("connection", "/summary")

    assert err.value.retry_after == 30  # noqa: PLR2004


async def test_post_rate_limit_raises() -> None:
    api, _ = _api(FakeResponse(status=429))

    with pytest.raises(ZonneplanRateLimitError):
        await api.async_post("connection", "/action")


async def test_get_error_status_raises() -> None:
    api, _ = _api(FakeResponse(status=500))

    with pytest.raises(ClientResponseError):
        await api.async_get("connection", "/summary")


async def test_post_error_status_raises() -> None:
    api, _ = _api(FakeResponse(status=422, body="invalid"))

    with pytest.raises(ClientResponseError):
        await api.async_post("connection", "/action", {"a": 1})


async def test_post_no_content_returns_ok() -> None:
    api, request = _api(FakeResponse(status=204))

    assert await api.async_post("connection", "/action") == {"ok": True}
    assert request.call_args.kwargs["json"] == {}


async def test_set_reserve_discharge_posts_to_the_contract_action() -> None:
    api, request = _api(FakeResponse(body={"ok": True}))

    await api.async_set_reserve_discharge("connection", "contract", 500)

    assert request.call_args.args[1] == f"{URL}connections/connection/home-battery-installation/contract/actions/set_backup_power_reserved_state_of_charge"
    assert request.call_args.kwargs["json"] == {"reserved_state_of_charge_wh": 500}


def test_pkce_challenge_is_the_s256_hash_of_the_verifier() -> None:
    verifier, challenge = _generate_pkce_pair()

    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    assert challenge == base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    assert 43 <= len(verifier) <= 128  # noqa: PLR2004


def test_pkce_pairs_are_unique() -> None:
    assert _generate_pkce_pair() != _generate_pkce_pair()


async def test_access_token_is_refreshed_when_expired() -> None:
    oauth_session = MagicMock(valid_token=False, token={"access_token": "new"})
    oauth_session.async_ensure_token_valid = AsyncMock()
    api = AsyncConfigEntryAuth(MagicMock(), oauth_session)

    assert await api.async_get_access_token() == "new"
    oauth_session.async_ensure_token_valid.assert_awaited_once()


async def test_valid_access_token_is_not_refreshed() -> None:
    oauth_session = MagicMock(valid_token=True, token={"access_token": "current"})
    oauth_session.async_ensure_token_valid = AsyncMock()
    api = AsyncConfigEntryAuth(MagicMock(), oauth_session)

    assert await api.async_get_access_token() == "current"
    oauth_session.async_ensure_token_valid.assert_not_awaited()


async def test_set_locale_puts_the_locale() -> None:
    api, request = _api(FakeResponse(status=204))

    await api.async_set_locale("nl-NL")

    assert request.call_args.args == ("PUT", f"{URL}user-accounts/locale")
    assert request.call_args.kwargs["json"] == {"locale": "nl-NL"}


@pytest.mark.parametrize(
    ("call", "path"),
    [
        pytest.param(lambda api: api.async_get_user_accounts(), "user-accounts/me", id="accounts"),
        pytest.param(
            lambda api: api.async_get_battery_chart("c", "days", date(2025, 12, 1)),
            "contracts/c/home_battery_installation/charts/days?date=2025-12-01",
            id="chart",
        ),
        pytest.param(lambda api: api.async_get_battery_control_mode("c"), "api/contracts/c/home-battery/control-mode", id="control_mode"),
        pytest.param(
            lambda api: api.async_get_battery_home_optimization("c"), "api/contracts/c/home-battery/control-mode/home_optimization", id="optimization"
        ),
        pytest.param(lambda api: api.async_get_consumer_prices("gas-daily", "c"), "api/consumer-prices/charts/gas-daily", id="prices"),
    ],
)
async def test_get_endpoints_use_the_expected_url(call: Any, path: str) -> None:
    api, request = _api(FakeResponse(body={"data": {}}))

    await call(api)

    assert request.call_args.args == ("GET", f"{URL}{path}")


async def test_ratelimit_header_is_handled_on_a_normal_response(caplog: pytest.LogCaptureFixture) -> None:
    api, _ = _api(FakeResponse(body={"data": {}}, headers={"x-ratelimit-remaining": "0", "Retry-After": "30"}))

    await api.async_get("connection", "/summary")

    assert "retry in: 30 seconds" in caplog.text


def _implementation(**api_methods: AsyncMock) -> ZonneplanOAuth2Implementation:
    return ZonneplanOAuth2Implementation(MagicMock(**api_methods))


def test_oauth_implementation_identifies_itself() -> None:
    implementation = _implementation()

    assert implementation.name == "Zonneplan"
    assert implementation.domain == DOMAIN


async def test_oauth_implementation_has_no_redirect_flow() -> None:
    implementation = _implementation()

    assert await implementation.async_generate_authorize_url("flow") == ""
    with pytest.raises(NotImplementedError):
        await implementation.async_resolve_external_data({})


async def test_oauth_implementation_forwards_the_login_calls() -> None:
    implementation = _implementation(
        async_request_otp=AsyncMock(return_value=("session", "verifier")),
        async_submit_otp=AsyncMock(return_value={"access_token": "access"}),
    )

    assert await implementation.async_request_otp("user@example.com", "source") == ("session", "verifier")
    assert await implementation.async_submit_otp("session", "123456", "verifier") == {"access_token": "access"}


async def test_oauth_implementation_refresh_returns_the_new_token() -> None:
    implementation = _implementation(async_refresh_token=AsyncMock(return_value={"access_token": "new"}))

    assert await implementation._async_refresh_token({"refresh_token": "refresh"}) == {"access_token": "new"}


async def test_oauth_implementation_refresh_without_token_raises() -> None:
    implementation = _implementation(async_refresh_token=AsyncMock(return_value=None))

    with pytest.raises(ZonneplanApiError):
        await implementation._async_refresh_token({"refresh_token": "refresh"})
