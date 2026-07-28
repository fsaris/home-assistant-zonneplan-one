import logging
from datetime import datetime, timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

import homeassistant.util.dt as dt_util
from aiohttp.client_exceptions import ClientResponseError
from homeassistant.core import HassJob, HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.event import async_call_later

from ..api import AsyncConfigEntryAuth, ZonneplanRateLimitError
from ..const import DOMAIN
from ..zonneplan_api.types import ZonneplanContract
from .zonneplan_data_update_coordinator import ZonneplanDataUpdateCoordinator

if TYPE_CHECKING:
    from collections.abc import Callable

_LOGGER = logging.getLogger(__name__)

DYNAMIC_CHARGE_CONSTRAINTS = "state.dynamic_charging_user_constraints"
DYNAMIC_CHARGE_END_TIME = DYNAMIC_CHARGE_CONSTRAINTS + ".desired_end_time"
DYNAMIC_CHARGE_PERCENTAGE = DYNAMIC_CHARGE_CONSTRAINTS + ".desired_additional_battery_percentage"
DYNAMIC_CHARGE_KILOMETERS = DYNAMIC_CHARGE_CONSTRAINTS + ".desired_distance_in_kilometers"

DYNAMIC_CHARGE_AMOUNT_UNITS = {
    DYNAMIC_CHARGE_KILOMETERS: "kilometers",
    DYNAMIC_CHARGE_PERCENTAGE: "percentage",
}

# The API rejects a session that ends (nearly) immediately.
MIN_DYNAMIC_CHARGE_DURATION = timedelta(minutes=15)


