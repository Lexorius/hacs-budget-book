"""Haushaltsdoku - automatische Verbrauchsdokumentation für Home Assistant."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_change

from .const import (
    DOMAIN,
    CONF_OUTPUT_DIR,
    CONF_AUTO_MONTHLY,
    CONF_AUTO_YEARLY,
    DEFAULT_OUTPUT_DIR,
    SERVICE_GENERATE_MONTHLY,
    SERVICE_GENERATE_YEARLY,
    SERVICE_GENERATE_RANGE,
)
from .coordinator import HaushaltsdokuCoordinator
from .report_generator import ReportGenerator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

SERVICE_GENERATE_RANGE_SCHEMA = vol.Schema(
    {
        vol.Required("start"): cv.datetime,
        vol.Required("end"): cv.datetime,
        vol.Optional("title"): cv.string,
    }
)

SERVICE_GENERATE_MONTH_SCHEMA = vol.Schema(
    {
        vol.Optional("year"): vol.Coerce(int),
        vol.Optional("month"): vol.All(vol.Coerce(int), vol.Range(min=1, max=12)),
    }
)

SERVICE_GENERATE_YEAR_SCHEMA = vol.Schema(
    {
        vol.Optional("year"): vol.Coerce(int),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Haushaltsdoku from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    output_dir = entry.options.get(
        CONF_OUTPUT_DIR, entry.data.get(CONF_OUTPUT_DIR, DEFAULT_OUTPUT_DIR)
    )
    output_path = Path(hass.config.path(output_dir))
    output_path.mkdir(parents=True, exist_ok=True)

    coordinator = HaushaltsdokuCoordinator(hass, entry)
    generator = ReportGenerator(hass, entry, coordinator, output_path)

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "generator": generator,
        "output_path": output_path,
        "unsub_listeners": [],
    }

    # Services registrieren (nur einmal global)
    if not hass.services.has_service(DOMAIN, SERVICE_GENERATE_MONTHLY):
        await _register_services(hass)

    # Auto-Generation: jeden 1. eines Monats um 00:05 Uhr läuft die Monatsauswertung
    # für den Vormonat
    if entry.options.get(CONF_AUTO_MONTHLY, True):
        unsub = async_track_time_change(
            hass, _make_monthly_callback(hass, entry.entry_id), hour=0, minute=5, second=0
        )
        hass.data[DOMAIN][entry.entry_id]["unsub_listeners"].append(unsub)

    if entry.options.get(CONF_AUTO_YEARLY, True):
        unsub = async_track_time_change(
            hass, _make_yearly_callback(hass, entry.entry_id), hour=0, minute=15, second=0
        )
        hass.data[DOMAIN][entry.entry_id]["unsub_listeners"].append(unsub)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _LOGGER.info("Haushaltsdoku eingerichtet — Output: %s", output_path)
    return True


def _make_monthly_callback(hass: HomeAssistant, entry_id: str):
    async def _cb(now: datetime) -> None:
        if now.day != 1:
            return
        # Vormonat
        last = now - timedelta(days=1)
        gen: ReportGenerator = hass.data[DOMAIN][entry_id]["generator"]
        await gen.generate_monthly(last.year, last.month)

    return _cb


def _make_yearly_callback(hass: HomeAssistant, entry_id: str):
    async def _cb(now: datetime) -> None:
        if now.day != 1 or now.month != 1:
            return
        gen: ReportGenerator = hass.data[DOMAIN][entry_id]["generator"]
        await gen.generate_yearly(now.year - 1)

    return _cb


async def _register_services(hass: HomeAssistant) -> None:
    """Register integration services."""

    async def _handle_monthly(call: ServiceCall) -> None:
        now = datetime.now()
        year = call.data.get("year", now.year)
        month = call.data.get("month", now.month)
        for entry_id, data in hass.data[DOMAIN].items():
            gen: ReportGenerator = data["generator"]
            await gen.generate_monthly(year, month)

    async def _handle_yearly(call: ServiceCall) -> None:
        year = call.data.get("year", datetime.now().year)
        for entry_id, data in hass.data[DOMAIN].items():
            gen: ReportGenerator = data["generator"]
            await gen.generate_yearly(year)

    async def _handle_range(call: ServiceCall) -> None:
        start: datetime = call.data["start"]
        end: datetime = call.data["end"]
        title = call.data.get("title")
        for entry_id, data in hass.data[DOMAIN].items():
            gen: ReportGenerator = data["generator"]
            await gen.generate_range(start, end, title=title)

    hass.services.async_register(
        DOMAIN, SERVICE_GENERATE_MONTHLY, _handle_monthly,
        schema=SERVICE_GENERATE_MONTH_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_GENERATE_YEARLY, _handle_yearly,
        schema=SERVICE_GENERATE_YEAR_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_GENERATE_RANGE, _handle_range,
        schema=SERVICE_GENERATE_RANGE_SCHEMA,
    )


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload nach Options-Update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id, {})
        for unsub in data.get("unsub_listeners", []):
            unsub()
        # Falls letzte Entry: Services entfernen
        if not hass.data[DOMAIN]:
            for svc in (SERVICE_GENERATE_MONTHLY, SERVICE_GENERATE_YEARLY, SERVICE_GENERATE_RANGE):
                if hass.services.has_service(DOMAIN, svc):
                    hass.services.async_remove(DOMAIN, svc)
    return unload_ok
