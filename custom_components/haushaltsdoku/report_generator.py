"""HTML-Report-Generator mit eingebetteten SVG-Charts. Zweisprachig (DE/EN)."""
from __future__ import annotations

import html
import logging
import math
from calendar import monthrange
from datetime import datetime
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import homeassistant.util.dt as dt_util

from .const import (
    CONF_CURRENCY,
    CONF_LANGUAGE,
    CONF_METERS,
    CONF_METER_BASE_FEE,
    CONF_METER_COLOR,
    CONF_METER_ENTITY,
    CONF_METER_ICON,
    CONF_METER_NAME,
    CONF_METER_PRICE,
    CONF_METER_UNIT,
    DEFAULT_COLORS,
    DEFAULT_CURRENCY,
    DEFAULT_ICONS,
    DEFAULT_LANGUAGE,
)
from .coordinator import HaushaltsdokuCoordinator
from .i18n import (
    format_date_full,
    format_date_short,
    format_month_year,
    format_number,
    month_name,
    month_short,
    t,
)

_LOGGER = logging.getLogger(__name__)


def _meter_color(meter: dict[str, Any]) -> str:
    if meter.get(CONF_METER_COLOR):
        return meter[CONF_METER_COLOR]
    return DEFAULT_COLORS.get(meter.get(CONF_METER_UNIT, ""), "#6366f1")


def _meter_icon(meter: dict[str, Any]) -> str:
    if meter.get(CONF_METER_ICON):
        return meter[CONF_METER_ICON]
    return DEFAULT_ICONS.get(meter.get(CONF_METER_UNIT, ""), "📊")


