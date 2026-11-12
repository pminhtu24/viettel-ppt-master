#!/usr/bin/env python3
"""Run with python3 scripts/test_spec_build.py; one synthetic source, plans built end to end."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import content_check as cc
import spec_build as sb
from source_index import build_index

SOURCE = """# Báo cáo định kỳ

## Hạ tầng
* **Tiến độ đầu tư mua sắm:**
* Hàng vô tuyến về cảng lũy kế: **7.480/20.120** trạm ~ 37%
* Hàng cơ điện (DC) về cảng: **10.144/20.929** tủ DC ~48%
* Bổ sung tài nguyên: Hoàn thành 140/457 GP, tuần TH 110.

## Hợp đồng OS
* Ký bộ hồ sơ Yêu cầu kỹ thuật: **25/8/2026**.
* Ký tờ trình đề xuất mua sắm: **03/9/2026**.
"""

PLAN = """# Plan
- title: Báo cáo định kỳ
- audience: Ban điều hành
- density: dense
- icons: tabler-filled: calendar, flag
- images: none

## Part 1: Hạ tầng

### P01 Báo cáo định kỳ
- rhythm: anchor
- layout: 01_cover
- background: bg_red_corner_sweep

### P02 Tiến độ mua sắm thiết bị
- job: Hàng về cảng so với kế hoạch
- template: progress_bar_chart
- blocks: B0004-B0005
- data: B0004 value=37%
- data: B0005 value=48%
- why: hai tỷ lệ cùng đo hàng về cảng trên kế hoạch năm
- calc: c1 percent B0006:140 B0006:457

### P03 Các mốc hợp đồng OS
- template: timeline
- blocks: B0008, B0009
- why: các mốc ký hồ sơ của cùng một hợp đồng
"""


def run(*argv) -> tuple[int, dict]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = sb.main([str(a) for a in argv])
    text = out.getvalue()
    return code, (json.loads(text) if text.lstrip().startswith("{") else {"text": text})


class SpecBuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "sources").mkdir()
        (self.root / "sources/report.md").write_text(SOURCE, encoding="utf-8")
        build_index(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, plan: str) -> tuple[int, dict]:
        (self.root / "plan.md").write_text(plan, encoding="utf-8")
        return run("build", self.root)

    def test_plan_builds_valid_locks_and_spec_lock(self):
        code, report = self.build(PLAN)
        self.assertEqual((code, report["plan_gate"]), (0, "pass"), report)
        pages = {p["page"]: p for p in cc.load_contract(self.root)}
        self.assertEqual(sorted(pages), ["P01", "P02", "P03"])
        p2 = pages["P02"]
        self.assertEqual(p2["svg"], "02_tien_do_mua_sam_thiet_bi.svg")
        values = {f["id"]: f for f in p2["facts"]}
        self.assertEqual((values["B0004_value"]["value"], values["B0004_value"]["unit"]), (37, "%"))
        self.assertEqual(p2["derived"][0]["value"], 30.6)                 # 140/457
        self.assertEqual(p2["visualizations"][0]["template"], "progress_bar_chart")
        self.assertIn("B0004", p2["required"])
        self.assertEqual(pages["P01"]["conclusions"][0]["kind"], "editorial")   # a cover shows no fact
        lock = (self.root / "spec_lock.md").read_text(encoding="utf-8")
        for line in ("- P02: progress_bar_chart", "- P01: 01_cover", "- P01: bg_red_corner_sweep",
                     "- inventory: calendar, flag", "- body: 20", "- generation_mode: parallel"):
            self.assertIn(line, lock)
        self.assertIn("templates/charts/progress_bar_chart.svg",
                      (self.root / "design_spec.md").read_text(encoding="utf-8"))

    def test_plan_mistakes_are_reported_before_anything_is_written(self):
        bad = (PLAN.replace("value=48%", "value=49%")                       # not a number of B0006
                   .replace("B0008, B0009", "B0008, B0099")                 # no such block
                   .replace("calendar, flag", "calendar, target-arrow")     # no such icon
                   .replace("- why: hai tỷ lệ cùng đo hàng về cảng trên kế hoạch năm\n", ""))
        code, report = self.build(bad)
        self.assertEqual(code, 1)
        errors = " | ".join(report["errors"])
        for needle in ("'49%' is not a number of that block", "unknown block", "target-arrow", "needs a `- why:`"):
            self.assertIn(needle, errors)
        self.assertFalse((self.root / "design_spec.md").exists())

    def test_coverage_names_sections_with_numbers_no_slide_shows(self):
        code, report = self.build(PLAN.replace("- blocks: B0008, B0009", "- blocks: B0008"))
        self.assertEqual(code, 0, report)
        self.assertIn("Hợp đồng OS", " ".join(report["uncovered_sections_with_numbers"]))

    def test_source_lists_every_block_once_with_its_id(self):
        code, report = run("source", self.root)
        self.assertIn("B0004 · Hàng vô tuyến về cảng lũy kế: 7.480/20.120 trạm ~ 37%", report["text"])
        self.assertIn("▸ B0003 Tiến độ đầu tư mua sắm:", report["text"])

    def test_catalog_file_matches_the_index(self):
        path = sb.SKILL_DIR / "templates/charts/catalog.md"
        self.assertEqual(path.read_text(encoding="utf-8"), sb.catalog_text(),
                         "run `spec_build.py catalog --write` after changing charts_index.json")


if __name__ == "__main__":
    unittest.main()
