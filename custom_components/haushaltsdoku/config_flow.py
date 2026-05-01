"""Config Flow für Haushaltsdoku."""
from __future__ import annotations

import logging
from typing import Any
import uuid

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    CONF_AUTO_MONTHLY,
    CONF_AUTO_YEARLY,
    CONF_CURRENCY,
    CONF_LANGUAGE,
    CONF_METER_BASE_FEE,
    CONF_METER_COLOR,
    CONF_METER_ENTITY,
    CONF_METER_ICON,
    CONF_METER_MANUAL,
    CONF_METER_MAX,
    CONF_METER_NAME,
    CONF_METER_PRICE,
    CONF_METER_STEP,
    CONF_METER_UNIT,
    CONF_METERS,
    CONF_OUTPUT_DIR,
    DEFAULT_CURRENCY,
    DEFAULT_LANGUAGE,
    DEFAULT_OUTPUT_DIR,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


METER_TYPE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_METER_MANUAL, default=False): bool,
    }
)

METER_AUTO_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_METER_NAME): TextSelector(TextSelectorConfig()),
        vol.Required(CONF_METER_ENTITY): EntitySelector(
            EntitySelectorConfig(domain=["sensor", "input_number"])
        ),
        vol.Required(CONF_METER_UNIT, default="kWh"): TextSelector(TextSelectorConfig()),
        vol.Optional(CONF_METER_PRICE): NumberSelector(
            NumberSelectorConfig(min=0, step=0.0001, mode=NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_METER_BASE_FEE): NumberSelector(
            NumberSelectorConfig(min=0, step=0.01, mode=NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_METER_ICON): TextSelector(TextSelectorConfig()),
        vol.Optional(CONF_METER_COLOR): TextSelector(TextSelectorConfig()),
    }
)