class ReportGenerator:
    """Erzeugt HTML-Berichte. Sprache wird aus der Config-Entry gelesen."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: HaushaltsdokuCoordinator,
        output_path: Path,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self.output_path = output_path

    @property
    def currency(self) -> str:
        return self.entry.options.get(
            CONF_CURRENCY, self.entry.data.get(CONF_CURRENCY, DEFAULT_CURRENCY)
        )

    @property
    def lang(self) -> str:
        return self.entry.options.get(
            CONF_LANGUAGE, self.entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
        )

    def _fmt(self, value: float, digits: int = 2) -> str:
        return format_number(value, digits, self.lang)

    # ──────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────

    async def generate_monthly(self, year: int, month: int) -> Path:
        tz = dt_util.DEFAULT_TIME_ZONE
        start = datetime(year, month, 1, tzinfo=tz)
        last_day = monthrange(year, month)[1]
        end = datetime(year, month, last_day, 23, 59, 59, tzinfo=tz)

        title = (
            f"{t(self.lang, 'monthly_report')} — "
            f"{month_name(self.lang, month)} {year}"
        )
        sections = []
        meter_summaries = []

        for meter in self.coordinator.meters:
            data = await self.coordinator.async_get_consumption(
                meter[CONF_METER_ENTITY], start, end, period="day"
            )
            total = sum(r["change"] for r in data)
            cost = self._calc_cost(meter, total, days=last_day)
            meter_summaries.append((meter, total, cost))
            sections.append(self._render_meter_section(meter, data, total, cost, "day"))

        body = self._render_summary_grid(meter_summaries) + "\n".join(sections)
        html_content = self._wrap_page(title, body, year=year, month=month)

        filename = f"{year:04d}-{month:02d}.html"
        path = self.output_path / filename
        await self.hass.async_add_executor_job(path.write_text, html_content, "utf-8")

        await self._regenerate_index()
        _LOGGER.info("Monthly report created: %s", path)
        return path

    async def generate_yearly(self, year: int) -> Path:
        tz = dt_util.DEFAULT_TIME_ZONE
        start = datetime(year, 1, 1, tzinfo=tz)
        end = datetime(year, 12, 31, 23, 59, 59, tzinfo=tz)

        title = f"{t(self.lang, 'yearly_report')} — {year}"
        sections = []
        meter_summaries = []

        for meter in self.coordinator.meters:
            data = await self.coordinator.async_get_consumption(
                meter[CONF_METER_ENTITY], start, end, period="month"
            )
            total = sum(r["change"] for r in data)
            cost = self._calc_cost(meter, total, days=365)
            meter_summaries.append((meter, total, cost))
            sections.append(self._render_meter_section(meter, data, total, cost, "month"))

        body = self._render_summary_grid(meter_summaries) + "\n".join(sections)
        html_content = self._wrap_page(title, body, year=year)

        filename = f"{year:04d}.html"
        path = self.output_path / filename
        await self.hass.async_add_executor_job(path.write_text, html_content, "utf-8")

        await self._regenerate_index()
        _LOGGER.info("Yearly report created: %s", path)
        return path

    async def generate_range(
        self, start: datetime, end: datetime, title: str | None = None
    ) -> Path:
        if start.tzinfo is None:
            start = start.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        if end.tzinfo is None:
            end = end.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)

        days = max(1, (end - start).days)
        period = "day" if days <= 90 else "month"
        if not title:
            title = (
                f"{t(self.lang, 'report')} "
                f"{format_date_short(self.lang, start)} – "
                f"{format_date_short(self.lang, end)}"
            )

        sections = []
        meter_summaries = []
        for meter in self.coordinator.meters:
            data = await self.coordinator.async_get_consumption(
                meter[CONF_METER_ENTITY], start, end, period=period
            )
            total = sum(r["change"] for r in data)
            cost = self._calc_cost(meter, total, days=days)
            meter_summaries.append((meter, total, cost))
            sections.append(self._render_meter_section(meter, data, total, cost, period))

        body = self._render_summary_grid(meter_summaries) + "\n".join(sections)
        html_content = self._wrap_page(title, body)

        slug = f"range-{start.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}.html"
        path = self.output_path / slug
        await self.hass.async_add_executor_job(path.write_text, html_content, "utf-8")

        await self._regenerate_index()
        return path

    # ──────────────────────────────────────────────────────────
    # Cost helper
    # ──────────────────────────────────────────────────────────

    def _calc_cost(
        self, meter: dict[str, Any], total: float, days: int
    ) -> float | None:
        price = meter.get(CONF_METER_PRICE)
        if price is None:
            return None
        base_fee_monthly = meter.get(CONF_METER_BASE_FEE) or 0
        base = base_fee_monthly * (days / 30.0)
        return float(price) * total + base

    # ──────────────────────────────────────────────────────────
    # Rendering
    # ──────────────────────────────────────────────────────────

    def _render_summary_grid(
        self, summaries: list[tuple[dict, float, float | None]]
    ) -> str:
        cards = []
        for meter, total, cost in summaries:
            color = _meter_color(meter)
            icon = _meter_icon(meter)
            unit = html.escape(meter.get(CONF_METER_UNIT, ""))
            name = html.escape(meter.get(CONF_METER_NAME, ""))
            cost_html = (
                f'<div class="summary-cost">{self._fmt(cost)} {self.currency}</div>'
                if cost is not None
                else ""
            )
            cards.append(
                f'''
<div class="summary-card" style="--accent:{color}">
  <div class="summary-icon">{icon}</div>
  <div class="summary-name">{name}</div>
  <div class="summary-value">{self._fmt(total, 2)} <span class="unit">{unit}</span></div>
  {cost_html}
</div>'''
            )
        return f'<section class="summary-grid">{"".join(cards)}</section>'

    def _render_meter_section(
        self,
        meter: dict[str, Any],
        data: list[dict],
        total: float,
        cost: float | None,
        period: str,
    ) -> str:
        color = _meter_color(meter)
        icon = _meter_icon(meter)
        name = html.escape(meter.get(CONF_METER_NAME, ""))
        unit = html.escape(meter.get(CONF_METER_UNIT, ""))
        entity = html.escape(meter.get(CONF_METER_ENTITY, ""))

        chart = self._render_bar_chart(data, color, period, unit)
        table = self._render_table(data, period, unit)

        avg = total / len(data) if data else 0
        max_row = max(data, key=lambda r: r["change"], default=None)
        max_str = ""
        if max_row:
            max_str = (
                f'{self._fmt(max_row["change"])} {unit} '
                f'{t(self.lang, "on_date")} {format_date_short(self.lang, max_row["start"])}'
            )

        avg_label = (
            t(self.lang, "average_per_day")
            if period == "day"
            else t(self.lang, "average_per_month")
        )

        cost_row = ""
        if cost is not None:
            cost_row = (
                f'<div class="stat"><span>{t(self.lang, "cost")}</span>'
                f'<strong>{self._fmt(cost)} {self.currency}</strong></div>'
            )

        return f'''
<section class="meter-section" style="--accent:{color}">
  <header class="meter-header">
    <div class="meter-title">
      <span class="meter-icon">{icon}</span>
      <h2>{name}</h2>
    </div>
    <code class="entity-id">{entity}</code>
  </header>

  <div class="stats-row">
    <div class="stat"><span>{t(self.lang, "total")}</span><strong>{self._fmt(total)} {unit}</strong></div>
    <div class="stat"><span>{avg_label}</span><strong>{self._fmt(avg)} {unit}</strong></div>
    <div class="stat"><span>{t(self.lang, "peak")}</span><strong>{max_str}</strong></div>
    {cost_row}
  </div>

  {chart}
  {table}
</section>'''

    def _render_bar_chart(
        self, data: list[dict], color: str, period: str, unit: str
    ) -> str:
        if not data:
            return f'<div class="empty">{t(self.lang, "no_data")}</div>'

        width = 880
        height = 280
        pad_left = 56
        pad_right = 16
        pad_top = 24
        pad_bottom = 48
        chart_w = width - pad_left - pad_right
        chart_h = height - pad_top - pad_bottom

        max_val = max((r["change"] for r in data), default=0) or 1
        nice_max = _nice_ceil(max_val)
        bar_w = chart_w / len(data)

        bars = []
        labels = []
        for i, row in enumerate(data):
            v = row["change"]
            h = (v / nice_max) * chart_h if nice_max > 0 else 0
            x = pad_left + i * bar_w
            y = pad_top + chart_h - h
            bw = max(1, bar_w - 2)
            bars.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" '
                f'rx="2" fill="{color}" opacity="0.85">'
                f'<title>{self._fmt(v)} {unit}</title></rect>'
            )

            show_label = (
                period == "month"
                or (i % max(1, len(data) // 10) == 0)
                or i == len(data) - 1
            )
            if show_label:
                if period == "day":
                    label = format_date_short(self.lang, row["start"])
                else:
                    label = month_short(self.lang, row["start"].month)
                labels.append(
                    f'<text x="{x + bw/2:.1f}" y="{pad_top + chart_h + 16}" '
                    f'class="x-label" text-anchor="middle">{label}</text>'
                )

        y_ticks = []
        for i in range(5):
            v = nice_max * i / 4
            y = pad_top + chart_h - (v / nice_max) * chart_h
            y_ticks.append(
                f'<line x1="{pad_left}" y1="{y:.1f}" x2="{width - pad_right}" '
                f'y2="{y:.1f}" class="grid"/>'
            )
            y_ticks.append(
                f'<text x="{pad_left - 8}" y="{y + 4:.1f}" class="y-label" '
                f'text-anchor="end">'
                f'{self._fmt(v, 1 if nice_max < 10 else 0)}</text>'
            )

        axis_title = f"{t(self.lang, 'consumption')} ({unit})"
        return f'''
<div class="chart-wrap">
<svg viewBox="0 0 {width} {height}" class="chart" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{axis_title}">
  <style>
    .chart {{ font-family: inherit; width: 100%; height: auto; }}
    .grid {{ stroke: var(--grid); stroke-width: 1; }}
    .x-label, .y-label {{ font-size: 11px; fill: var(--muted); }}
    .axis-title {{ font-size: 12px; fill: var(--muted); font-weight: 600; }}
  </style>
  {''.join(y_ticks)}
  {''.join(bars)}
  {''.join(labels)}
  <text x="{pad_left}" y="{pad_top - 8}" class="axis-title">{axis_title}</text>
</svg>
</div>'''

    def _render_table(self, data: list[dict], period: str, unit: str) -> str:
        if not data:
            return ""
        rows = []
        for row in data:
            if period == "day":
                label = format_date_full(self.lang, row["start"])
            else:
                label = format_month_year(self.lang, row["start"])
            rows.append(
                f'<tr><td>{label}</td><td class="num">{self._fmt(row["change"])} {unit}</td></tr>'
            )
        col_label = t(self.lang, "day") if period == "day" else t(self.lang, "month")
        return f'''
<details class="data-table">
  <summary>{t(self.lang, "data_table")} ({len(data)} {t(self.lang, "entries")})</summary>
  <table>
    <thead><tr><th>{col_label}</th><th>{t(self.lang, "consumption")}</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</details>'''

    # ──────────────────────────────────────────────────────────
    # Page Wrapper
    # ──────────────────────────────────────────────────────────

    def _wrap_page(
        self, title: str, body: str, year: int | None = None, month: int | None = None
    ) -> str:
        nav = self._render_nav(year=year, month=month)
        now = datetime.now()
        generated = format_date_full(self.lang, now) + " " + now.strftime("%H:%M")
        return f'''<!DOCTYPE html>
<html lang="{t(self.lang, "html_lang")}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} — Haushaltsdoku</title>
<style>{_CSS}</style>
</head>
<body>
<div class="page">
  <header class="page-header">
    <div class="brand">
      <span class="brand-mark">⌂</span>
      <div>
        <div class="brand-name">Haushaltsdoku</div>
        <div class="brand-sub">{t(self.lang, "brand_subtitle")}</div>
      </div>
    </div>
    <div class="generated">{t(self.lang, "generated_on")} {generated}</div>
  </header>

  <h1 class="page-title">{html.escape(title)}</h1>
  {nav}

  <main>
    {body}
  </main>

  <footer class="page-footer">
    <p>{t(self.lang, "footer")}</p>
  </footer>
</div>
</body>
</html>'''

    def _render_nav(self, year: int | None, month: int | None) -> str:
        if year is None:
            return (
                f'<nav class="page-nav">'
                f'<a href="index.html">{t(self.lang, "back_to_overview")}</a>'
                f'</nav>'
            )

        prev_arrow = t(self.lang, "prev_arrow")
        next_arrow = t(self.lang, "next_arrow")
        links = [f'<a href="index.html">{t(self.lang, "overview")}</a>']

        if month is not None:
            prev_y, prev_m = (year, month - 1) if month > 1 else (year - 1, 12)
            next_y, next_m = (year, month + 1) if month < 12 else (year + 1, 1)
            links.append(
                f'<a href="{prev_y:04d}-{prev_m:02d}.html">'
                f'{prev_arrow} {month_name(self.lang, prev_m)} {prev_y}</a>'
            )
            links.append(f'<a href="{year:04d}.html">{t(self.lang, "year")} {year}</a>')
            links.append(
                f'<a href="{next_y:04d}-{next_m:02d}.html">'
                f'{month_name(self.lang, next_m)} {next_y} {next_arrow}</a>'
            )
        else:
            links.append(f'<a href="{year-1:04d}.html">{prev_arrow} {year-1}</a>')
            links.append(f'<a href="{year+1:04d}.html">{year+1} {next_arrow}</a>')
        return f'<nav class="page-nav">{" · ".join(links)}</nav>'

    # ──────────────────────────────────────────────────────────
    # Index page
    # ──────────────────────────────────────────────────────────

    async def _regenerate_index(self) -> None:
        files = sorted(
            [p for p in self.output_path.glob("*.html") if p.name != "index.html"],
            reverse=True,
        )
        monthly = []
        yearly = []
        ranges = []
        for f in files:
            stem = f.stem
            if stem.startswith("range-"):
                ranges.append(f)
            elif "-" in stem and len(stem) == 7:  # YYYY-MM
                monthly.append(f)
            elif len(stem) == 4 and stem.isdigit():
                yearly.append(f)

        def _link(f: Path, label: str) -> str:
            return f'<li><a href="{f.name}">{label}</a></li>'

        monthly_html = "".join(
            _link(
                f,
                f"{month_name(self.lang, int(f.stem.split('-')[1]))} "
                f"{f.stem.split('-')[0]}",
            )
            for f in monthly
        )
        yearly_html = "".join(_link(f, f.stem) for f in yearly)
        ranges_html = "".join(
            _link(f, f.stem.replace("range-", "")) for f in ranges
        )

        sections = []
        if yearly_html:
            sections.append(
                f'<section><h2>{t(self.lang, "yearly_reports")}</h2>'
                f'<ul>{yearly_html}</ul></section>'
            )
        if monthly_html:
            sections.append(
                f'<section><h2>{t(self.lang, "monthly_reports")}</h2>'
                f'<ul>{monthly_html}</ul></section>'
            )
        if ranges_html:
            sections.append(
                f'<section><h2>{t(self.lang, "custom_ranges")}</h2>'
                f'<ul>{ranges_html}</ul></section>'
            )

        body = "\n".join(sections) or f'<p>{t(self.lang, "no_reports_yet")}</p>'
        html_content = self._wrap_page(t(self.lang, "overview"), body)
        path = self.output_path / "index.html"
        await self.hass.async_add_executor_job(path.write_text, html_content, "utf-8")


def _nice_ceil(value: float) -> float:
    if value <= 0:
        return 1
    exp = math.floor(math.log10(value))
    base = 10 ** exp
    for m in (1, 2, 2.5, 5, 10):
        if value <= m * base:
            return m * base
    return 10 * base


_CSS = """
:root {
  --bg: #f7f8fb;
  --card: #ffffff;
  --text: #0f172a;
  --muted: #64748b;
  --border: #e2e8f0;
  --grid: #eef2f7;
  --accent: #6366f1;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0b1020;
    --card: #131a2e;
    --text: #e6ecff;
    --muted: #8a94b1;
    --border: #243049;
    --grid: #1c2640;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.55;
}
.page { max-width: 960px; margin: 0 auto; padding: 32px 24px 64px; }
.page-header {
  display: flex; justify-content: space-between; align-items: center;
  border-bottom: 1px solid var(--border); padding-bottom: 16px; margin-bottom: 24px;
}
.brand { display: flex; align-items: center; gap: 12px; }
.brand-mark {
  display: inline-flex; align-items: center; justify-content: center;
  width: 36px; height: 36px; border-radius: 8px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white; font-size: 20px; font-weight: 700;
}
.brand-name { font-weight: 700; font-size: 16px; }
.brand-sub { color: var(--muted); font-size: 12px; }
.generated { color: var(--muted); font-size: 13px; }
.page-title { font-size: 28px; margin: 8px 0 16px; }
.page-nav {
  display: flex; gap: 12px; flex-wrap: wrap;
  padding: 12px 16px; background: var(--card); border: 1px solid var(--border);
  border-radius: 10px; margin-bottom: 28px; font-size: 14px;
}
.page-nav a { color: var(--accent); text-decoration: none; }
.page-nav a:hover { text-decoration: underline; }

