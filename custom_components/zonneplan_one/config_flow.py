"""Config flow for Zonneplan."""

import logging
import time
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL
from homeassistant.helpers import aiohttp_client, config_entry_oauth2_flow

from .api import AsyncConfigEntryAuth, ZonneplanOAuth2Implementation
from .const import DOMAIN, VERSION

_LOGGER = logging.getLogger(__name__)

CONF_OTP = "otp"


class ZonneplanLoginFlowHandler(config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Config flow to handle Zonneplan authentication."""

    VERSION = 1

    DOMAIN = DOMAIN
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    _email: str | None = None
    _auth_session: str | None = None
    _code_verifier: str | None = None
    _token: dict | None = None
    flow_impl: ZonneplanOAuth2Implementation = None

    @property
    def otp_app_name(self) -> str:
        return f"Zonneplan integration for Home Assistant - {VERSION} - {self.hass.config.location_name}"

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
                self._auth_session = None
                self._code_verifier = None
                self.logger.info("request otp %s", self._email)
                result = await self.flow_impl.async_request_otp(self._email, self.otp_app_name)
                if result:
                    self._auth_session, self._code_verifier = result
            except Exception:
                self.logger.exception("Failed to request otp")

            if not self._auth_session:
                errors[CONF_EMAIL] = "failed_to_request_login"

        if self._auth_session:
            return await self.async_step_otp()

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

    async def async_step_otp(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        """Ask for the 6-digit code emailed to the user and exchange it for tokens."""
        errors = {}

        if user_input and CONF_OTP in user_input:
            if not isinstance(self._auth_session, str) or not isinstance(self._code_verifier, str):
                # Session expired/lost (e.g. HA restarted mid-flow) - start over.
                return await self.async_step_user()

            try:
                self._token = await self.flow_impl.async_submit_otp(
                    self._auth_session,
                    user_input[CONF_OTP],
                    self._code_verifier,
                )
            except Exception:
                self.logger.exception("Failed to submit otp")
                self._token = None

            if self._token:
                return await self.async_step_finish()

            # A used/wrong auth_session can never produce a second code, so a fresh
            # challenge is required before the user can retry the OTP form.
            self._auth_session = None
            self._code_verifier = None
            if isinstance(self._email, str):
                result = await self.flow_impl.async_request_otp(self._email, self.otp_app_name)
                if result:
                    self._auth_session, self._code_verifier = result

            if not self._auth_session:
                # Couldn't even get a fresh challenge - bail back to the email step.
                return await self.async_step_auth()

            errors[CONF_OTP] = "invalid_otp"

        return self.async_show_form(
            step_id="otp",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_OTP): str,
                }
            ),
            last_step=False,
            errors=errors,
        )

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
