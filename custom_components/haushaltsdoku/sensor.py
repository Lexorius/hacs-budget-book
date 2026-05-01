"""Sensor-Plattform: Status der Haushaltsdoku."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    output_path: Path = hass.data[DOMAIN][entry.entry_id]["output_path"]
    async_add_entities([HaushaltsdokuStatusSensor(entry, output_path)], True)


class HaushaltsdokuStatusSensor(SensorEntity):
    """Sensor mit Pfad/Anzahl der Berichte."""

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
