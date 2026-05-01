# Changelog

Alle nennenswerten Änderungen werden hier dokumentiert.
Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
Versionierung nach [Semantic Versioning](https://semver.org/lang/de/).

## [0.2.12] — 2026-05-01

### Geändert
- Re-Release der Inhalte aus 0.2.11 unter neuer Versionsnummer, nachdem
  der Tag `v0.2.11` ohne den dazugehörigen manifest-Bump auf GitHub gepusht
  worden war. Inhaltlich identisch zu 0.2.11.

## [0.2.11] — 2026-05-01

### Behoben
- **Config-Flow lädt nicht** (eigentlicher Fehler aus dem Stack-Trace):
  `voluptuous.error.MultipleInvalid: not a valid value for dictionary
  value @ data['step']` — `NumberSelectorConfig` validiert `step` strenger:
  Werte müssen entweder `"any"` sein oder mindestens `0.001`. Drei
  Stellen mit `step=0.0001` auf `step="any"` umgestellt (für Preise,
  Step-Konfiguration und manuellen Zähler-Step).
- `number.py` clampt `_attr_native_step` defensiv auf minimum `0.001`,
  damit eine versehentlich zu kleine Konfigurations-Eingabe nicht zur
  Laufzeit Folge-Validierungsfehler auslöst.

## [0.2.10] — 2026-05-01

### Behoben
- **Config-Flow lädt nicht** in HA 2025.x (`Exception importing
  custom_components.haushaltsdoku.config_flow`):
  - `FlowResult`-Import aus `homeassistant.data_entry_flow` in einen
    `TYPE_CHECKING`-Block verschoben. In HA 2024.10+ wurde der Typ durch
    `ConfigFlowResult` in `homeassistant.config_entries` ersetzt;
    der alte Import bleibt als Fallback.
  - `OptionsFlow.__init__` setzt `self.config_entry` nicht mehr selbst.
    In HA 2025.x ist `config_entry` ein Property der `OptionsFlow`-Klasse
    und das eigene Setzen wirft `AttributeError`. Der Wert wird vom Parent
    automatisch befüllt.

## [0.2.9] — 2026-05-01

### Behoben
- Alle 14 ruff-Errors aus `validate.yml`:
  - **I001** (10×): Imports in `__init__.py`, `config_flow.py`,
    `coordinator.py`, `report_generator.py`, `storage.py` durch
    `ruff --fix` automatisch sortiert
  - **F401** (4×): unbenutzte Imports entfernt — `homeassistant.config_entries`
    in `config_flow.py`, `CONF_METER_ENTITY` in `coordinator.py`,
    `CONF_METERS` in `report_generator.py`, `CONF_METER_ICON` in
    `sensor.py`, `field` in `storage.py`
  - **E501** (4×): zu lange Zeilen umgebrochen
    - `i18n.py`: Footer-Strings (DE+EN) als verkettete Literale
    - `report_generator.py`: stats-row mit jedem `<div class="stat">` auf
      mehreren Zeilen, SVG-Tag-Attribute aufgeteilt

### Geändert
- HTML-Output durch das Aufbrechen der stats-row jetzt etwas ausführlicher
  formatiert — semantisch identisch, optisch unverändert

## [0.2.8] — 2026-05-01

### Behoben
- `Permission denied` bei `./scripts/check-manifest.sh` im CI: Workflow ruft
  Scripts jetzt explizit über `bash scripts/...` auf — damit ist das
  Execute-Bit egal
- README-Hinweis ergänzt, wie das Mode-Bit persistent ins Git-Tree gesetzt
  wird (`git update-index --chmod=+x scripts/*.sh`), damit lokales Ausführen
  ohne `bash`-Präfix funktioniert

## [0.2.7] — 2026-05-01

### Behoben
- HACS-Validation-Fehler `Validation topics failed` und `Validation
  description failed`: beide Checks beziehen sich auf das GitHub-Repo
  selbst (nicht auf den Code) und werden in der CI-Pipeline jetzt
  ignoriert — `ignore: brands topics description`
- Empfehlung in der README ergänzt, beide Werte direkt auf GitHub zu
  setzen (Repo-Seite → Zahnrad neben "About")

## [0.2.6] — 2026-05-01

### Behoben
- hassfest-Fehler `Manifest keys are not sorted correctly`:
  `manifest.json` ist jetzt korrekt sortiert (`domain`, `name`, dann
  alphabetisch — wie hassfest es verlangt)

### Hinzugefügt
- `scripts/check-manifest.sh` — lokaler Schnell-Check für Pflichtkeys und
  Key-Reihenfolge. Wird auch im `validate.yml`-Workflow ausgeführt, damit
  das Problem nicht erst bei hassfest in CI auffällt
- `bump-version.sh` sortiert beim Bump die manifest-Keys automatisch
  hassfest-konform

## [0.2.5] — 2026-05-01

### Geändert
- **Release-Prozess vereinfacht und robuster gemacht**:
  - HACS-Validation in CI ignoriert jetzt den `brands`-Check (Custom-Repo,
    kein Icon im `home-assistant/brands` hinterlegt — gewollt)
  - HACS-Default-Registry-Check wird ohnehin nicht ausgeführt (würde nur
    bei einem PR im `hacs/default` Repo greifen) — keine Aktion nötig
  - `validate.yml` umstrukturiert: drei klar getrennte Jobs (hassfest /
    hacs / python), wöchentlicher Cron entfernt
  - `release.yml` schlanker: weniger Schritte, identischer Output
- `bump-version.sh` unterstützt jetzt `--release`-Flag — macht in einem
  Rutsch Bump + Commit + Tag + Push (mit Pause zum CHANGELOG-Ausfüllen)

## [0.2.4] — 2026-05-01

### Behoben
- HACS-Download schlug fehl: `zip_release: true` aus `hacs.json` entfernt.
  Damit installiert HACS den Quellbaum direkt vom Tag — funktioniert auch
  ohne erfolgreichen Release-Workflow. (Wer Release-Assets bevorzugt,
  kann später beide Felder wieder reinnehmen.)

## [0.2.3] — 2026-05-01

### Behoben
- "Invalid handler specified" beim Laden des Config-Flows: `integration_type`
  in `manifest.json` von `service` (Cloud-Services) auf `helper` korrigiert
  — letzteres ist der korrekte Typ für lokal-rechnende Custom-Integrationen
- Cross-Plattform-Import (`from .number import _slug` in `sensor.py`)
  beseitigt; verhindert potenzielle Lade-Reihenfolge-Probleme bei HA-Setup.
  Slugify-Logik ist jetzt in `helpers.py`
- Defensive Behandlung der `statistics_during_period`-Signatur — fängt
  `TypeError` bei API-Änderungen zwischen HA-Versionen ab und versucht
  Fallback-Aufrufe statt komplett zu scheitern
- Unbenutzter `i18n`-Import in `config_flow.py` entfernt

### Geändert
- Neues `helpers.py` Modul mit `slugify_name()` als zentraler Slug-Funktion

## [0.2.2] — 2026-05-01

### Hinzugefügt
- GitHub-Workflow `validate.yml`: Hassfest, HACS-Validation, Python-Lint
  (ruff), JSON/YAML-Validierung, Versions-Konsistenzcheck (manifest ↔
  CHANGELOG)
- GitHub-Workflow `release.yml`: bei Tag `v*` wird automatisch ein Release
  mit `haushaltsdoku.zip` als Asset erzeugt; Release-Notes werden aus dem
  CHANGELOG extrahiert
- Lokales Build-Script `scripts/build.sh` mit identischem Output zum
  CI-Build
- Versions-Bump-Script `scripts/bump-version.sh` mit `patch`/`minor`/
  `major`-Modi und automatischem CHANGELOG-Eintrag
- Issue-Templates für Bug-Reports und Feature-Requests
- `.gitignore` für Python/Build-Artefakte/IDE-Files

### Geändert
- Release-ZIP jetzt HACS-konform: Inhalt von `custom_components/haushaltsdoku/`
  liegt direkt im ZIP-Root (statt mit `custom_components/<domain>/` Wrapper)

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
