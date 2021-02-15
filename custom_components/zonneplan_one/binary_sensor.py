"""Zonneplan Binary Sensor"""

import logging
from homeassistant.helpers.typing import HomeAssistantType

from .coordinator import ZonneplanUpdateCoordinator
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistantType, config_entry, async_add_entities):

    coordinator: ZonneplanUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        "coordinator"
    ]

    _LOGGER.debug("setup binary sensor")
