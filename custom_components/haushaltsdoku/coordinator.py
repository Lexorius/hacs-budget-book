"""Datenkoordinator – nutzt HA's Statistics-API."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import (
    statistics_during_period,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util

from .const import CONF_METERS, CONF_METER_ENTITY

_LOGGER = logging.getLogger(__name__)


class HaushaltsdokuCoordinator:
    """Holt Verbrauchsdaten aus dem Recorder."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry

    @property
    def meters(self) -> list[dict[str, Any]]:
        """Konfigurierte Zähler (aus Options, sonst Data)."""
        return self.entry.options.get(
            CONF_METERS, self.entry.data.get(CONF_METERS, [])
        )

    async def async_get_consumption(
        self,
        entity_id: str,
        start: datetime,
        end: datetime,
        period: str = "day",
    ) -> list[dict[str, Any]]:
        """
        Holt aggregierte Verbrauchswerte für entity_id zwischen start und end.

        period: "5minute" | "hour" | "day" | "week" | "month"
        Liefert eine Liste von {start, end, change} – wobei `change` der
        Verbrauch innerhalb des Bins ist (in Sensoreinheit).
        """
        recorder = get_instance(self.hass)

        # Sicherstellen, dass start/end timezone-aware sind
        if start.tzinfo is None:
            start = dt_util.as_utc(start.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE))
        if end.tzinfo is None:
            end = dt_util.as_utc(end.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE))

        stats = await recorder.async_add_executor_job(
            statistics_during_period,
            self.hass,
            start,
            end,
            {entity_id},
            period,
            None,
            {"change", "sum", "state"},
        )

        rows = stats.get(entity_id, [])
        # Normalisierung: HA liefert "change" für total_increasing-Sensoren
        result = []
        for row in rows:
            change = row.get("change")
            if change is None:
                # Fallback: Differenz aus sum
                change = row.get("sum") or 0
            result.append(
                {
                    "start": dt_util.utc_from_timestamp(row["start"])
                    if isinstance(row["start"], (int, float))
                    else row["start"],
                    "end": dt_util.utc_from_timestamp(row["end"])
                    if isinstance(row["end"], (int, float))
                    else row["end"],
                    "change": float(change),
                }
            )
        return result

    async def async_get_total(
        self, entity_id: str, start: datetime, end: datetime
    ) -> float:
        """Gesamtverbrauch zwischen start und end."""
        rows = await self.async_get_consumption(entity_id, start, end, period="day")
        return sum(r["change"] for r in rows)
