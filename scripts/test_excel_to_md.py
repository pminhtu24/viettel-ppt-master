#!/usr/bin/env python3
"""Run with python3 scripts/test_excel_to_md.py: numbers as the sheet shows them, merged notes once."""
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).parent / "source_to_md"))
from excel_to_md import convert_to_markdown  # noqa: E402


class ExcelToMarkdownTests(unittest.TestCase):
    def test_formats_and_merged_cells(self):
        wb = Workbook()
        ws = wb.active
        ws.title = "Doanh thu"
        ws.append(["Mảng", "Quý 3", None, "Hạn"])
        ws.merge_cells("B1:C1")                                   # short group header: repeated
        ws.append(["Di động", 0.725382, 1234567.25, date(2026, 12, 15)])
        ws["B2"].number_format = "0.0%"
        ws["C2"].number_format = "#,##0.0"
        ws["D2"].number_format = "dd/mm/yyyy"
        ws.append(["Nhận xét: doanh thu di động đạt 72,5% KH năm, tăng 3,2% so với cùng kỳ."])
        ws.merge_cells("A3:D3")                                   # long note: once
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "r.xlsx"
            wb.save(src)
            convert_to_markdown(str(src))
            md = src.with_suffix(".md").read_text(encoding="utf-8")
        self.assertIn("| Mảng | Quý 3 | Quý 3 | Hạn |", md)
        self.assertIn("| Di động | 72.5% | 1234567.3 | 15/12/2026 |", md)
        self.assertEqual(md.count("doanh thu di động đạt 72,5%"), 1)


if __name__ == "__main__":
    unittest.main()
