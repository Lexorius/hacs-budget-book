# Haushaltsdoku — Verbrauchsberichte für Home Assistant

🇩🇪 Deutsch · [🇬🇧 English](README.en.md)

Eine HACS-kompatible Custom Integration, die aus deinen Sensor-Daten automatisch
**HTML-Verbrauchsberichte pro Monat und Jahr** erzeugt — mit Zusammenfassung,
SVG-Charts, Datentabelle, Kostenkalkulation und druckfähigem Layout. Dunkel- und
Helldarstellung wird automatisch erkannt. Berichte sind in **Deutsch oder
Englisch** generierbar.

> **Hinweis:** Das Repository heißt `hacs-budget-book`, die Integration in HA
> registriert sich aber unter dem Domain-Namen `haushaltsdoku` — das ist
> Absicht und ändert nichts an der Funktionalität.

**Autor:** [Lexorius](https://github.com/Lexorius) (Thomas Kloppholz)

📋 Versionshistorie: siehe [CHANGELOG.md](CHANGELOG.md)

![Berichts-Beispiel](docs/screenshot.png)

## Features

- 📊 **HTML-Berichte mit eingebetteten SVG-Charts** — keine externen Dependencies, kein JavaScript, druckbar
- 🗓️ **Automatische monatliche & jährliche Generierung** (jeweils am 1. des Folgezeitraums)
- ⚙️ **Komplett über die UI konfigurierbar** — Config Flow + Options Flow
- ✍️ **Manuelle Zähler-Eingabe** — pro Zähler wählbar; Eingabe-Entity (`number.*`) und Verbrauchssensor (`sensor.*`) werden automatisch erstellt, kein YAML-Bastelei nötig
- 💰 **Kostenkalkulation** mit Preis pro Einheit + monatlicher Grundgebühr
- 🎨 **Pro Zähler anpassbar**: Name, Einheit, Icon/Emoji, Farbe
- 📁 **Berichte direkt erreichbar** unter `/local/haushaltsdoku/`
- 🛠️ **Services** für manuelle Generierung & Eintrag von Zählerständen
- 🌍 **Sprachen**: Deutsch, Englisch (umschaltbar in den Einstellungen)
- 🌙 **Dark Mode** automatisch (via `prefers-color-scheme`)

## Voraussetzungen

Die Integration nutzt die **Long-Term Statistics** von Home Assistant. Damit ein
Sensor verwendbar ist, muss er eines dieser Attribute haben:

- `state_class: total_increasing` — für klassische Verbrauchszähler (Strom-, Gas-, Wasserzähler, die immer nur steigen)
- `state_class: total` — für Zähler, die auch sinken können
- `state_class: measurement` — funktioniert eingeschränkt (kein „change"-Wert)

Das ist bei Sensoren von Shelly, Tasmota, ESPHome, AI-on-the-edge usw. fast
immer schon korrekt gesetzt. Bei einem **manuell gepflegten** `input_number`
musst du einen Template-Sensor mit `state_class: total_increasing` darüber
legen — siehe [Manuelle Zähler](#manuelle-zähler).

## Installation

### Via HACS (empfohlen)

1. HACS öffnen → drei Punkte oben rechts → **Custom Repositories**
2. URL: `https://github.com/Lexorius/hacs-budget-book`, Kategorie: **Integration**
3. Hinzufügen → installieren → **Home Assistant neu starten**
4. Einstellungen → Geräte & Dienste → **Integration hinzufügen** → "Haushaltsdoku"

### Manuell

```bash
cd /config
git clone https://github.com/Lexorius/hacs-budget-book
cp -r hacs-budget-book/custom_components/haushaltsdoku custom_components/
```

dann Home Assistant neu starten.

## Einrichtung

Beim Hinzufügen der Integration kommt ein Wizard:

1. **Globale Einstellungen** — Ausgabeverzeichnis (Default: `www/haushaltsdoku`),
   Währung, **Sprache (DE/EN)**, Auto-Generierung an/aus
2. **Zähler hinzufügen** — Name, Entity, Einheit, optional Preis & Grundgebühr,
   Icon (Emoji), Farbe (Hex)
3. **Weiteren Zähler oder fertig** — beliebig wiederholbar

Später jederzeit über **Konfigurieren** anpassbar (Zähler hinzufügen /
entfernen, globale Einstellungen ändern).

## Berichte aufrufen

Nach der ersten Generierung erreichbar unter:

```
http://homeassistant.local:8123/local/haushaltsdoku/index.html
```

Tipp: leg dir das als Webseite in einem Lovelace-Dashboard ab oder als
Lesezeichen.

## Services

Drei Services stehen bereit:

### `haushaltsdoku.generate_monthly_report`

```yaml
service: haushaltsdoku.generate_monthly_report
data:
  year: 2026
  month: 4
```

Ohne Parameter wird der **aktuelle** Monat erzeugt.

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
  title: "Urlaubswoche April"
```

### `haushaltsdoku.add_reading`

Trägt für einen manuellen Zähler einen neuen Stand ein:

```yaml
service: haushaltsdoku.add_reading
data:
  meter_name: "Wasser kalt"
  value: 1234.567
```

## Beispielautomation: Monatlicher Push mit Bericht

```yaml
automation:
  - alias: "Monatsbericht senden"
    trigger:
      - platform: time
        at: "00:30:00"
    condition:
      - condition: template
        value_template: "{{ now().day == 1 }}"
    action:
      - service: haushaltsdoku.generate_monthly_report
      - delay: "00:00:30"
      - service: notify.mobile_app_dein_handy
        data:
          title: "Verbrauchsbericht ist fertig"
          message: "{{ now().strftime('%B %Y') }} — Tippe zum Öffnen"
          data:
            url: "/local/haushaltsdoku/index.html"
```

## Manuelle Zähler

Beim Hinzufügen eines Zählers im Wizard kannst du **Manueller Zähler** anhaken.
Dann brauchst du keinen vorhandenen Sensor und keinen Template-Sensor —
Haushaltsdoku erstellt automatisch:

- `number.haushaltsdoku_<name>_input` — das Eingabefeld (Zahl). Diese
  Entity in einer normalen Lovelace `entities`-Karte ablegen, fertig: das
  Eintragen passiert direkt in der HA-UI.
- `sensor.haushaltsdoku_<name>` — der Verbrauchszähler (mit
  `state_class: total_increasing` und passender `device_class`). Wird
  automatisch in den Long-Term-Statistics erfasst und ist im Energie-Dashboard
  sowie in unseren Berichten verwendbar.

Beispiel-Lovelace-Karte für die Eingabe (auf einem dedizierten Dashboard
"Zählerstände"):

```yaml
type: entities
title: Zählerstände eintragen
entities:
  - entity: number.haushaltsdoku_wasser_kalt_input
    name: Wasser kalt — neuer Stand
  - entity: sensor.haushaltsdoku_wasser_kalt
    name: aktueller Stand
    secondary_info: last-changed
  - entity: number.haushaltsdoku_strom_haupt_input
  - entity: sensor.haushaltsdoku_strom_haupt
```

### Eintrag per Service / Automation

Aus einer Automation oder einer Push-Notification-Action heraus:

```yaml
service: haushaltsdoku.add_reading
data:
  meter_name: "Wasser kalt"
  value: 1234.567
  # optional: timestamp: "2026-04-30 22:00:00"
```

`meter_name` muss exakt dem Anzeigenamen aus der Konfiguration entsprechen;
alternativ kann `meter_id` (interne UUID, in den Options sichtbar) verwendet
werden.

### Plausibilitätscheck

Wenn ein neuer Stand kleiner als der letzte ist, wird das im HA-Log als
Warnung geloggt — der Eintrag wird trotzdem gespeichert (Edge-Cases wie
Zählerwechsel sind sonst nicht abbildbar). Falsche Werte korrigierst du
über *Entwicklungswerkzeuge → Statistik → Statistik anpassen*.

## Konfigurations-Beispiel (Result)

Eine fertig eingerichtete Konfiguration sieht intern z.B. so aus:

```yaml
output_dir: www/haushaltsdoku
currency: EUR
auto_monthly: true
auto_yearly: true
meters:
  - id: "abc-123"
    name: "Strom Hauptzähler"
    entity_id: sensor.stromzaehler_total
    unit: "kWh"
    price_per_unit: 0.32
    base_fee_monthly: 12.50
    icon: "⚡"
  - id: "def-456"
    name: "Wasser Haushalt"
    entity_id: sensor.wasserzaehler_kalt
    unit: "m³"
    price_per_unit: 4.20
    base_fee_monthly: 6.00
  - id: "ghi-789"
    name: "Gas Heizung"
    entity_id: sensor.gaszaehler
    unit: "kWh"
    price_per_unit: 0.11
    base_fee_monthly: 9.80
    color: "#ef4444"
    icon: "🔥"
```

## Was die Integration anlegt

- Sensor `sensor.haushaltsdoku_letzter_bericht` — zeigt Dateinamen des
  zuletzt erzeugten Berichts und enthält in den Attributen `index_url`,
  `report_count`, `output_path`.

## Limitations / TODOs

- Druckansicht ist da, aber **kein automatischer PDF-Export** — drucke aus dem
  Browser nach PDF. (Ein optionaler `wkhtmltopdf`-Pfad könnte später kommen.)
- Vergleich Vorjahr vs. aktuelles Jahr: noch nicht im Chart, aber in den
  Summary-Cards leicht ergänzbar.
- Keine Aufschlüsselung nach Tarifen (HT/NT) — der Utility-Meter kann das,
  müsste hier durchgeschleift werden.

## Lizenz

MIT — siehe LICENSE.