.summary-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px; margin-bottom: 32px;
}
.summary-card {
  background: var(--card); border: 1px solid var(--border); border-radius: 12px;
  padding: 18px; position: relative; overflow: hidden;
}
.summary-card::before {
  content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
  background: var(--accent);
}
.summary-icon { font-size: 22px; margin-bottom: 4px; }
.summary-name { font-size: 13px; color: var(--muted); margin-bottom: 8px; }
.summary-value { font-size: 22px; font-weight: 700; }
.summary-value .unit { font-size: 14px; font-weight: 400; color: var(--muted); }
.summary-cost { margin-top: 4px; color: var(--muted); font-size: 14px; }

.meter-section {
  background: var(--card); border: 1px solid var(--border); border-radius: 14px;
  padding: 24px; margin-bottom: 24px;
}
.meter-header {
  display: flex; justify-content: space-between; align-items: flex-start;
  gap: 12px; margin-bottom: 16px; flex-wrap: wrap;
}
.meter-title { display: flex; align-items: center; gap: 10px; }
.meter-title h2 { margin: 0; font-size: 20px; }
.meter-icon { font-size: 24px; }
.entity-id {
  font-size: 12px; color: var(--muted); background: var(--bg);
  padding: 4px 8px; border-radius: 6px; border: 1px solid var(--border);
}
.stats-row {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px; margin-bottom: 20px;
  padding: 14px; background: var(--bg); border-radius: 10px;
}
.stat { display: flex; flex-direction: column; gap: 2px; }
.stat span { font-size: 12px; color: var(--muted); }
.stat strong { font-size: 16px; }

.chart-wrap { margin: 20px 0; }
.empty { padding: 40px; text-align: center; color: var(--muted); }

.data-table { margin-top: 16px; }
.data-table summary {
  cursor: pointer; padding: 8px 12px; background: var(--bg);
  border-radius: 8px; font-size: 14px; color: var(--muted);
}
.data-table summary:hover { color: var(--text); }
.data-table table {
  width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 14px;
}
.data-table th, .data-table td {
  padding: 8px 12px; text-align: left; border-bottom: 1px solid var(--border);
}
.data-table th { color: var(--muted); font-weight: 500; }
.data-table td.num { text-align: right; font-variant-numeric: tabular-nums; }

.page-footer {
  margin-top: 48px; padding-top: 16px; border-top: 1px solid var(--border);
  color: var(--muted); font-size: 12px; text-align: center;
}

ul { list-style: none; padding: 0; }
ul li { padding: 8px 0; border-bottom: 1px solid var(--border); }
ul li a { color: var(--accent); text-decoration: none; font-size: 15px; }
ul li a:hover { text-decoration: underline; }

@media print {
  body { background: white; }
  .page-nav, .data-table { display: none; }
  .meter-section, .summary-card { break-inside: avoid; }
}
"""
