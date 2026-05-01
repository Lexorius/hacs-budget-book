"""Sensor-Plattform: Status + manuelle Zähler-Werte."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_METER_ICON,
    CONF_METER_MANUAL,
    CONF_METER_NAME,
    CONF_METER_UNIT,
    DOMAIN,
    MANUAL_SENSOR_PREFIX,
)
from .coordinator import HaushaltsdokuCoordinator
from .number import _slug

# Mapping unit → device_class (best effort)
_DEVICE_CLASS_BY_UNIT = {
    "kWh": SensorDeviceClass.ENERGY,
    "Wh": SensorDeviceClass.ENERGY,
    "MWh": SensorDeviceClass.ENERGY,
    "m³": SensorDeviceClass.WATER,
    "L": SensorDeviceClass.WATER,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: HaushaltsdokuCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    output_path: Path = hass.data[DOMAIN][entry.entry_id]["output_path"]

    entities: list[SensorEntity] = [HaushaltsdokuStatusSensor(entry, output_path)]

    for meter in coordinator.meters:
        if meter.get(CONF_METER_MANUAL):
            entities.append(ManualMeterSensor(coordinator, entry, meter))

    async_add_entities(entities)


class HaushaltsdokuStatusSensor(SensorEntity):
    """Status-Sensor mit Pfad/Anzahl der Berichte."""

    _attr_has_entity_name = True
    _attr_name = "Letzter Bericht"
    _attr_icon = "mdi:file-document-multiple"

    def __init__(self, entry: ConfigEntry, output_path: Path) -> None:
        self._entry = entry
        self._output_path = output_path
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Haushaltsdoku",
            "manufacturer": "Community",
            "model": "Verbrauchsbericht-Generator",
        }

    @property
    def native_value(self) -> str | None:
        files = sorted(
            [p for p in self._output_path.glob("*.html") if p.name != "index.html"],
            key=lambda p: p.stat().st_mtime if p.exists() else 0,
            reverse=True,
        )
        if not files:
            return "keine Berichte"
        return files[0].name

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        files = list(self._output_path.glob("*.html"))
        return {
            "report_count": len(files),
            "output_path": str(self._output_path),
            "index_url": "/local/haushaltsdoku/index.html",
            "last_modified": datetime.fromtimestamp(
                max((p.stat().st_mtime for p in files), default=0)
            ).isoformat() if files else None,
        }


class ManualMeterSensor(SensorEntity):
    """Sensor für einen manuell gepflegten Zähler.

    Der Wert spiegelt die letzte vom User eingetragene Ablesung. Mit
    state_class=total_increasing landet er automatisch in den Long-Term-
    Statistics und kann von Reports + Energie-Dashboard genutzt werden.
    """

    _attr_has_entity_name = False
    _attr_should_poll = False
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

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

        slug = _slug(meter[CONF_METER_NAME])
        unit = meter.get(CONF_METER_UNIT)

        self._attr_unique_id = f"{entry.entry_id}_{self._meter_id}_value"
        self.entity_id = f"sensor.{MANUAL_SENSOR_PREFIX}_{slug}"
        self._attr_name = meter[CONF_METER_NAME]
        self._attr_native_unit_of_measurement = unit
        if unit in _DEVICE_CLASS_BY_UNIT:
            self._attr_device_class = _DEVICE_CLASS_BY_UNIT[unit]
        self._attr_icon = "mdi:counter"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Haushaltsdoku",
            "manufacturer": "Community",
            "model": "Verbrauchsbericht-Generator",
        }

    @property
    def native_value(self) -> float | None:
        return self._coordinator.get_latest_value(self._meter_id)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        history = self._coordinator.store.history(self._meter_id, limit=10)
        latest = self._coordinator.store.latest(self._meter_id)
        return {
            "manual": True,
            "last_reading_at": latest.timestamp if latest else None,
            "reading_count": len(self._coordinator.store.history(self._meter_id)),
            "recent_readings": [
                {"timestamp": r.timestamp, "value": r.value} for r in history
            ],
        }

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        @callback
        def _on_change(meter_id: str) -> None:
            if meter_id == self._meter_id:
                self.async_write_ha_state()

        self.async_on_remove(self._coordinator.add_listener(_on_change))
