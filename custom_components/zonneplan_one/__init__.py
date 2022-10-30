"""The Zonneplan integration."""
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    aiohttp_client,
    config_entry_oauth2_flow,
)

from . import api, config_flow
from .coordinator import ZonneplanUpdateCoordinator
from .const import DOMAIN

PLATFORMS = ["sensor"]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Zonneplan component."""
    hass.data.setdefault(DOMAIN, {})

    config_flow.ZonneplanLoginFlowHandler.async_register_implementation(
        hass,
        api.ZonneplanOAuth2Implementation(
            api.AsyncConfigEntryAuth(aiohttp_client.async_get_clientsession(hass))
        ),
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Zonneplan from a config entry."""

    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass, entry
        )
    )

    session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)
    zonneplanApi = api.AsyncConfigEntryAuth(
        aiohttp_client.async_get_clientsession(hass), session
    )

    hass.data[DOMAIN][entry.entry_id] = zonneplanApi

    coordinator = ZonneplanUpdateCoordinator(hass, zonneplanApi)
    await coordinator.async_config_entry_first_refresh()

    # await coordinator.async_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "api": zonneplanApi,
        "coordinator": coordinator,
    }

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
