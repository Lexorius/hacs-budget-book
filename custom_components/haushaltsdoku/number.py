"""Number-Plattform: Eingabefelder für manuelle Zähler."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_METER_MANUAL,
    CONF_METER_MAX,
    CONF_METER_NAME,
    CONF_METER_STEP,
    CONF_METER_UNIT,
    DOMAIN,
    MANUAL_SENSOR_PREFIX,
)
from .coordinator import HaushaltsdokuCoordinator
from .helpers import slugify_name

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HaushaltsdokuCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities = []
    for meter in coordinator.meters:
        if not meter.get(CONF_METER_MANUAL):
            continue
        entities.append(MeterInputEntity(coordinator, entry, meter))
    if entities:
        async_add_entities(entities)


class MeterInputEntity(NumberEntity):
    """Eingabefeld für einen manuellen Zähler."""

    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_icon = "mdi:counter"

    def __init__(
        self,
        coordinator: HaushaltsdokuCoordinator,
        entry: ConfigEntry,
        meter: dict[str, Any],
    ) -> None:
        self._coordinator = coordinator
        self._entry = entry
        self._meter_id: str = meter["id"]
        self._meter = meter

        slug = slugify_name(meter[CONF_METER_NAME])
        self._attr_unique_id = f"{entry.entry_id}_{self._meter_id}_input"
        # gewünschte object_id
        self.entity_id = f"number.{MANUAL_SENSOR_PREFIX}_{slug}_input"
        self._attr_name = f"{meter[CONF_METER_NAME]} (Eingabe)"
        self._attr_native_unit_of_measurement = meter.get(CONF_METER_UNIT)
        self._attr_native_max_value = float(meter.get(CONF_METER_MAX, 9_999_999))
        # HA validiert step >= 0.001 — defensiv clampen, falls in der Config
        # versehentlich ein kleinerer Wert steht
        self._attr_native_step = max(0.001, float(meter.get(CONF_METER_STEP, 0.001)))

        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Haushaltsdoku",
            "manufacturer": "Community",
            "model": "Verbrauchsbericht-Generator",
        }

    @property
    def native_value(self) -> float | None:
        return self._coordinator.get_latest_value(self._meter_id)

    async def async_set_native_value(self, value: float) -> None:
        """Wird aufgerufen, wenn der User über die UI einen neuen Wert einträgt."""
        latest = self._coordinator.get_latest_value(self._meter_id)
        if latest is not None and value < latest:
            _LOGGER.warning(
                "Neuer Stand (%s) ist kleiner als letzter Stand (%s) für %s",
                value, latest, self._meter[CONF_METER_NAME],
            )
        await self._coordinator.async_add_reading(self._meter_id, value)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        @callback
        def _on_change(meter_id: str) -> None:
            if meter_id == self._meter_id:
                self.async_write_ha_state()

        self.async_on_remove(self._coordinator.add_listener(_on_change))
