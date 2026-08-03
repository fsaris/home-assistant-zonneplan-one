"""Config flow for Zonneplan."""

import asyncio
import logging
import time
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL
from homeassistant.helpers import aiohttp_client, config_entry_oauth2_flow

from .api import AsyncConfigEntryAuth, ZonneplanOAuth2Implementation
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

POLL_INTERVAL_SEC = 3
POLL_MAX_ATTEMPTS = 300  # 300 * 3s = 15 minutes


class ZonneplanLoginFlowHandler(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Config flow to handle Zonneplan authentication."""

    VERSION = 1

    DOMAIN = DOMAIN
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    _email: str | None = None
    _uuid: str | None = None
    _token: dict | None = None
    _poll_task: asyncio.Task | None = None
    flow_impl: ZonneplanOAuth2Implementation = None

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return _LOGGER

    async def async_step_reauth(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Perform reauth upon an API authentication error."""
        _LOGGER.debug("reauth %s", user_input)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=vol.Schema({}),
                last_step=False,
            )
        return await self.async_step_user()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Handle a flow start."""
        await self.async_set_unique_id(DOMAIN)

        self.async_register_implementation(
            self.hass,
            ZonneplanOAuth2Implementation(AsyncConfigEntryAuth(aiohttp_client.async_get_clientsession(self.hass))),
        )

        return await super().async_step_user(user_input)

    async def async_step_auth(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Create an entry for auth."""
        errors = {}

        self.logger.info("step_auth %s", user_input)

        # Use email from existing config on re-auth
        existing_entry = await self.async_set_unique_id(DOMAIN)
        if (not user_input or CONF_EMAIL not in user_input) and existing_entry and "email" in existing_entry.data:
            user_input = {CONF_EMAIL: existing_entry.data["email"]}

        if user_input and CONF_EMAIL in user_input and isinstance(user_input[CONF_EMAIL], str):
            try:
                self._email = user_input[CONF_EMAIL]
                self._uuid = None
                self.logger.info("request login link %s", self._email)
                self._uuid = await self.flow_impl.async_request_temp_pass(self._email)
            except Exception:
                self.logger.exception("Failed to request login link")

            if not self._uuid:
                errors[CONF_EMAIL] = "failed_to_request_login"

        if self._uuid:
            return await self.async_step_wait_for_approval()

        if user_input is None or errors:
            return self.async_show_form(
                step_id="auth",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_EMAIL, default=self._email): str,
                    }
                ),
                last_step=False,
                errors=errors,
            )

        return self.async_abort(reason="failed_to_authenticate")

    async def async_step_wait_for_approval(self, _user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Poll async_get_temp_pass until the login link is approved."""
        if not self._poll_task:
            self._poll_task = self.hass.async_create_task(self._async_poll_for_token(), "zonneplan_poll_temp_pass")

        if not self._poll_task.done():
            return self.async_show_progress(
                step_id="wait_for_approval",
                progress_action="wait_for_approval",
                progress_task=self._poll_task,
            )

        if exc := self._poll_task.exception():
            _LOGGER.error("Error while polling for Zonneplan login approval: %s", exc)
            if isinstance(exc, TimeoutError):
                return self.async_show_progress_done(next_step_id="timeout")
            return self.async_show_progress_done(next_step_id="poll_failed")

        return self.async_show_progress_done(next_step_id="finish")

    async def _async_poll_for_token(self) -> None:
        """Background task: poll until async_get_temp_pass returns a token."""
        if not isinstance(self._email, str) or not isinstance(self._uuid, str):
            msg = "Email and token must be set before polling for token"
            raise TypeError(msg)

        for _attempt in range(POLL_MAX_ATTEMPTS):
            token = await self.flow_impl.async_resolve_token_by_temp_pass(self._email, self._uuid)
            if token is not None:
                self._token = token
                return

            await asyncio.sleep(POLL_INTERVAL_SEC)

        msg = "Login link was not approved in time"
        raise TimeoutError(msg)

    async def async_step_timeout(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Shown when the user never clicked the link in time."""
        if user_input is not None:
            # Let the user retry - restart at the email step.
            self._poll_task = None
            return await self.async_step_user()

        return self.async_show_form(step_id="timeout")

    async def async_step_poll_failed(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Shown on a genuine API error while polling."""
        if user_input is not None:
            # Let the user retry - restart at the email step.
            self._poll_task = None
            return await self.async_step_user()

        return self.async_show_form(step_id="poll_failed")

    async def async_step_finish(self, _user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Finalize the entry now that we have a token."""
        if self._token and "expires_at" not in self._token:
            if "expires_in" not in self._token:
                _LOGGER.error("Token from Zonneplan is missing expires_in: %s", self._token)
                return self.async_abort(reason="oauth_error")
            try:
                self._token["expires_in"] = int(self._token["expires_in"])
            except (TypeError, ValueError) as err:
                _LOGGER.warning("Error converting expires_in to int: %s", err)
                return self.async_abort(reason="oauth_error")
            self._token["expires_at"] = time.time() + self._token["expires_in"]

        return await self.async_oauth_create_entry({"auth_implementation": self.flow_impl.domain, "token": self._token})

    async def async_oauth_create_entry(self, data: dict) -> config_entries.ConfigFlowResult:
        """Create an oauth config entry or update existing entry for reauth."""
        data["email"] = self._email

        existing_entry = await self.async_set_unique_id(DOMAIN)
        if existing_entry:
            self.logger.info("Update entry [%s]: %s", existing_entry.entry_id, data["email"])
            self.hass.config_entries.async_update_entry(existing_entry, title=data["email"], data=data)
            await self.hass.config_entries.async_reload(existing_entry.entry_id)
            return self.async_abort(reason="reauth_successful")

        self.logger.info("Create entry: %s", data["email"])
        return self.async_create_entry(title=data["email"], data=data)
