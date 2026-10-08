import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from jinja2 import TemplateError
from playwright.sync_api import Error as PlaywrightError
from requests.exceptions import RequestException

from config import AIRBASE_TOKEN
from src.airtable_client import AirTableClient
from src.csv_service import merge_sequencing_data
from src.report_service import generate_reports

PROJECT_DIR = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="Airtable und Sequencing CSV zu A4-PDF-Berichten")
    parser.add_argument("--url", help="Airtable-Tabellen-URL")
    parser.add_argument("--csv", type=Path, help="Sequencing CSV")
    parser.add_argument("--records-json", type=Path, help="Lokale Airtable-Testdaten statt API")
    parser.add_argument("--id-column", default="Sample_ID", help="Proben-ID-Feld in Airtable")
    parser.add_argument("--sample", help="Nur diese Probe ausgeben")
    parser.add_argument("--output", type=Path, default=PROJECT_DIR / "output")
    args = parser.parse_args()
    try:
        csv_path = args.csv
        if csv_path is None:
            default_csv = PROJECT_DIR / "data" / "sequencing_data.csv"
            entry = input(f"CSV-Pfad [Enter fuer {default_csv}]: ").strip().strip('"')
            csv_path = Path(entry) if entry else default_csv
        if args.records_json:
            records = json.loads(args.records_json.read_text(encoding="utf-8"))
        else:
            url = args.url or input("Geben Sie die Airtable-URL an: ").strip()
            records = AirTableClient(AIRBASE_TOKEN).get_table(url).all()
        if not isinstance(records, list) or not records:
            raise ValueError("Keine Airtable-Datensaetze vorhanden.")
        if any(not isinstance(r, dict) or not isinstance(r.get("fields"), dict) for r in records):
            raise ValueError("Airtable-Testdaten muessen eine Liste mit fields-Objekten sein.")
        data = merge_sequencing_data(records, csv_path, args.id_column)
        if args.sample:
            data = data.loc[data["Sample_ID"] == args.sample]
            if data.empty:
                raise ValueError(f"Probe {args.sample!r} nicht in der CSV gefunden.")
        print(data.to_string(index=False))
        for path in generate_reports(data, PROJECT_DIR / "templates", args.output):
            print(f"PDF erstellt: {path}")
        return 0
    except RequestException:
        print("Airtable-Abruf fehlgeschlagen. Netzwerk, Token und Tabellenzugriff pruefen.", file=sys.stderr)
    except PlaywrightError:
        print("PDF-Renderer fehlgeschlagen. Setup pruefen: python -m playwright install chromium", file=sys.stderr)
    except (OSError, ValueError, TemplateError, pd.errors.ParserError) as error:
        print(f"Fehler: {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
