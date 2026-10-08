import re
from datetime import datetime
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from playwright.sync_api import sync_playwright
from pypdf import PdfReader


def display(value):
    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
        return "—"
    return str(value)


def number(value):
    return "—" if pd.isna(value) else f"{value:g}"


def build_reports(data):
    reports = []
    for sample_id, rows in data.groupby("Sample_ID", sort=True):
        first = rows.iloc[0]

        def metadata(name):
            return display(first.get(name + "_airtable", first.get(name)))

        measurements = []
        for _, row in rows.iterrows():
            status = display(row["Mutation_Status"])
            measurements.append(
                {
                    "gene": display(row["Gene_Target"]),
                    "read_count": number(row["Read_Count"]),
                    "coverage": number(row["Coverage_Depth"]),
                    "quality": number(row["Quality_Score"]),
                    "status": status,
                    "status_class": {"PASS": "pass", "FLAGGED": "flagged"}.get(
                        status, "unknown"
                    ),
                }
            )
        reports.append(
            {
                "sample_id": sample_id,
                "client_name": metadata("Client_Name"),
                "project_name": metadata("Project_Name"),
                "submission_date": metadata("Submission_Date"),
                "notes": metadata("Operator_Notes"),
                "measurements": measurements,
                "flagged_count": sum(m["status"] == "FLAGGED" for m in measurements),
                "missing_metadata": first["Zuordnung"] != "both",
            }
        )
    return reports


def generate_reports(data, template_dir, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html"]),
        undefined=StrictUndefined,
    )
    template = env.get_template("report.html")
    generated_date = datetime.now().astimezone().date().isoformat()
    generated = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            for report in build_reports(data):
                html = template.render(**report, generated_date=generated_date)
                page.set_content(html, wait_until="load")
                pdf = page.pdf(
                    format="A4", prefer_css_page_size=True, print_background=True
                )
                if len(PdfReader(BytesIO(pdf)).pages) != 1:
                    raise ValueError(
                        f"Probe {report['sample_id']}: Inhalt passt nicht auf eine A4-Seite. "
                        "Vorlage anpassen oder weniger Messungen pro Bericht verwenden."
                    )
                sample_id = report["sample_id"]
                safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", sample_id)[:80]
                if safe_id != sample_id:
                    safe_id += "_" + sha256(sample_id.encode()).hexdigest()[:10]
                stem = f"Report_{safe_id}_{generated_date}"
                pdf_path = output_dir / f"{stem}.pdf"
                (output_dir / f"{stem}.html").write_text(html, encoding="utf-8")
                pdf_path.write_bytes(pdf)
                generated.append(pdf_path)
        finally:
            browser.close()
    return generated
