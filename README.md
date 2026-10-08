# Airtable Report Generator

Python-Skript: Airtable-Stammdaten + Sequencing CSV → Jinja2 HTML → einseitiger A4-PDF-Bericht pro Probe.

## Installation (Windows / PowerShell)

Python 3.10 oder neuer verwenden.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
```

Für echte Airtable-Daten `.env.example` als `.env` kopieren und `AIRBASE_TOKEN` setzen. Der Token benötigt Lesezugriff auf die gewünschte Base. `.env` wird nicht versioniert.

## Ausführen

Ohne Airtable-Zugang mit synthetischen Stammdaten:

```powershell
.\.venv\Scripts\python.exe main.py --records-json data/airtable_example.json --csv data/sequencing_data.csv
```

Mit Airtable:

```powershell
.\.venv\Scripts\python.exe main.py --url "https://airtable.com/appBASE/tblTABLE" --csv data/sequencing_data.csv
```

Oder `main.py` ohne Argumente starten und die Eingabeaufforderungen beantworten. Der CSV-Standard ist `data/sequencing_data.csv`. `--sample SMP-2026-001` beschränkt die Ausgabe auf eine Probe, `--output output/demo` ändert den Ausgabeordner, `--id-column Proben_ID` wählt ein anderes Airtable-ID-Feld.

Ausgabe: `output/Report_<Sample_ID>_<Datum>.pdf` und die zugehörige HTML-Datei. Das Datum entspricht der lokalen Systemzeitzone. Ein erneuter Lauf am selben Tag überschreibt denselben Bericht. Airtable wird nur gelesen; eine View-ID in der URL filtert die Tabelle nicht.

## Daten und Annahmen

- Ein Bericht pro eindeutiger `Sample_ID` in der CSV. Airtable-Proben ohne CSV-Messungen erhalten keinen Bericht.
- CSV: UTF-8, Komma als Trennzeichen. Pflichtspalten: `Sample_ID`, `Gene_Target`, `Read_Count`, `Coverage_Depth`, `Quality_Score`, `Mutation_Status`.
- `Sample_ID` und `Gene_Target` müssen befüllt sein. Leerzeichen am Rand werden entfernt, IDs bleiben Text.
- Read Count: nichtnegative ganze Zahl. Coverage und Qualität: nichtnegative endliche Zahlen, optional mit `x` am Ende bzw. `Q` am Anfang. Fehlende Zahlen bleiben fehlend und erscheinen als `—`.
- Stammdaten: `Sample_ID`, `Client_Name`, `Project_Name`, `Submission_Date`, `Operator_Notes`. Fehlende optionale Felder erscheinen als `—`.
- Mehrere Messungen dürfen derselben Probe zugeordnet sein. Doppelte Airtable-IDs führen zu einem Fehler. Fehlende Zuordnungen werden im Bericht kenntlich gemacht.
- `PASS` und `FLAGGED` werden farblich dargestellt; keine selbst erfundenen fachlichen Grenzwerte. Andere Statuswerte bleiben sichtbar.
- Layout in `templates/report.html`. Keine externen Schriftarten oder Bilder erforderlich. HTML-Daten werden von Jinja2 escaped.
- Die PDF-Seitenzahl wird geprüft. Bei mehr als einer Seite wird dieser Bericht nicht gespeichert und der Lauf mit Fehlermeldung beendet. Bereits zuvor erzeugte Berichte bleiben bestehen. Es werden keine Zeilen abgeschnitten oder stillschweigend weggelassen.

## Aufbau

- `main.py`: Eingaben, Ablauf und Fehlermeldungen
- `src/airtable_client.py`: API-Verbindung und URL-Prüfung
- `src/csv_service.py`: CSV-Bereinigung und Zusammenführung
- `src/report_service.py`: Berichtsdaten, Jinja2 und PDF-Export
- `templates/report.html`: HTML/CSS-Vorlage
- `data/`: kleine Übungsdaten für einen Offline-Durchlauf

Tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

PDF-Export nutzt [Playwright `page.pdf()`](https://playwright.dev/python/docs/api/class-page#page-pdf) mit Print-CSS; pypdf kontrolliert die Seitenzahl.
