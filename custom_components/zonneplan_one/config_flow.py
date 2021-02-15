"""Config flow for Zonneplan ONE."""
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
                errors=errors,
            )

        return self.async_abort(reason="failed_to_authenticate")

    async def async_step_fetch_password(self, user_input: Optional[Mapping] = None):
        self.logger.info("fetch_password %s", user_input)
        if user_input is not None:
            self.external_data = {"email": self._email, "uuid": self._token}
            self.logger.debug("next step")
            return await self.async_step_creation()

        return self.async_show_form(step_id="fetch_password")

    async def async_oauth_create_entry(self, data: dict) -> dict:
        """Create an entry for the flow."""
        return self.async_create_entry(title=self._email, data=data)