METER_MANUAL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_METER_NAME): TextSelector(TextSelectorConfig()),
        vol.Required(CONF_METER_UNIT, default="kWh"): TextSelector(TextSelectorConfig()),
        vol.Optional(CONF_METER_MAX, default=9999999): NumberSelector(
            NumberSelectorConfig(min=1, step=1, mode=NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_METER_STEP, default=0.001): NumberSelector(
            NumberSelectorConfig(min=0.0001, step=0.0001, mode=NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_METER_PRICE): NumberSelector(
            NumberSelectorConfig(min=0, step=0.0001, mode=NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_METER_BASE_FEE): NumberSelector(
            NumberSelectorConfig(min=0, step=0.01, mode=NumberSelectorMode.BOX)
        ),
        vol.Optional(CONF_METER_ICON): TextSelector(TextSelectorConfig()),
        vol.Optional(CONF_METER_COLOR): TextSelector(TextSelectorConfig()),
    }
)


class HaushaltsdokuConfigFlow(ConfigFlow, domain=DOMAIN):
    """Anfangs-Setup."""

    VERSION = 1

    def __init__(self) -> None:
        self._meters: list[dict[str, Any]] = []
        self._global: dict[str, Any] = {}
        self._pending_manual: bool = False

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Schritt 1: Globale Einstellungen."""
        # Nur eine Instanz erlauben
        await self.async_set_unique_id("haushaltsdoku_main")
        self._abort_if_unique_id_configured()

        if user_input is not None:
            self._global = user_input
            return await self.async_step_add_meter()

        schema = vol.Schema(
            {
                vol.Optional(CONF_OUTPUT_DIR, default=DEFAULT_OUTPUT_DIR): str,
                vol.Optional(CONF_CURRENCY, default=DEFAULT_CURRENCY): str,
                vol.Optional(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): vol.In(
                    {"de": "Deutsch", "en": "English"}
                ),
                vol.Optional(CONF_AUTO_MONTHLY, default=True): bool,
                vol.Optional(CONF_AUTO_YEARLY, default=True): bool,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_add_meter(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Schritt 2a: Modus wählen — manuell oder automatisch."""
        if user_input is not None:
            self._pending_manual = user_input.get(CONF_METER_MANUAL, False)
            if self._pending_manual:
                return await self.async_step_meter_manual()
            return await self.async_step_meter_auto()

        return self.async_show_form(
            step_id="add_meter",
            data_schema=METER_TYPE_SCHEMA,
            description_placeholders={"count": str(len(self._meters))},
        )

    async def async_step_meter_auto(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            user_input["id"] = str(uuid.uuid4())
            user_input[CONF_METER_MANUAL] = False
            self._meters.append(user_input)
            return await self.async_step_menu()
        return self.async_show_form(
            step_id="meter_auto", data_schema=METER_AUTO_SCHEMA
        )

    async def async_step_meter_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            user_input["id"] = str(uuid.uuid4())
            user_input[CONF_METER_MANUAL] = True
            self._meters.append(user_input)
            return await self.async_step_menu()
        return self.async_show_form(
            step_id="meter_manual", data_schema=METER_MANUAL_SCHEMA
        )

    async def async_step_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Weiteren Zähler oder fertig?"""
        if user_input is not None:
            if user_input.get("action") == "add":
                return await self.async_step_add_meter()
            # finish
            return self.async_create_entry(
                title="Haushaltsdoku",
                data={**self._global, CONF_METERS: self._meters},
            )

        return self.async_show_form(
            step_id="menu",
            data_schema=vol.Schema(
                {
                    vol.Required("action", default="add"): vol.In(
                        {"add": "Weiteren Zähler hinzufügen", "finish": "Fertig"}
                    )
                }
            ),
            description_placeholders={
                "count": str(len(self._meters)),
                "names": ", ".join(m[CONF_METER_NAME] for m in self._meters) or "—",
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return HaushaltsdokuOptionsFlow(config_entry)


class HaushaltsdokuOptionsFlow(OptionsFlow):
    """Options: Zähler hinzufügen / entfernen / globale Einstellungen ändern."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry
        self._pending_manual: bool = False
        # Aktuelle Konfiguration laden
        self._meters: list[dict[str, Any]] = list(
            config_entry.options.get(
                CONF_METERS, config_entry.data.get(CONF_METERS, [])
            )
        )
        self._global: dict[str, Any] = {
            CONF_OUTPUT_DIR: config_entry.options.get(
                CONF_OUTPUT_DIR,
                config_entry.data.get(CONF_OUTPUT_DIR, DEFAULT_OUTPUT_DIR),
            ),
            CONF_CURRENCY: config_entry.options.get(
                CONF_CURRENCY,
                config_entry.data.get(CONF_CURRENCY, DEFAULT_CURRENCY),
            ),
            CONF_LANGUAGE: config_entry.options.get(
                CONF_LANGUAGE,
                config_entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE),
            ),
            CONF_AUTO_MONTHLY: config_entry.options.get(
                CONF_AUTO_MONTHLY, config_entry.data.get(CONF_AUTO_MONTHLY, True)
            ),
            CONF_AUTO_YEARLY: config_entry.options.get(
                CONF_AUTO_YEARLY, config_entry.data.get(CONF_AUTO_YEARLY, True)
            ),
        }

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            action = user_input["action"]
            if action == "add":
                return await self.async_step_add_meter()
            if action == "remove":
                return await self.async_step_remove_meter()
            if action == "global":
                return await self.async_step_global()
            return self._save()

        meters_listing = "\n".join(
            f"• {m[CONF_METER_NAME]} ({m[CONF_METER_ENTITY]})" for m in self._meters
        ) or "—"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("action", default="add"): vol.In(
                        {
                            "add": "Zähler hinzufügen",
                            "remove": "Zähler entfernen",
                            "global": "Globale Einstellungen",
                            "save": "Speichern & schließen",
                        }
                    )
                }
            ),
            description_placeholders={"meters": meters_listing},
        )

    async def async_step_add_meter(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._pending_manual = user_input.get(CONF_METER_MANUAL, False)
            if self._pending_manual:
                return await self.async_step_meter_manual()
            return await self.async_step_meter_auto()
        return self.async_show_form(step_id="add_meter", data_schema=METER_TYPE_SCHEMA)

    async def async_step_meter_auto(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            user_input["id"] = str(uuid.uuid4())
            user_input[CONF_METER_MANUAL] = False
            self._meters.append(user_input)
            return await self.async_step_init()
        return self.async_show_form(
            step_id="meter_auto", data_schema=METER_AUTO_SCHEMA
        )

    async def async_step_meter_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            user_input["id"] = str(uuid.uuid4())
            user_input[CONF_METER_MANUAL] = True
            self._meters.append(user_input)
            return await self.async_step_init()
        return self.async_show_form(
            step_id="meter_manual", data_schema=METER_MANUAL_SCHEMA
        )

    async def async_step_remove_meter(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if not self._meters:
            return await self.async_step_init()

        if user_input is not None:
            self._meters = [m for m in self._meters if m.get("id") != user_input["meter"]]
            return await self.async_step_init()

        options = {m["id"]: m[CONF_METER_NAME] for m in self._meters if "id" in m}
        return self.async_show_form(
            step_id="remove_meter",
            data_schema=vol.Schema({vol.Required("meter"): vol.In(options)}),
        )

    async def async_step_global(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            self._global.update(user_input)
            return await self.async_step_init()

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_OUTPUT_DIR, default=self._global[CONF_OUTPUT_DIR]
                ): str,
                vol.Optional(
                    CONF_CURRENCY, default=self._global[CONF_CURRENCY]
                ): str,
                vol.Optional(
                    CONF_LANGUAGE, default=self._global[CONF_LANGUAGE]
                ): vol.In({"de": "Deutsch", "en": "English"}),
                vol.Optional(
                    CONF_AUTO_MONTHLY, default=self._global[CONF_AUTO_MONTHLY]
                ): bool,
                vol.Optional(
                    CONF_AUTO_YEARLY, default=self._global[CONF_AUTO_YEARLY]
                ): bool,
            }
        )
        return self.async_show_form(step_id="global", data_schema=schema)

    def _save(self) -> FlowResult:
        return self.async_create_entry(
            title="",
            data={**self._global, CONF_METERS: self._meters},
        )
