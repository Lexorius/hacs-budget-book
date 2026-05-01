"""Datenkoordinator – nutzt HA's Statistics-API plus Storage für manuelle Eingaben."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    statistics_during_period,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util

from .const import CONF_METERS, CONF_METER_ENTITY, CONF_METER_MANUAL
from .storage import ReadingStore

_LOGGER = logging.getLogger(__name__)


class HaushaltsdokuCoordinator:
    """Holt Verbrauchsdaten aus dem Recorder + verwaltet manuelle Eingaben."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        store: ReadingStore,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.store = store
        # Listener, die bei manuellen Updates getriggert werden
        self._listeners: list[Callable[[str], None]] = []

    @property
    def meters(self) -> list[dict[str, Any]]:
        """Konfigurierte Zähler (aus Options, sonst Data)."""
        return self.entry.options.get(
            CONF_METERS, self.entry.data.get(CONF_METERS, [])
        )

    def get_meter(self, meter_id: str) -> dict[str, Any] | None:
        for m in self.meters:
            if m.get("id") == meter_id:
                return m
        return None

    def manual_meters(self) -> list[dict[str, Any]]:
        return [m for m in self.meters if m.get(CONF_METER_MANUAL)]

    # ── Listener für UI-Updates ────────────────────────────────
    def add_listener(self, callback: Callable[[str], None]) -> Callable[[], None]:
        self._listeners.append(callback)

        def _unsub() -> None:
            if callback in self._listeners:
                self._listeners.remove(callback)

        return _unsub

    def _notify(self, meter_id: str) -> None:
        for cb in list(self._listeners):
            try:
                cb(meter_id)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Listener error")

    # ── Manuelle Ablesungen ─────────────────────────────────────
    async def async_add_reading(
        self,
        meter_id: str,
        value: float,
        timestamp: datetime | None = None,
    ) -> None:
        await self.store.async_add(meter_id, value, timestamp)
        self._notify(meter_id)

    def get_latest_value(self, meter_id: str) -> float | None:
        latest = self.store.latest(meter_id)
        return latest.value if latest else None

    # ── Statistics aus Recorder ────────────────────────────────
    async def async_get_consumption(
        self,
        entity_id: str,
        start: datetime,
        end: datetime,
        period: str = "day",
    ) -> list[dict[str, Any]]:
        recorder = get_instance(self.hass)

        if start.tzinfo is None:
            start = dt_util.as_utc(start.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE))
        if end.tzinfo is None:
            end = dt_util.as_utc(end.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE))

        # statistics_during_period: Signatur hat sich über HA-Versionen mehrfach
        # geändert. Wir versuchen das aktuelle 7-Argument-Format und fallen
        # auf ältere Varianten zurück.
        try:
            stats = await recorder.async_add_executor_job(
                statistics_during_period,
                self.hass, start, end, {entity_id}, period, None,
                {"change", "sum", "state"},
            )
        except TypeError:
            try:
                stats = await recorder.async_add_executor_job(
                    statistics_during_period,
                    self.hass, start, end, {entity_id}, period, None,
                    {"sum", "state"},
                )
            except TypeError as err:
                _LOGGER.error(
                    "statistics_during_period nicht aufrufbar (HA-Version "
                    "inkompatibel?): %s", err,
                )
                return []
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Fehler beim Abruf der Statistics: %s", err)
            return []

        rows = stats.get(entity_id, [])
        result = []
        for row in rows:
            change = row.get("change")
            if change is None:
                change = row.get("sum") or 0
            start_val = row["start"]
            end_val = row["end"]
            if isinstance(start_val, (int, float)):
                start_val = dt_util.utc_from_timestamp(start_val)
            if isinstance(end_val, (int, float)):
                end_val = dt_util.utc_from_timestamp(end_val)
            result.append(
                {"start": start_val, "end": end_val, "change": float(change)}
            )
        return result

    async def async_get_total(
        self, entity_id: str, start: datetime, end: datetime
    ) -> float:
        rows = await self.async_get_consumption(entity_id, start, end, period="day")
        return sum(r["change"] for r in rows)
