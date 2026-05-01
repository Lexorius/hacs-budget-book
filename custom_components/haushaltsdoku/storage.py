"""Persistenz für manuelle Zählerablesungen."""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

import homeassistant.util.dt as dt_util
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import STORAGE_KEY_FMT, STORAGE_VERSION

_LOGGER = logging.getLogger(__name__)


@dataclass
class Reading:
    """Eine einzelne Ablesung."""

    meter_id: str
    value: float
    timestamp: str  # ISO format

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Reading":
        return cls(
            meter_id=data["meter_id"],
            value=float(data["value"]),
            timestamp=data["timestamp"],
        )

    @property
    def datetime(self) -> datetime:
        return dt_util.parse_datetime(self.timestamp) or dt_util.utcnow()


class ReadingStore:
    """Speichert die History manueller Ablesungen pro Config-Entry."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self._store: Store = Store(
            hass,
            STORAGE_VERSION,
            STORAGE_KEY_FMT.format(entry_id=entry_id),
        )
        self._readings: list[Reading] = []
        self._loaded = False

    async def async_load(self) -> None:
        if self._loaded:
            return
        data = await self._store.async_load() or {}
        raw = data.get("readings", [])
        self._readings = [Reading.from_dict(r) for r in raw]
        self._loaded = True
        _LOGGER.debug("ReadingStore loaded %d readings", len(self._readings))

    async def async_save(self) -> None:
        await self._store.async_save(
            {"readings": [asdict(r) for r in self._readings]}
        )

    async def async_add(
        self, meter_id: str, value: float, timestamp: datetime | None = None
    ) -> Reading:
        if timestamp is None:
            timestamp = dt_util.utcnow()
        reading = Reading(
            meter_id=meter_id,
            value=float(value),
            timestamp=timestamp.isoformat(),
        )
        self._readings.append(reading)
        # nach Zeit sortieren, damit "letzter Stand" trivial ist
        self._readings.sort(key=lambda r: r.timestamp)
        await self.async_save()
        return reading

    def latest(self, meter_id: str) -> Reading | None:
        """Letzter Eintrag für einen Zähler."""
        for r in reversed(self._readings):
            if r.meter_id == meter_id:
                return r
        return None

    def history(self, meter_id: str, limit: int | None = None) -> list[Reading]:
        items = [r for r in self._readings if r.meter_id == meter_id]
        if limit:
            items = items[-limit:]
        return list(reversed(items))  # neuestes zuerst

    def all_readings(self) -> list[Reading]:
        return list(self._readings)

    async def async_delete(self, meter_id: str, timestamp: str) -> bool:
        """Eine Ablesung anhand timestamp+meter_id entfernen."""
        before = len(self._readings)
        self._readings = [
            r
            for r in self._readings
            if not (r.meter_id == meter_id and r.timestamp == timestamp)
        ]
        if len(self._readings) < before:
            await self.async_save()
            return True
        return False

    async def async_purge_for_meter(self, meter_id: str) -> None:
        """Alle Einträge eines Zählers löschen (z.B. wenn Zähler entfernt wird)."""
        self._readings = [r for r in self._readings if r.meter_id != meter_id]
        await self.async_save()
