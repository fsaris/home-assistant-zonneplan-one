"""Tests for the email + one-time code login flow."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.zonneplan_one.const import DOMAIN

API_CLASS = "custom_components.zonneplan_one.zonneplan_api.api.ZonneplanApi"
EMAIL = "new-user@example.com"
TOKEN = {"access_token": "access", "refresh_token": "refresh", "token_type": "Bearer", "expires_in": 3600}


@pytest.fixture
def request_otp() -> Generator[AsyncMock]:
    with patch(f"{API_CLASS}.async_request_otp", AsyncMock(return_value=("auth-session", "verifier"))) as mock:
        yield mock


@pytest.fixture
def submit_otp() -> Generator[AsyncMock]:
    with patch(f"{API_CLASS}.async_submit_otp", AsyncMock(return_value=dict(TOKEN))) as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_setup_entry() -> Generator[AsyncMock]:
    with patch("custom_components.zonneplan_one.async_setup_entry", AsyncMock(return_value=True)) as mock:
        yield mock


@pytest.fixture(autouse=True)
async def setup_component(hass: HomeAssistant, current_request_with_host: None) -> None:  # noqa: ARG001
    assert await async_setup_component(hass, DOMAIN, {})


async def _start_flow(hass: HomeAssistant) -> dict:
    return await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})


async def _at_otp_step(hass: HomeAssistant) -> dict:
    result = await _start_flow(hass)
    return await hass.config_entries.flow.async_configure(result["flow_id"], {"email": EMAIL})


@pytest.mark.usefixtures("submit_otp")
async def test_login_creates_entry(hass: HomeAssistant, request_otp: AsyncMock) -> None:
    result = await _start_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "auth"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"email": EMAIL})
    assert result["step_id"] == "otp"
    assert request_otp.call_args.args[0] == EMAIL

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"otp": "123456"})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == EMAIL
    assert result["data"]["email"] == EMAIL
    assert result["data"]["token"]["access_token"] == TOKEN["access_token"]
    assert "expires_at" in result["data"]["token"]


async def test_failed_otp_request_shows_error(hass: HomeAssistant, request_otp: AsyncMock) -> None:
    request_otp.return_value = None

    result = await _at_otp_step(hass)

    assert result["step_id"] == "auth"
    assert result["errors"] == {"email": "failed_to_request_login"}


@pytest.mark.usefixtures("request_otp")
async def test_wrong_code_requests_new_challenge_and_can_retry(hass: HomeAssistant, request_otp: AsyncMock, submit_otp: AsyncMock) -> None:
    result = await _at_otp_step(hass)
    submit_otp.return_value = None

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"otp": "000000"})

    assert result["step_id"] == "otp"
    assert result["errors"] == {"otp": "invalid_otp"}
    assert request_otp.call_count == 2  # noqa: PLR2004

    submit_otp.return_value = dict(TOKEN)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"otp": "123456"})

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_wrong_code_without_new_challenge_returns_to_email(hass: HomeAssistant, request_otp: AsyncMock, submit_otp: AsyncMock) -> None:
    result = await _at_otp_step(hass)
    submit_otp.return_value = None
    request_otp.return_value = None

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"otp": "000000"})

    assert result["step_id"] == "auth"


@pytest.mark.usefixtures("request_otp")
async def test_token_without_expiry_aborts(hass: HomeAssistant, submit_otp: AsyncMock) -> None:
    result = await _at_otp_step(hass)
    submit_otp.return_value = {"access_token": "access"}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"otp": "123456"})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "oauth_error"


async def test_otp_request_exception_shows_error(hass: HomeAssistant, request_otp: AsyncMock) -> None:
    request_otp.side_effect = RuntimeError("unexpected")

    result = await _at_otp_step(hass)

    assert result["step_id"] == "auth"
    assert result["errors"] == {"email": "failed_to_request_login"}


@pytest.mark.usefixtures("request_otp")
async def test_otp_submit_exception_is_handled_like_a_wrong_code(hass: HomeAssistant, submit_otp: AsyncMock) -> None:
    result = await _at_otp_step(hass)
    submit_otp.side_effect = RuntimeError("unexpected")

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"otp": "123456"})

    assert result["step_id"] == "otp"
    assert result["errors"] == {"otp": "invalid_otp"}


@pytest.mark.usefixtures("request_otp")
async def test_token_with_invalid_expiry_aborts(hass: HomeAssistant, submit_otp: AsyncMock) -> None:
    result = await _at_otp_step(hass)
    submit_otp.return_value = {"access_token": "access", "expires_in": "soon"}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"otp": "123456"})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "oauth_error"


@pytest.mark.usefixtures("request_otp")
async def test_token_with_expiry_as_text_is_accepted(hass: HomeAssistant, submit_otp: AsyncMock) -> None:
    result = await _at_otp_step(hass)
    submit_otp.return_value = {"access_token": "access", "expires_in": "3600"}

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"otp": "123456"})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"]["token"]["expires_in"] == 3600  # noqa: PLR2004


@pytest.mark.usefixtures("submit_otp")
async def test_reauth_updates_existing_entry(hass: HomeAssistant, request_otp: AsyncMock, config_entry: MockConfigEntry) -> None:
    config_entry.add_to_hass(hass)

    result = await config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "otp"
    assert request_otp.call_args.args[0] == config_entry.data["email"]

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"otp": "123456"})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data["token"]["access_token"] == TOKEN["access_token"]
