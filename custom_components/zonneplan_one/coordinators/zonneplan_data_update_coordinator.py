from __future__ import annotations
from datetime import timedelta

import logging
from collections.abc import Callable
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.core import CALLBACK_TYPE, HomeAssistant

from typing import Any

_LOGGER = logging.getLogger(__name__)


class ZonneplanDataUpdateCoordinator(DataUpdateCoordinator):
    _custom_data_update_interval: timedelta | None

    def __init__(self, hass: HomeAssistant, logger: logging.Logger, update_interval: timedelta | None = None, **kwargs):
        super().__init__(
            hass,
            logger,
            update_interval=None,
            **kwargs
        )
        self._custom_data_update_interval = update_interval

    def async_add_listener(self, update_callback: CALLBACK_TYPE, context: Any = None) -> Callable[[], None]:

        # Initiate interval after first item registration
        if len(self._listeners) == 0:
            _LOGGER.info("Set interval for %s from %s to %s", self.__class__.__name__, self.update_interval, self._custom_data_update_interval)
            self.update_interval = self._custom_data_update_interval
            self.hass.async_create_task(self._async_refresh())

        return super().async_add_listener(update_callback, context)

    def get_data_value(self, value_path: str):

        keys = value_path.split(".")
        rv = self.data
        for key in keys:
            if rv is None:
                _LOGGER.info("No value for %s part (%s)", value_path, key)
                return None

            if key.lstrip('-').isdigit():
                key = int(key)
                if not type(rv) is list or (key >= 0 and len(rv) <= key) or (key < 0 and -len(rv) > key):
                    _LOGGER.info(
                        "Could not find %d of %s",
                        key,
                        value_path,
                    )
                    _LOGGER.debug(" in %s %s", rv, type(rv))
                    return None

            elif key not in rv:
                _LOGGER.info("Could not find %s of %s", key, value_path)
                _LOGGER.debug("in %s", rv)
                return None
            rv = rv[key]

        return rv

    def set_data_value(self, value_path: str, value: str | int):

        keys = value_path.split(".")
        rv = self.data
        for key in keys[:-1]:
            if rv is None:
                return

            if key.lstrip('-').isdigit():
                key = int(key)
                if not type(rv) is list or (key >= 0 and len(rv) <= key) or (key < 0 and -len(rv) > key):
                    return

            elif key not in rv:
                return

            rv = rv[key]

        last_key = keys[-1]
        if last_key.isdigit():
            last_key = int(last_key)
            if type(rv) is list and len(rv) > last_key:
                rv[last_key] = value
        else:
            rv[last_key] = value
