from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd
from pypdf import PdfReader

from src.csv_service import merge_sequencing_data, read_sequencing_csv
from src.report_service import build_reports, generate_reports

ROOT = Path(__file__).resolve().parents[1]
HEADER = "Sample_ID,Gene_Target,Read_Count,Coverage_Depth,Quality_Score,Mutation_Status\n"


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.records = json.loads((ROOT / "data/airtable_example.json").read_text())

    def test_missing_values_and_numeric_conversion(self):
        data = read_sequencing_csv(StringIO(HEADER + "001,EGFR,,150x,Q38,PASS\n"))
        self.assertEqual(data.iloc[0]["Sample_ID"], "001")
        self.assertTrue(pd.isna(data.iloc[0]["Read_Count"]))
        self.assertEqual(data.iloc[0]["Coverage_Depth"], 150)
        self.assertEqual(data.iloc[0]["Quality_Score"], 38)

    def test_invalid_data_rejected(self):
        for row in [",EGFR,10,20,Q30,PASS", "A,EGFR,-1,20,Q30,PASS", "A,EGFR,1.5,20,Q30,PASS", "A,EGFR,10,bad,Q30,PASS"]:
            with self.subTest(row=row), self.assertRaises(ValueError):
                read_sequencing_csv(StringIO(HEADER + row))

    def test_duplicate_ids_rejected(self):
        with self.assertRaisesRegex(ValueError, "doppelte"):
            merge_sequencing_data(self.records * 2, ROOT / "data/sequencing_data.csv")

    def test_unmatched_sample_preserved(self):
        data = merge_sequencing_data(self.records[:1], ROOT / "data/sequencing_data.csv")
        reports = build_reports(data)
        self.assertEqual(len(data), 6)
        self.assertTrue(reports[1]["missing_metadata"])
        self.assertEqual(reports[1]["client_name"], "—")

    def test_pdf_content_and_single_page(self):
        self.records[0]["fields"]["Client_Name"] = "<b>Test & Kunde</b>"
        data = merge_sequencing_data(self.records, ROOT / "data/sequencing_data.csv")
        with TemporaryDirectory() as directory:
            paths = generate_reports(data, ROOT / "templates", directory)
            self.assertEqual(len(paths), 2)
            for path in paths:
                pdf = PdfReader(path)
                self.assertEqual(len(pdf.pages), 1)
                self.assertAlmostEqual(float(pdf.pages[0].mediabox.width), 595, delta=2)
                self.assertAlmostEqual(float(pdf.pages[0].mediabox.height), 842, delta=2)
                text = pdf.pages[0].extract_text()
                self.assertIn("Probenbericht", text)
                if "001" in path.name:
                    self.assertIn("EGFR", text)
                    self.assertIn("KRAS", text)
                    self.assertIn("&lt;b&gt;Test &amp; Kunde&lt;/b&gt;", path.with_suffix(".html").read_text(encoding="utf-8"))
                else:
                    self.assertIn("PIK3CA", text)
                    self.assertIn("FLAGGED", text)

    def test_overflow_rejected(self):
        data = merge_sequencing_data(self.records, ROOT / "data/sequencing_data.csv")
        data = pd.concat([data.loc[data["Sample_ID"] == "SMP-2026-001"]] * 40)
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "A4-Seite"):
                generate_reports(data, ROOT / "templates", directory)
            self.assertEqual(list(Path(directory).glob("*.pdf")), [])


if __name__ == "__main__":
    unittest.main()
