"""Haushaltsdoku - automatische Verbrauchsdokumentation für Home Assistant."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from pathlib import Path

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_change

from .const import (
    CONF_AUTO_MONTHLY,
    CONF_AUTO_YEARLY,
    CONF_METER_ENTITY,
    CONF_METER_MANUAL,
    CONF_METER_NAME,
    CONF_METERS,
    CONF_OUTPUT_DIR,
    DEFAULT_OUTPUT_DIR,
    DOMAIN,
    MANUAL_SENSOR_PREFIX,
    SERVICE_ADD_READING,
    SERVICE_GENERATE_MONTHLY,
    SERVICE_GENERATE_RANGE,
    SERVICE_GENERATE_YEARLY,
)
from .coordinator import HaushaltsdokuCoordinator
from .helpers import slugify_name
from .report_generator import ReportGenerator
from .storage import ReadingStore

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER]

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

SERVICE_ADD_READING_SCHEMA = vol.Schema(
    vol.All(
        {
            vol.Optional("meter_id"): cv.string,
            vol.Optional("meter_name"): cv.string,
            vol.Required("value"): vol.Coerce(float),
            vol.Optional("timestamp"): cv.datetime,
        },
        cv.has_at_least_one_key("meter_id", "meter_name"),
    )
)


def _slug(name: str) -> str:  # internal alias, nutzt helpers
    return slugify_name(name)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Haushaltsdoku from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    output_dir = entry.options.get(
        CONF_OUTPUT_DIR, entry.data.get(CONF_OUTPUT_DIR, DEFAULT_OUTPUT_DIR)
    )
    output_path = Path(hass.config.path(output_dir))
    output_path.mkdir(parents=True, exist_ok=True)

    # Storage für manuelle Eingaben
    store = ReadingStore(hass, entry.entry_id)
    await store.async_load()

    # Bei manuellen Zählern entity_id automatisch auf den selbst-erzeugten
    # Sensor zeigen lassen.
    meters = list(
        entry.options.get(CONF_METERS, entry.data.get(CONF_METERS, []))
    )
    needs_save = False
    for meter in meters:
        if meter.get(CONF_METER_MANUAL) and not meter.get(CONF_METER_ENTITY):
            meter[CONF_METER_ENTITY] = (
                f"sensor.{MANUAL_SENSOR_PREFIX}_{_slug(meter[CONF_METER_NAME])}"
            )
            needs_save = True
    if needs_save:
        new_options = dict(entry.options)
        new_options[CONF_METERS] = meters
        hass.config_entries.async_update_entry(entry, options=new_options)

    coordinator = HaushaltsdokuCoordinator(hass, entry, store)
    generator = ReportGenerator(hass, entry, coordinator, output_path)

    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "generator": generator,
        "store": store,
        "output_path": output_path,
        "unsub_listeners": [],
    }

    if not hass.services.has_service(DOMAIN, SERVICE_GENERATE_MONTHLY):
        await _register_services(hass)

    if entry.options.get(CONF_AUTO_MONTHLY, True):
        unsub = async_track_time_change(
            hass, _make_monthly_callback(hass, entry.entry_id),
            hour=0, minute=5, second=0,
        )
        hass.data[DOMAIN][entry.entry_id]["unsub_listeners"].append(unsub)

    if entry.options.get(CONF_AUTO_YEARLY, True):
        unsub = async_track_time_change(
            hass, _make_yearly_callback(hass, entry.entry_id),
            hour=0, minute=15, second=0,
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

    async def _handle_add_reading(call: ServiceCall) -> None:
        meter_id = call.data.get("meter_id")
        meter_name = call.data.get("meter_name")
        value = call.data["value"]
        timestamp = call.data.get("timestamp")

        for entry_id, data in hass.data[DOMAIN].items():
            coordinator: HaushaltsdokuCoordinator = data["coordinator"]
            target_meter = None
            for meter in coordinator.meters:
                if meter_id and meter.get("id") == meter_id:
                    target_meter = meter
                    break
                if meter_name and meter.get(CONF_METER_NAME) == meter_name:
                    target_meter = meter
                    break
            if target_meter:
                if not target_meter.get(CONF_METER_MANUAL):
                    raise ServiceValidationError(
                        f"Zähler '{target_meter[CONF_METER_NAME]}' ist nicht "
                        "als manueller Zähler konfiguriert."
                    )
                await coordinator.async_add_reading(
                    target_meter["id"], value, timestamp
                )
                _LOGGER.info(
                    "Reading hinzugefügt: %s = %s",
                    target_meter[CONF_METER_NAME], value,
                )
                return
        raise ServiceValidationError(
            f"Kein manueller Zähler gefunden (id={meter_id}, name={meter_name})"
        )

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
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_READING, _handle_add_reading,
        schema=SERVICE_ADD_READING_SCHEMA,
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
        if not hass.data[DOMAIN]:
            for svc in (
                SERVICE_GENERATE_MONTHLY,
                SERVICE_GENERATE_YEARLY,
                SERVICE_GENERATE_RANGE,
                SERVICE_ADD_READING,
            ):
                if hass.services.has_service(DOMAIN, svc):
                    hass.services.async_remove(DOMAIN, svc)
    return unload_ok
