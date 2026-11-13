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

    def test_ratio_gives_value_and_target_and_footer_carries_the_document_line(self):
        plan = PLAN.replace("- template: progress_bar_chart", "- template: bullet_chart").replace(
            "- data: B0004 value=37%\n- data: B0005 value=48%",
            '- data: B0004 value=7.480/20.120 category="Hàng vô tuyến"\n- data: B0005 value=10.144/20.929 category="Hàng DC"')
        (self.root / "sources/report.md").write_text(SOURCE.replace("# Báo cáo định kỳ", "# BÁO CÁO ĐỊNH KỲ"),
                                                     encoding="utf-8")
        build_index(self.root)                                  # an all-caps heading becomes sentence case
        code, report = self.build(plan)
        self.assertEqual((code, report["plan_gate"]), (0, "pass"), report)
        p2 = {p["page"]: p for p in cc.load_contract(self.root)}["P02"]
        values = {f["id"]: f for f in p2["facts"]}
        row = p2["visualizations"][0]["observations"][0]
        self.assertEqual((values[row["value"]]["value"], values[row["target"]]["value"]), (7480, 20120))
        src = next(c for c in p2["conclusions"] if c["id"] == "c_src")
        self.assertTrue(src["text"].startswith("Nguồn: Báo cáo định kỳ"), src)

    def test_unreadable_or_invented_slides_and_tables_instead_of_charts_are_errors(self):
        long = SOURCE + "\n## Phụ lục\n" + "".join(f"* Mục {i}: " + "nội dung dài " * 30 + f"{i}/{i + 40} trạm.\n" for i in range(8))
        (self.root / "sources/report.md").write_text(long, encoding="utf-8")
        build_index(self.root)
        tables = "".join(f"\n### P{n:02d} Bảng {n}\n- template: metric_table\n- blocks: B0004-B0006\n- why: cùng tiến độ\n"
                         for n in range(4, 8))
        plan = (PLAN.replace("# Plan\n", "# Plan\n- pages: 5\n").replace("### P03 Các mốc hợp đồng OS", "### P03 Các mốc hợp đồng OS tại VTNT")
                    .replace("- template: timeline", "- template: vertical_list") + tables +
                "\n### P08 Phụ lục\n- template: vertical_list\n- blocks: B0011-B0018\n- why: các mục phụ lục\n")
        code, report = self.build(plan)
        errors = " | ".join(report["errors"])
        self.assertEqual(code, 1)
        for needle in ("'VTNT' is nowhere in the source", "P06: metric_table — P04, P05 already show prose numbers",
                       "P08: its blocks hold", "data chart(s) for", "the plan has 8 slides but the user confirmed 5"):
            self.assertIn(needle, errors)

    def test_recurring_entity_colors_reach_the_shared_lock(self):
        code, report = self.build(PLAN.replace("- images: none", "- images: none\n- colors: KV1=#12436D, KV2=#28A197, KV3=#7C3AED"))
        self.assertEqual(code, 0, report)
        lock = (self.root / "spec_lock.md").read_text(encoding="utf-8")
        self.assertIn("- entity_colors: KV1=#12436D, KV2=#28A197, KV3=#7C3AED", lock)
        code, report = self.build(PLAN.replace("- images: none", "- images: none\n- colors: KV1=#EE0033"))
        self.assertIn("colors: 'KV1=#EE0033'", " ".join(report["errors"]))

    def test_coverage_names_sections_with_numbers_no_slide_shows(self):
        code, report = self.build(PLAN.replace("- blocks: B0008, B0009", "- blocks: B0008"))
        self.assertEqual(code, 0, report)
        self.assertIn("Hợp đồng OS", " ".join(report["uncovered_sections_with_numbers"]))

    def test_delays_no_slide_shows_are_warned_by_id(self):
        (self.root / "sources/report.md").write_text(SOURCE.replace(
            "* Ký tờ trình đề xuất mua sắm: **03/9/2026**.",
            "* Ký tờ trình đề xuất mua sắm: **03/9/2026**.\n* Phần mềm thị trường đang chậm theo KL (15/8/2026).\n"
            "* Không có KPI nào cảnh báo đỏ trong tuần 33."), encoding="utf-8")
        build_index(self.root)
        code, report = self.build(PLAN)
        risks = [w for w in report["warnings"] if w.startswith("risk items")]
        self.assertEqual(code, 0, report)
        self.assertEqual(len(risks), 1, report["warnings"])
        self.assertIn("B0010 (chậm)", risks[0])
        self.assertNotIn("B0011", risks[0])                    # "không có … cảnh báo" is good news

    def test_source_lists_every_block_once_with_its_id(self):
        code, report = run("source", self.root)
        self.assertIn("B0004 · Hàng vô tuyến về cảng lũy kế: 7.480/20.120 trạm ~ 37%", report["text"])
        self.assertIn("▸ B0003 Tiến độ đầu tư mua sắm:", report["text"])

    def test_source_ends_with_a_page_estimate_that_grows_with_the_text(self):
        _, report = run("source", self.root)
        self.assertIn("▸ Page estimate: 4 slides (cover 1 + chapters 0 + content 2 + ending 1)", report["text"])
        long = SOURCE + "\n## Phụ lục\n" + "".join(f"* Mục {i}: " + "nội dung dài " * 30 + f"{i}/{i + 40} trạm.\n" for i in range(8))
        (self.root / "sources/report.md").write_text(long, encoding="utf-8")
        build_index(self.root)
        _, report = run("source", self.root)
        first = next(l for l in report["text"].splitlines() if l.startswith("▸ Page estimate"))
        self.assertRegex(first, r"Page estimate: (\d+) slides .* content [3-9] .*; \d+ slides still show all of it")

    def test_page_estimate_counts_flat_files_and_lets_small_topics_share_the_minimum(self):
        flat = "".join(f"Đoạn {i}: " + "nội dung biên bản họp " * 20 + "\n\n" for i in range(8))     # no heading at all
        topics = "".join(f"## {i}. Chủ đề {i}\n* " + "ý chính ngắn " * 25 + "\n" for i in range(8))
        for text, content, least in ((flat, "content 3", 4), (topics, "content 8", 4)):
            (self.root / "sources/report.md").write_text(text, encoding="utf-8")
            build_index(self.root)
            line = next(l for l in run("source", self.root)[1]["text"].splitlines() if "Page estimate" in l)
            self.assertIn(content, line)
            self.assertIn(f"fewer than {least},", line)

    def test_catalog_file_matches_the_index(self):
        path = sb.SKILL_DIR / "templates/charts/catalog.md"
        self.assertEqual(path.read_text(encoding="utf-8"), sb.catalog_text(),
                         "run `spec_build.py catalog --write` after changing charts_index.json")


if __name__ == "__main__":
    unittest.main()
