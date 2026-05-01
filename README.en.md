# Haushaltsdoku — Consumption Reports for Home Assistant

🇬🇧 English · [🇩🇪 Deutsch](README.md)

A HACS-compatible custom integration that turns your sensor data into
**printable HTML consumption reports** — monthly and yearly, with summary
cards, SVG charts, data tables, cost calculation, and dark mode. No external
dependencies, no JavaScript, fully self-contained.

## Features

- 📊 **HTML reports with embedded SVG charts** — printable, no JS required
- 🗓️ **Automatic monthly & yearly generation** (1st of the following period)
- ⚙️ **Fully UI-configurable** via Config Flow + Options Flow
- 💰 **Cost calculation** with price per unit + monthly base fee
- 🎨 **Per-meter customization**: name, unit, icon/emoji, color
- 📁 **Reports served at** `/local/haushaltsdoku/`
- 🛠️ **Services** for monthly, yearly, and custom date ranges
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
2. URL: `https://github.com/yourname/haushaltsdoku`, Category: **Integration**
3. Add → install → **restart Home Assistant**
4. Settings → Devices & Services → **Add Integration** → "Haushaltsdoku"

### Manual

```bash
cd /config
git clone https://github.com/yourname/haushaltsdoku
cp -r haushaltsdoku/custom_components/haushaltsdoku custom_components/
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

If you read your meters by hand:

```yaml
# configuration.yaml
input_number:
  water_cold:
    name: "Cold water — reading in m³"
    min: 0
    max: 100000
    step: 0.001
    mode: box

template:
  - sensor:
      - name: "Water meter cold"
        unit_of_measurement: "m³"
        device_class: water
        state_class: total_increasing
        state: "{{ states('input_number.water_cold') | float(0) }}"
```

Then add `sensor.water_meter_cold` as a meter in Haushaltsdoku.

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
