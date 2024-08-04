"""Config flow for Zonneplan"""
import logging

from typing import Any, Dict, Mapping, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import aiohttp_client, config_entry_oauth2_flow

from homeassistant.const import CONF_EMAIL

from .const import DOMAIN
from .api import AsyncConfigEntryAuth, ZonneplanApi, ZonneplanOAuth2Implementation

_LOGGER = logging.getLogger(__name__)


class ZonneplanLoginFlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Config flow to handle Zonneplan authentication."""

    DOMAIN = DOMAIN
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        self._email = ""
        self._token = ""
        super().__init__()
        self.flow_impl: ZonneplanOAuth2Implementation = None  # type: ignore

        _LOGGER.info("__init__")

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return logging.getLogger(__name__)

    async def async_step_reauth(self, user_input=None):
        """Perform reauth upon an API authentication error."""
        _LOGGER.debug("reauth %s", user_input)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            return self.async_show_form(
                step_id="reauth_confirm",
                data_schema=vol.Schema({}),
                last_step=False,
            )
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow start."""
        await self.async_set_unique_id(DOMAIN)

        self.async_register_implementation(
            self.hass,
            ZonneplanOAuth2Implementation(
                AsyncConfigEntryAuth(aiohttp_client.async_get_clientsession(self.hass))
            ),
        )

        return await super().async_step_user(user_input)

    async def async_step_auth(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create an entry for auth."""

        errors = {}

        self.logger.info("step_auth %s", user_input)

        # Use email from existing config on re-auth
        existing_entry = await self.async_set_unique_id(DOMAIN)
        if existing_entry and "email" in existing_entry.data:
            user_input = {CONF_EMAIL: existing_entry.data["email"]}

        if user_input and CONF_EMAIL in user_input:
            try:
                self._email = user_input[CONF_EMAIL]
                self._token = ""
                self.logger.info("request login link %s", self._email)
                self._token = await self.flow_impl.async_request_temp_pass(self._email)
            except Exception as e:
                self.logger.exception("Failed %s", e)

            if not self._token:
                errors[CONF_EMAIL] = "failed_to_request_login"

        if self._token:
            return await self.async_step_fetch_password()

        if user_input is None or errors:
            return self.async_show_form(
                step_id="auth",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_EMAIL, default=""): str,
                    }
                ),
                last_step=False,
                errors=errors,
            )

        return self.async_abort(reason="failed_to_authenticate")

    async def async_step_fetch_password(self, user_input: Optional[Mapping] = None):
        self.logger.info("fetch_password %s", user_input)
        if user_input is not None:
            self.external_data = {"email": self._email, "uuid": self._token}
            self.logger.debug("next step %s", self.external_data)
            return await self.async_step_creation()

        return self.async_show_form(
            step_id="fetch_password",
            data_schema=vol.Schema({}),
            last_step=False,
        )

    async def async_oauth_create_entry(self, data: dict) -> dict:
        """Create an oauth config entry or update existing entry for reauth."""

        data["email"] = self._email

        existing_entry = await self.async_set_unique_id(DOMAIN)
        if existing_entry:
            self.logger.info(
                "Update entry [%s]: %s", existing_entry.entry_id, data["email"]
            )
            self.hass.config_entries.async_update_entry(existing_entry, data=data)
            await self.hass.config_entries.async_reload(existing_entry.entry_id)
            return self.async_abort(reason="reauth_successful")

        self.logger.info("Create entry: %s", data["email"])
        return self.async_create_entry(title=data["email"], data=data)