class ChargePointDataUpdateCoordinator(ZonneplanDataUpdateCoordinator):
    """Zonneplan charge point data update coordinator."""

    hass: HomeAssistant
    api: AsyncConfigEntryAuth
    address_uuid: str
    connection_uuid: str
    contract: ZonneplanContract

    def __init__(
        self,
        hass: HomeAssistant,
        api: AsyncConfigEntryAuth,
        address_uuid: str,
        connection_uuid: str,
        contract: ZonneplanContract,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=300),
            request_refresh_debouncer=Debouncer(hass, _LOGGER, cooldown=60, immediate=False),
        )

        self.api: AsyncConfigEntryAuth = api
        self.address_uuid = address_uuid
        self.connection_uuid = connection_uuid
        self.contract = contract

        self._delayed_fetch_charge_point: Callable[[], None] | None = None
        self._pending_dynamic_charge: dict[str, Any] = {}
        self._pending_dynamic_charge_baseline: dict[str, Any] = {}
        self.vehicles: list[dict] = []
        self.selected_vehicle_uuid: str | None = None
        self.zonneplan_api_time_zone = dt_util.get_time_zone("Europe/Amsterdam")

    async def _async_update_data(self) -> dict:
        """Fetch the latest status."""
        try:
            charge_point = await self._async_get_charge_point_data(self.connection_uuid, self.contract.get("uuid"))
        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise

        if not charge_point:
            return self.data

        contract = charge_point["contracts"][0]
        self.vehicles = charge_point.get("vehicles") or []
        self._reconcile_pending_dynamic_charge(contract)

        return contract

    async def _async_get_charge_point_data(self, connection_uuid: str, charge_point_uuid: str) -> dict:
        return await self.api.async_get(connection_uuid, "/charge-points/" + charge_point_uuid)

    async def async_update_charge_point_data(self) -> None:
        charge_point = await self._async_get_charge_point_data(self.connection_uuid, self.contract["uuid"])
        if charge_point:
            contract = charge_point["contracts"][0]
            self.vehicles = charge_point.get("vehicles") or []
            self._reconcile_pending_dynamic_charge(contract)

            self.data = contract
            self.async_update_listeners()

    def get_vehicle(self, vehicle_uuid: str | None) -> dict | None:
        return next((vehicle for vehicle in self.vehicles if vehicle.get("uuid") == vehicle_uuid), None)

    def get_max_desired_kilometers(self) -> int | None:
        vehicle = self.get_vehicle(self.selected_vehicle_uuid)
        if not vehicle:
            return None

        consumption_wh_per_km = vehicle.get("consumption_wh_per_km")
        battery_capacity_useable_wh = vehicle.get("battery_capacity_useable_wh")
        if not consumption_wh_per_km or not battery_capacity_useable_wh:
            return None

        return int(battery_capacity_useable_wh / consumption_wh_per_km)

    async def async_start_charge(self) -> None:
        await self.api.async_post(
            self.connection_uuid,
            "/charge-points/" + self.contract["uuid"] + "/actions/start_boost",
        )

        self.data["state"]["processing"] = True
        self.async_update_listeners()

        await self.async_fetch_charge_point_data()

    async def async_stop_charge(self) -> None:
        await self.api.async_post(
            self.connection_uuid,
            "/charge-points/" + self.contract["uuid"] + "/actions/stop_charging",
        )

        self.data["state"]["processing"] = True

        self.async_update_listeners()

        await self.async_fetch_charge_point_data()

    def parse_dynamic_charge_datetime(self, value: Any) -> datetime | None:
        """Parse an API or staged end time; a value without offset is Europe/Amsterdam, like the API expects it back."""
        parsed = dt_util.parse_datetime(value) if isinstance(value, str) else value
        if not isinstance(parsed, datetime):
            return None

        return parsed.replace(tzinfo=self.zonneplan_api_time_zone) if parsed.tzinfo is None else parsed

    def _api_dynamic_charge_value(self, data: dict | None, path: str) -> Any:
        """Read a constraint from an arbitrary payload; get_data_value can only read self.data."""
        value = data
        for key in path.split("."):
            if not isinstance(value, dict):
                return None
            value = value.get(key)

        return value

    def _dynamic_charge_values_equal(self, path: str, left: Any, right: Any) -> bool:
        if path == DYNAMIC_CHARGE_END_TIME:
            return self.parse_dynamic_charge_datetime(left) == self.parse_dynamic_charge_datetime(right)

        return left == right

    def get_dynamic_charge_value(self, path: str) -> Any:
        """Return the staged value when the user edited this constraint, otherwise the one from the API."""
        if path in self._pending_dynamic_charge:
            return self._pending_dynamic_charge[path]

        return self._api_dynamic_charge_value(self.data, path)

    def stage_dynamic_charge_value(self, path: str, value: Any) -> None:
        """Record a user edit locally; nothing is sent until the apply button is pressed."""
        api_value = self._api_dynamic_charge_value(self.data, path)

        if self._dynamic_charge_values_equal(path, value, api_value):
            self._pending_dynamic_charge.pop(path, None)
            self._pending_dynamic_charge_baseline.pop(path, None)
        else:
            self._pending_dynamic_charge[path] = value
            self._pending_dynamic_charge_baseline[path] = api_value

        self.async_update_listeners()

        # An unavailable apply button says nothing about what it is still waiting for.
        self._build_dynamic_charge_params(log_level=logging.INFO)

    def has_pending_dynamic_charge_changes(self) -> bool:
        return bool(self._pending_dynamic_charge)

    def pending_amount_unit(self) -> str | None:
        """Return the unit the user staged an amount for; the API accepts only one unit per session."""
        return next(
            (unit for path, unit in DYNAMIC_CHARGE_AMOUNT_UNITS.items() if path in self._pending_dynamic_charge),
            None,
        )

    def discard_dynamic_charge_changes(self) -> None:
        self._pending_dynamic_charge.clear()
        self._pending_dynamic_charge_baseline.clear()
        self.async_update_listeners()

    def _reconcile_pending_dynamic_charge(self, data: dict) -> None:
        """Drop staged edits the API moved on from: an expired session or a change made in the app wins."""
        for path, baseline in list(self._pending_dynamic_charge_baseline.items()):
            if not self._dynamic_charge_values_equal(path, self._api_dynamic_charge_value(data, path), baseline):
                self._pending_dynamic_charge.pop(path, None)
                self._pending_dynamic_charge_baseline.pop(path, None)

    def _build_dynamic_charge_params(self, *, log_level: int | None = None) -> dict | None:
        def reject(message: str) -> None:
            if log_level is not None:
                _LOGGER.log(log_level, message)

        desired_end_time = self.get_dynamic_charge_value(DYNAMIC_CHARGE_END_TIME)
        desired_percentage = self.get_dynamic_charge_value(DYNAMIC_CHARGE_PERCENTAGE)
        desired_kilometers = self.get_dynamic_charge_value(DYNAMIC_CHARGE_KILOMETERS)

        desired_end_datetime = self.parse_dynamic_charge_datetime(desired_end_time)
        if desired_end_datetime is None:
            reject("Can not start a dynamic charge session, the end date is not set.")
            return None
        if desired_end_datetime < dt_util.now() + MIN_DYNAMIC_CHARGE_DURATION:
            reject("Can not set the dynamic charge session to end in the past or the next 15 minutes.")
            return None

        user_constraints = {"desired_end_time": desired_end_datetime.astimezone(self.zonneplan_api_time_zone).strftime("%Y-%m-%d %H:%M:00")}

        # A staged amount is the user's explicit choice of unit; otherwise fall back to whatever the API still has.
        pending_unit = self.pending_amount_unit()
        if pending_unit == "kilometers" and desired_kilometers:
            user_constraints["unit"] = "kilometers"
            user_constraints["value"] = desired_kilometers
        elif pending_unit == "percentage" and desired_percentage:
            user_constraints["unit"] = "percentage"
            user_constraints["value"] = desired_percentage
        elif desired_kilometers:
            user_constraints["unit"] = "kilometers"
            user_constraints["value"] = desired_kilometers
        elif desired_percentage:
            user_constraints["unit"] = "percentage"
            user_constraints["value"] = desired_percentage
        else:
            reject("Can not set the dynamic charge session, no amount to charge set.")
            return None

        params = {"user_constraints": user_constraints}
        if self.selected_vehicle_uuid:
            params["vehicle"] = {"vehicle_uuid": self.selected_vehicle_uuid}

        return params

    def dynamic_charge_params_are_valid(self) -> bool:
        return self._build_dynamic_charge_params() is not None

    async def async_apply_dynamic_charge(self) -> None:
        params = self._build_dynamic_charge_params(log_level=logging.WARNING)
        if params is None:
            return

        await self.api.async_post(
            self.connection_uuid,
            "/charge-points/" + self.contract["uuid"] + "/actions/start_dynamic_charging_session",
            params,
        )

        self._pending_dynamic_charge.clear()
        self._pending_dynamic_charge_baseline.clear()

        self.data["state"]["processing"] = True

        self.async_update_listeners()

        await self.async_fetch_charge_point_data()

    def has_dynamic_charge_schedule(self) -> bool:
        return self.parse_dynamic_charge_datetime(self._api_dynamic_charge_value(self.data, DYNAMIC_CHARGE_END_TIME)) is not None

    async def async_reset_dynamic_charge(self) -> None:
        # The app stops a running dynamic session before clearing the planning; mirror that order.
        # A planning scheduled for later has nothing to stop, so tolerate that rejection and still reset.
        try:
            await self.api.async_post(
                self.connection_uuid,
                "/charge-points/" + self.contract["uuid"] + "/actions/stop_dynamic_charging_session",
            )
        except ZonneplanRateLimitError:
            raise
        except ClientResponseError as e:
            _LOGGER.debug("Could not stop the dynamic charge session before reset (%s); continuing", e.status)

        await self.api.async_post(
            self.connection_uuid,
            "/charge-points/" + self.contract["uuid"] + "/actions/reset_schedule",
        )

        self._pending_dynamic_charge.clear()
        self._pending_dynamic_charge_baseline.clear()

        self.data["state"]["processing"] = True

        self.async_update_listeners()

        await self.async_fetch_charge_point_data()

    def _processing_charge_point_update(self) -> bool:
        processing = self.data.get("state", {}).get("processing")

        return bool(processing)

    async def async_fetch_charge_point_data(self, _now: Any = None) -> None:
        if self._delayed_fetch_charge_point:
            self._delayed_fetch_charge_point()
        self._delayed_fetch_charge_point = None

        if self._processing_charge_point_update():
            await self.async_update_charge_point_data()

        if self._processing_charge_point_update():
            # Retry in 10 seconds when api didn't respond with an update
            self._delayed_fetch_charge_point = async_call_later(
                self.hass,
                10,
                HassJob(self.async_fetch_charge_point_data, cancel_on_shutdown=True),
            )
