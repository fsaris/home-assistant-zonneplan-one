import logging
from datetime import datetime

import homeassistant.util.dt as dt_util
from homeassistant.components.datetime import DateTimeEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import (
    CHARGE_POINT,
    DATETIME_TYPE,
    ZonneplanDateTimeEntityDescription,
)
from .coordinators.account_data_coordinator import ZonneplanConfigEntry
from .coordinators.charge_point_data_coordinator import ChargePointDataUpdateCoordinator
from .entity import ChargePointEntity

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: ZonneplanConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    entities = []

    for uuid, connection in entry.runtime_data.coordinators.items():
        if connection.charge_point_installation:
            _LOGGER.debug("Setup datetime for connection %s", uuid)

            entities.extend(
                ZonneplanChargePointDateTime(
                    uuid,
                    sensor_key,
                    connection.charge_point_installation,
                    0,
                    DATETIME_TYPE[CHARGE_POINT][sensor_key],
                )
                for sensor_key in DATETIME_TYPE[CHARGE_POINT]
            )

    async_add_entities(entities)


class ZonneplanChargePointDateTime(ChargePointEntity, CoordinatorEntity[ChargePointDataUpdateCoordinator], DateTimeEntity):
    """Representation of a datetime picker exposed by your integration."""

    coordinator: ChargePointDataUpdateCoordinator
    entity_description: ZonneplanDateTimeEntityDescription
    _connection_uuid: str
    _entity_key: str
    _install_index: int

    def __init__(
        self,
        connection_uuid: str,
        entity_key: str,
        coordinator: ChargePointDataUpdateCoordinator,
        install_index: int,
        description: ZonneplanDateTimeEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._connection_uuid = connection_uuid
        self._entity_key = entity_key
        self._install_index = install_index
        self.entity_description = description

    @property
    def unique_id(self) -> str | None:
        """Return a unique ID."""
        return self.install_uuid + "_" + self._entity_key

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.data or not self.coordinator.last_update_success:
            return False

        state = self.coordinator.get_data_value("state")

        if not state or not state["connectivity_state"]:
            return False

        if "processing" in state:
            return False

        return True

    @property
    def native_value(self) -> datetime:
        value = self.coordinator.get_data_value(self.entity_description.key.format(install_index=self._install_index))
        return dt_util.parse_datetime(value) if isinstance(value, str) else None

    async def async_set_value(self, value: datetime) -> None:
        self.coordinator.set_data_value(
            self.entity_description.key.format(install_index=self._install_index),
            value.strftime("%Y-%m-%d %H:%M:00"),
        )

        await self.coordinator.async_dynamic_charge()
