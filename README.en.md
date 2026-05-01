# Haushaltsdoku — Consumption Reports for Home Assistant

🇬🇧 English · [🇩🇪 Deutsch](README.md)

A HACS-compatible custom integration that turns your sensor data into
**printable HTML consumption reports** — monthly and yearly, with summary
cards, SVG charts, data tables, cost calculation, and dark mode. No external
dependencies, no JavaScript, fully self-contained.

> **Note:** The repository is named `hacs-budget-book`, but the integration
> registers itself in HA under the domain `haushaltsdoku` — by design,
> doesn't affect anything.

**Author:** [Lexorius](https://github.com/Lexorius) (Thomas Kloppholz)

📋 Version history: see [CHANGELOG.md](CHANGELOG.md)

## Features

- 📊 **HTML reports with embedded SVG charts** — printable, no JS required
- 🗓️ **Automatic monthly & yearly generation** (1st of the following period)
- ⚙️ **Fully UI-configurable** via Config Flow + Options Flow
- ✍️ **Manual meter entry** — per meter; an input entity (`number.*`) and a consumption sensor (`sensor.*`) are created automatically, no YAML required
- 💰 **Cost calculation** with price per unit + monthly base fee
- 🎨 **Per-meter customization**: name, unit, icon/emoji, color
- 📁 **Reports served at** `/local/haushaltsdoku/`
- 🛠️ **Services** for monthly/yearly/range reports and adding manual readings
- 🌍 **Languages**: German, English (switchable in settings)
- 🌙 **Dark mode** automatic via `prefers-color-scheme`

## Requirements

The integration uses Home Assistant's **Long-Term Statistics**. Sensors must
have one of these `state_class` attributes:

- `total_increasing` — for cumulative meters that only go up (electricity,
  gas, water meters)
- `total` — for meters that can decrease (e.g. battery)
- `measurement` — works partially (no `change` value)

This is already correctly set for most Shelly, Tasmota, ESPHome, and
AI-on-the-edge integrations. For a manual `input_number`, wrap it with a
template sensor that has `state_class: total_increasing` — see
[Manual meters](#manual-meters) below.

## Installation

### Via HACS (recommended)

1. Open HACS → 3-dot menu → **Custom Repositories**
2. URL: `https://github.com/Lexorius/hacs-budget-book`, Category: **Integration**
3. Add → install → **restart Home Assistant**
4. Settings → Devices & Services → **Add Integration** → "Haushaltsdoku"

### Manual

```bash
cd /config
git clone https://github.com/Lexorius/hacs-budget-book
cp -r hacs-budget-book/custom_components/haushaltsdoku custom_components/
```

Then restart Home Assistant.

## Setup

When you add the integration, a wizard appears:

1. **Global settings** — output directory (default: `www/haushaltsdoku`),
   currency, **report language (DE/EN)**, auto-generation toggles
2. **Add meter** — name, entity, unit, optional price & base fee, icon
   (emoji), color (hex)
3. **Add another or finish** — repeat as needed

You can change anything later via **Configure** in the integration card
(add/remove meters, switch language, etc.).

## Viewing reports

After the first generation, browse to:

```
http://homeassistant.local:8123/local/haushaltsdoku/index.html
```

Tip: bookmark it or embed it as a webpage card in a Lovelace dashboard.

## Services

### `haushaltsdoku.generate_monthly_report`

```yaml
service: haushaltsdoku.generate_monthly_report
data:
  year: 2026
  month: 4
```

Without parameters: generates for the **current** month.

### `haushaltsdoku.generate_yearly_report`

```yaml
service: haushaltsdoku.generate_yearly_report
data:
  year: 2025
```

### `haushaltsdoku.generate_range_report`

```yaml
service: haushaltsdoku.generate_range_report
data:
  start: "2026-04-15 00:00:00"
  end:   "2026-04-30 23:59:59"
  title: "April vacation week"
```

### `haushaltsdoku.add_reading`

Add a new reading for a manual meter:

```yaml
service: haushaltsdoku.add_reading
data:
  meter_name: "Cold water"
  value: 1234.567
```

## Example automation: monthly notification

```yaml
automation:
  - alias: "Send monthly report"
    trigger:
      - platform: time
        at: "00:30:00"
    condition:
      - condition: template
        value_template: "{{ now().day == 1 }}"
    action:
      - service: haushaltsdoku.generate_monthly_report
      - delay: "00:00:30"
      - service: notify.mobile_app_your_phone
        data:
          title: "Consumption report ready"
          message: "{{ now().strftime('%B %Y') }} — tap to open"
          data:
            url: "/local/haushaltsdoku/index.html"
```

## Manual meters

When adding a meter in the wizard, tick **Manual meter**. No existing sensor
or template needed — Haushaltsdoku auto-creates:

- `number.haushaltsdoku_<name>_input` — the input field. Drop it in any
  Lovelace `entities` card to enter readings directly in the HA UI.
- `sensor.haushaltsdoku_<name>` — the consumption sensor (with
  `state_class: total_increasing` and proper `device_class`). Goes into
  long-term statistics automatically; usable in the Energy Dashboard and
  our reports.

Example Lovelace card for entry (on a dedicated "Meter readings" dashboard):

```yaml
type: entities
title: Enter meter readings
entities:
  - entity: number.haushaltsdoku_water_cold_input
    name: Cold water — new reading
  - entity: sensor.haushaltsdoku_water_cold
    name: current reading
    secondary_info: last-changed
  - entity: number.haushaltsdoku_electricity_main_input
  - entity: sensor.haushaltsdoku_electricity_main
```

### Entry via service / automation

From an automation or a notification action:

```yaml
service: haushaltsdoku.add_reading
data:
  meter_name: "Cold water"
  value: 1234.567
  # optional: timestamp: "2026-04-30 22:00:00"
```

Use `meter_name` (display name) or `meter_id` (internal UUID).

### Plausibility check

If a new reading is lower than the previous one, a warning is logged but the
entry is still stored (corner cases like meter replacements need that). Fix
incorrect values via *Developer Tools → Statistics → Adjust a statistic*.

## What the integration creates

- Sensor `sensor.haushaltsdoku_last_report` — shows the filename of the most
  recent report; attributes include `index_url`, `report_count`,
  `output_path`.

## Limitations / TODOs

- Print view is included, but **no automatic PDF export** — print to PDF via
  the browser. (An optional `weasyprint` path could be added.)
- Year-over-year comparison: not yet shown in the chart.
- No tariff splitting (peak/off-peak) — `utility_meter` supports it but it's
  not piped through here.

## Number formatting

Numbers are formatted according to the chosen report language:
- German: `1.234,56 kWh`
- English: `1,234.56 kWh`

Date formats:
- German: `Mo, 01.04.2026`
- English: `Mon, 2026-04-01`

## License

MIT — see LICENSE.
