"""Konstanten für Haushaltsdoku."""
from __future__ import annotations

DOMAIN = "haushaltsdoku"

# Config keys
CONF_METERS = "meters"
CONF_METER_NAME = "name"
CONF_METER_ENTITY = "entity_id"
CONF_METER_UNIT = "unit"
CONF_METER_PRICE = "price_per_unit"
CONF_METER_BASE_FEE = "base_fee_monthly"
CONF_METER_ICON = "icon"
CONF_METER_COLOR = "color"

CONF_OUTPUT_DIR = "output_dir"
CONF_AUTO_MONTHLY = "auto_monthly"
CONF_AUTO_YEARLY = "auto_yearly"
CONF_CURRENCY = "currency"
CONF_LANGUAGE = "language"

DEFAULT_OUTPUT_DIR = "www/haushaltsdoku"
DEFAULT_CURRENCY = "EUR"
DEFAULT_LANGUAGE = "de"

# Service names
SERVICE_GENERATE_MONTHLY = "generate_monthly_report"
SERVICE_GENERATE_YEARLY = "generate_yearly_report"
SERVICE_GENERATE_RANGE = "generate_range_report"

# Default colors per common type
DEFAULT_COLORS = {
    "kWh": "#f59e0b",
    "Wh": "#f59e0b",
    "m³": "#3b82f6",
    "L": "#06b6d4",
    "MWh": "#ef4444",
}

DEFAULT_ICONS = {
    "kWh": "⚡",
    "Wh": "⚡",
    "m³": "💧",
    "L": "💧",
    "MWh": "🔥",
}
