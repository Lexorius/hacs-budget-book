# Changelog

Alle nennenswerten Änderungen werden hier dokumentiert.
Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionierung nach [Semantic Versioning](https://semver.org/lang/de/).

## [0.2.1] — 2026-05-01

### Geändert
- Author auf [Lexorius](https://github.com/Lexorius) (Thomas Kloppholz) gesetzt
- Repository-URLs in `manifest.json` und READMEs auf
  `https://github.com/Lexorius/hacs-budget-book` aktualisiert
- LICENSE: Copyright-Holder auf Thomas Kloppholz (Lexorius)
- Hinweis in beiden READMEs ergänzt, dass Repo-Name (`hacs-budget-book`)
  und Integration-Domain (`haushaltsdoku`) bewusst unterschiedlich sind

## [0.2.0] — 2026-05-01

### Hinzugefügt
- **Manuelle Zähler**: Beim Hinzufügen wählbar zwischen *automatisch*
  (vorhandener Sensor) und *manuell*
- Bei manuellen Zählern werden automatisch erstellt:
  - `number.haushaltsdoku_<name>_input` — Eingabefeld in Lovelace
  - `sensor.haushaltsdoku_<name>` — Verbrauchssensor mit
    `state_class: total_increasing` und passender `device_class`
- Service `haushaltsdoku.add_reading` für programmatische Eingabe
  (z.B. aus Push-Notification-Action)
- Persistente History aller Eingaben mit Zeitstempel
  (`.storage/haushaltsdoku.<entry>.readings`)
- Sensor-Attribute `recent_readings`, `reading_count`, `last_reading_at`
- Plausibilitätswarnung im Log, wenn neuer Stand kleiner als letzter

### Geändert
- Config-Flow: separate Schritte für `meter_auto` und `meter_manual`
- Translations (DE/EN) um neue Schritte erweitert

## [0.1.0] — 2026-05-01

### Hinzugefügt
- Initiale Version
- HTML-Berichte (Monat / Jahr / freier Zeitraum) mit eingebetteten SVG-Charts
- Auto-Generierung am 1. des Folgemonats / -jahres
- Config-Flow + Options-Flow mit Multi-Zähler-Setup
- Kostenkalkulation mit Preis pro Einheit + Grundgebühr
- Druckfähiges Layout, Dark-Mode via `prefers-color-scheme`
- Zweisprachig (DE/EN) für UI und Berichte
- Status-Sensor `sensor.haushaltsdoku_letzter_bericht`
- Services: `generate_monthly_report`, `generate_yearly_report`,
  `generate_range_report`
