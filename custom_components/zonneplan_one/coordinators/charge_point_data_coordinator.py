import logging
from datetime import timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING, Any

from aiohttp.client_exceptions import ClientResponseError
import homeassistant.util.dt as dt_util
from homeassistant.core import HassJob, HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.event import async_call_later

from ..api import AsyncConfigEntryAuth
from ..const import DOMAIN
from ..zonneplan_api.types import ZonneplanContract
from .zonneplan_data_update_coordinator import ZonneplanDataUpdateCoordinator

if TYPE_CHECKING:
    from collections.abc import Callable

_LOGGER = logging.getLogger(__name__)


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
        self._last_edited_dynamic_charge_unit: str | None = None
        self.vehicles: list[dict] = []
        self.selected_vehicle_uuid: str | None = None

    async def _async_update_data(self) -> dict:
        """Fetch the latest status."""
        try:
            charge_point = await self._async_get_charge_point_data(self.connection_uuid, self.contract.get("uuid"))

            if not charge_point:
                return self.data

            self.vehicles = charge_point.get("vehicles") or []
            return charge_point["contracts"][0]

        except ClientResponseError as e:
            if e.status == HTTPStatus.UNAUTHORIZED:
                raise ConfigEntryAuthFailed from e
            raise

    async def _async_get_charge_point_data(self, connection_uuid: str, charge_point_uuid: str) -> dict:
        return await self.api.async_get(connection_uuid, "/charge-points/" + charge_point_uuid)

    async def async_update_charge_point_data(self) -> None:
        charge_point = await self._async_get_charge_point_data(self.connection_uuid, self.contract["uuid"])
        if charge_point:
            self.vehicles = charge_point.get("vehicles") or []
            self.data = charge_point["contracts"][0]
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

    async def async_dynamic_charge(self, edited_unit: str | None = None) -> None:
        if edited_unit:
            self._last_edited_dynamic_charge_unit = edited_unit

        desired_end_time = self.get_data_value("state.dynamic_charging_user_constraints.desired_end_time")
        desired_percentage = self.get_data_value("state.dynamic_charging_user_constraints.desired_additional_battery_percentage")
        desired_kilometers = self.get_data_value("state.dynamic_charging_user_constraints.desired_distance_in_kilometers")

        desired_end_datetime = dt_util.parse_datetime(desired_end_time) if isinstance(desired_end_time, str) else None
        if desired_end_datetime is None:
            return  # do nothing when there is no desired end time
        if desired_end_datetime < dt_util.now() + timedelta(minutes=15):
            return  # do nothing when the desired end time already passed (or is too soon)

        user_constraints = {"desired_end_time": desired_end_datetime.strftime("%Y-%m-%d %H:%M:00")}

        if self._last_edited_dynamic_charge_unit == "kilometers" and desired_kilometers:
            user_constraints["unit"] = "kilometers"
            user_constraints["value"] = desired_kilometers
        elif self._last_edited_dynamic_charge_unit == "percentage" and desired_percentage:
            user_constraints["unit"] = "percentage"
            user_constraints["value"] = desired_percentage
        elif desired_kilometers:
            user_constraints["unit"] = "kilometers"
            user_constraints["value"] = desired_kilometers
        elif desired_percentage:
            user_constraints["unit"] = "percentage"
            user_constraints["value"] = desired_percentage

        params = {"user_constraints": user_constraints}
        if self.selected_vehicle_uuid:
            params["vehicle"] =  {"vehicle_uuid": self.selected_vehicle_uuid}

        await self.api.async_post(
            self.connection_uuid,
            "/charge-points/" + self.contract["uuid"] + "/actions/start_dynamic_charging_session",
            {"user_constraints": user_constraints},
        )

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
