#!/usr/bin/env python3
"""Run with python3 scripts/test_page_plan.py; synthetic projects only."""
import contextlib
import io
import json
import math
import re
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import page_plan
from page_plan import Project, classify, main, partition

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720"><text>{}</text></svg>'
CHARTS = {5: "bar_chart", 6: "basic_table", 9: "kpi_cards", 12: "bar_chart", 15: "timeline", 18: "bar_chart"}


def make_project(root: Path, pages: int = 20, execution: str = "") -> Project:
    parts = {1: "Mở đầu", 3: "Hạ tầng", 9: "Nhiệm vụ", 16: "Tuần sau"}
    chapters = {1, 3, 9, 16, pages}
    lines = ["# Design Spec", "content_contract: 1", "## IX. Content Outline"]
    for n in range(1, pages + 1):
        if n in parts:
            lines.append(f"### Part {len(lines)}: {parts[n]}")
        lines += [f"#### Slide {n:02d} - Trang số {n}", f"- **Title**: Tiêu đề {n}",
                  "```content-lock", json.dumps({"page": f"P{n:02d}", "svg": f"{n:02d}_page.svg"}), "```", ""]
    (root / "design_spec.md").write_text("\n".join(lines), encoding="utf-8")
    rhythm = "\n".join(f"- P{n:02d}: {'anchor' if n in chapters else 'dense'}" for n in range(1, pages + 1))
    charts = "\n".join(f"- P{n:02d}: {c}" for n, c in CHARTS.items() if n <= pages)
    (root / "spec_lock.md").write_text(
        f"## colors\n\n- primary: #EE0033\n\n## forbidden\n\n- rgba()\n\n## page_rhythm\n\n{rhythm}\n\n"
        f"## page_charts\n\n{charts}\n\n## execution\n\n- generation_mode: parallel\n{execution}",
        encoding="utf-8")
    (root / "svg_output").mkdir()
    return Project(root)


def write_svg(project: Project, n: int, body: str = "ok") -> Path:
    path = project.svg_dir / f"{n:02d}_page.svg"
    path.write_text(SVG.format(body), encoding="utf-8")
    return path


def run(*argv) -> int:
    with contextlib.redirect_stdout(io.StringIO()):
        return main([str(a) for a in argv])


@patch("page_plan.checker_errors", return_value=[])
class PagePlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.content = patch("page_plan.content_errors", return_value={}).start()
        self.addCleanup(patch.stopall)

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self):
        return json.loads((self.root / "briefs/plan.json").read_text(encoding="utf-8"))

    def test_groups_respect_limits_cover_every_page_and_balance(self, _):
        for pages, max_pages in ((20, 6), (35, 6), (50, 6), (12, 3)):
            with self.subTest(pages=pages):
                for p in self.root.iterdir():
                    if p.is_dir():
                        for f in p.iterdir():
                            f.unlink()
                        p.rmdir()
                    else:
                        p.unlink()
                project = make_project(self.root, pages, f"- max_pages_per_subagent: {max_pages}\n")
                self.assertEqual(run("briefs", self.root), 0)
                plan = self.plan()
                anchor = plan["anchor"]["page"]
                grouped = [pid for wave in plan["waves"] for g in wave for pid in g["pages"]]
                self.assertEqual(sorted(grouped + [anchor]), sorted(p["id"] for p in project.pages))
                self.assertEqual(len(grouped), len(set(grouped)))
                self.assertNotIn(anchor, grouped)
                for wave in plan["waves"]:
                    self.assertLessEqual(len(wave), project.max_subagents)
                    for group in wave:
                        self.assertLessEqual(len(group["pages"]), max_pages)
                        nums = [project.by_id[pid]["num"] for pid in group["pages"]]
                        self.assertEqual(nums, sorted(nums))
                groups = max(math.ceil(len(grouped) / max_pages), min(project.max_subagents, math.ceil(len(grouped) / 3)))
                self.assertLessEqual(sum(len(w) for w in plan["waves"]), groups)
                self.assertLessEqual(max(len(g["pages"]) for w in plan["waves"] for g in w), math.ceil(len(grouped) / groups) + 1)
                self.assertEqual(len(plan["waves"]), math.ceil(groups / project.max_subagents))
                weights = [g["weight"] for wave in plan["waves"] for g in wave]
                if len(weights) > 1:
                    self.assertLessEqual(max(weights), 1.5 * sum(weights) / len(weights))

    def test_partition_contiguous_and_minimal_group_count(self, _):
        items = [{"id": f"P{i}", "part": i // 4} for i in range(13)]
        groups = partition(items, {i["id"]: 1.0 for i in items}, 5)
        self.assertEqual(len(groups), 3)
        self.assertEqual([i for g in groups for i in g], items)

    def test_anchor_is_a_representative_content_page_not_the_agenda(self, _):
        make_project(self.root, 8)
        lock = self.root / "spec_lock.md"
        lock.write_text(lock.read_text(encoding="utf-8").replace("## page_charts\n\n", "## page_charts\n\n- P02: agenda_list\n- P04: vertical_list\n"),
                        encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main(["briefs", str(self.root)])
        self.assertEqual(self.plan()["anchor"]["page"], "P05")          # the first data chart, not P02/P04
        self.assertIn("separate sub-agent calls", out.getvalue())

    def test_briefs_share_one_rules_file_and_keep_verbatim_lock(self, _):
        project = make_project(self.root)
        run("briefs", self.root)
        shared = (self.root / "briefs/_shared.md").read_text(encoding="utf-8")
        self.assertIn("Binding pattern", shared)
        self.assertIn("- primary: #EE0033", shared)
        texts = {pid: (self.root / f"briefs/{pid}.md").read_text(encoding="utf-8") for pid in ("P04", "P05", "P12")}
        for text in texts.values():
            self.assertTrue(text.startswith("# Page "))
            self.assertNotIn("Binding pattern", text)
            self.assertIn(str(self.root.resolve() / "briefs/_shared.md"), text)
        self.assertIn(project.by_id["P05"]["text"], texts["P05"])
        self.assertIn("bar_chart.svg", texts["P05"])
        self.assertIn(str(project.svg_dir / "05_page.svg"), texts["P05"])
        context = self.plan()["waves"][0][0]["context"]
        self.assertIn("ONLY these files", context)
        self.assertIn("_shared.md", context)
        self.assertIn("Never open the skill's scripts", context)
        self.assertNotIn("{SKILL_DIR}", context)

    def test_icons_reports_missing_inventory_names_with_real_alternatives(self, _):
        make_project(self.root)
        spec_lock = self.root / "spec_lock.md"
        base = spec_lock.read_text(encoding="utf-8")
        spec_lock.write_text(base + "\n## icons\n\n- library: chunk-filled\n- inventory: bolt, server, handshake\n",
                             encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["icons", str(self.root)])
        missing = json.loads(out.getvalue())
        self.assertEqual(code, 1)
        self.assertEqual(list(missing), ["handshake"])
        icons = page_plan.ICONS_DIR / "chunk-filled"
        self.assertTrue(missing["handshake"] and all((icons / f"{n}.svg").exists() for n in missing["handshake"]))
        spec_lock.write_text(base + "\n## icons\n\n- library: chunk-filled\n- inventory: bolt, server\n",
                             encoding="utf-8")
        self.assertEqual(run("icons", self.root), 0)

    def test_status_classifies_every_state(self, _):
        project = make_project(self.root, 8)
        for n in (1, 2, 3, 4, 5):
            write_svg(project, n)
        (project.svg_dir / "06_page.svg").write_text("<svg", encoding="utf-8")
        (project.svg_dir / "99_extra.svg").write_text(SVG.format("x"), encoding="utf-8")
        self.assertEqual(run("record", self.root, "--pages", "1,2,3"), 0)
        write_svg(project, 2, "user edit")
        spec = self.root / "design_spec.md"
        spec.write_text(spec.read_text(encoding="utf-8").replace("Tiêu đề 3", "Tiêu đề 3 mới"), encoding="utf-8")
        status = {pid: e["status"] for pid, e in classify(Project(self.root))["pages"].items()}
        self.assertEqual(status, {"P01": "done", "P02": "edited", "P03": "stale", "P04": "unknown",
                                  "P05": "unknown", "P06": "broken", "P07": "missing", "P08": "missing"})
        self.assertEqual(classify(Project(self.root))["extra"], ["99_extra.svg"])

    def test_unknown_page_with_checker_errors_is_broken(self, checker):
        project = make_project(self.root, 3)
        write_svg(project, 1)
        checker.return_value = ["[brand-font] bad"]
        self.assertEqual(classify(project)["pages"]["P01"]["status"], "broken")

    def test_resume_only_draws_missing_broken_stale(self, _):
        project = make_project(self.root, 10)
        for n in range(1, 11):
            write_svg(project, n)
        run("record", self.root, "--pages", "all")
        (project.svg_dir / "07_page.svg").unlink()
        write_svg(project, 4, "user edit")
        run("briefs", self.root, "--only", "missing,broken,stale")
        plan = self.plan()
        self.assertEqual(sorted(plan["pages"]), ["P07"])
        self.assertIn("P04", plan["frozen"])
        self.assertNotIn("P04", [pid for w in plan["waves"] for g in w for pid in g["pages"]])

    def test_record_refuses_stale_and_checker_errors(self, checker):
        project = make_project(self.root, 4)
        write_svg(project, 1)
        write_svg(project, 2)
        run("record", self.root, "--pages", "1")
        spec = self.root / "design_spec.md"
        spec.write_text(spec.read_text(encoding="utf-8").replace("Tiêu đề 1", "Tiêu đề 1 mới"), encoding="utf-8")
        self.assertEqual(run("record", self.root, "--pages", "1"), 1)
        checker.return_value = ["[text-overflow] x"]
        self.assertEqual(run("record", self.root, "--pages", "2"), 1)
        self.assertNotIn("P02", Project(self.root).load_state()["pages"])

    def test_verify_flags_missing_extra_and_frozen_changes(self, _):
        project = make_project(self.root, 8)
        write_svg(project, 8)
        run("briefs", self.root, "--pages", "3,4")
        for n in (3, 4):
            write_svg(project, n)
        self.assertEqual(run("verify", self.root), 0)
        write_svg(project, 8, "overwritten by a sub-agent")
        self.assertEqual(run("verify", self.root), 1)
        write_svg(project, 8)
        (project.svg_dir / "04_page.svg").unlink()
        self.assertEqual(run("verify", self.root), 1)

    def test_legacy_spec_keeps_existing_svg_names(self, _):
        (self.root / "design_spec.md").write_text("### Part 1: A\n#### Slide 01 - Bìa đầu\n#### Slide 02 - Hạ tầng\n",
                                                   encoding="utf-8")
        (self.root / "svg_output").mkdir()
        (self.root / "svg_output/02_ten_cu.svg").write_text(SVG.format("x"), encoding="utf-8")
        project = Project(self.root)
        self.assertEqual([p["svg"] for p in project.pages], ["01_bia_dau.svg", "02_ten_cu.svg"])
        self.assertEqual(project.mode, "sequential")



    def test_svg_name_must_carry_own_slide_number(self, _):
        make_project(self.root, 4)
        spec = self.root / "design_spec.md"
        spec.write_text(spec.read_text(encoding="utf-8").replace('"03_page.svg"', '"02_chapter.svg"'), encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            Project(self.root)
        self.assertIn("P03: 02_chapter.svg", str(ctx.exception))

    def test_partition_fills_every_subagent_slot(self, _):
        items = [{"id": f"P{i}", "part": 0} for i in range(19)]
        groups = partition(items, {i["id"]: 1.0 for i in items}, 6, 6)
        self.assertLessEqual(len(groups), 6)
        self.assertEqual([i for g in groups for i in g], items)
        self.assertEqual(max(map(len, groups)), 4)  # ceil(19/6): as short as 6 groups, one agent fewer
        self.assertEqual(max(map(len, partition(items, {i["id"]: 1.0 for i in items}, 6))), 5)  # old: 4 groups
        for n, expected in ((3, 1), (5, 2), (9, 3), (13, 5), (17, 6), (36, 6), (40, 7)):
            self.assertEqual(len(partition([{"id": f"Q{k}", "part": 0} for k in range(n)],
                                           {f"Q{k}": 1.0 for k in range(n)}, 6, 6)), expected, n)

    def test_briefs_refuse_pages_without_content_lock(self, _):
        make_project(self.root, 4)
        spec = self.root / "design_spec.md"
        text = spec.read_text(encoding="utf-8")
        spec.write_text(re.sub(r"(#### Slide 03 - [^\n]*\n[^\n]*\n)```content-lock\n[^\n]*\n```\n", r"\1", text),
                        encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["briefs", str(self.root)]), 1)
        self.assertIn("P03", out.getvalue())
        self.assertFalse((self.root / "briefs/plan.json").exists())

    def test_check_reports_unwritten_svg_and_block_id_pattern(self, _):
        make_project(self.root, 4)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["check", str(self.root), "--pages", "2"]), 1)
        self.assertIn("svg missing", out.getvalue())
        self.assertEqual(run("check", self.root, "--pages", "all", "--lock-only"), 0)  # plan gate: locks only
        self.assertEqual(page_plan.BLOCK_ID_RE.findall("Nguồn: S3f9a1c2b7d4e-B0006, tuần 34/2026, 9/9"),
                         ["S3f9a1c2b7d4e-B0006"])

    def test_lock_errors_list_every_broken_fact_with_its_id_and_a_hint(self, _):
        import content_check as cc
        catalog = json.loads(cc.CATALOG.read_text(encoding="utf-8"))["charts"]
        blocks = {"S1-B0001": "* Hàng vô tuyến: **7.480/20.120** trạm ~ 37%", "S1-B0002": "Tiếp nhận 271.7K PAKH"}

        def fact(fid, ref, quote, raw, value):
            return {"id": fid, "text": "t", "entity": "e", "unit": "u", "period": "n/a", "scope": "n/a",
                    "status": "reported", "sources": [{"ref": ref, "quote": quote}], "raw": raw, "value": value,
                    "locale": "vi"}
        lock = {"source_index_sha256": "old", "facts": [
            fact("f1", "S1-B0001", "Hàng vô tuyến: **7.480/20.120**", "7.480", 7480),
            fact("f2", "S1-B0001", "not in this block", "37", 37),
            fact("f3", "S1-B0002", "Tiếp nhận 271.7K PAKH", "271.7", 271.7)]}
        errors = page_plan.lock_errors(lock, blocks, catalog, "new")
        self.assertEqual(len(errors), 3)
        self.assertIn("source_index_sha256 must be new", errors[0])
        self.assertTrue(errors[1].startswith("f2: ") and "source_index.py <project> --list" in errors[1])
        self.assertTrue(errors[2].startswith("f3: Invalid Vietnamese number") and "locale en" in errors[2])
        lock["source_index_sha256"] = "new"
        lock["facts"] = lock["facts"][:1]
        self.assertEqual(page_plan.lock_errors(lock, blocks, catalog, "new"), [])

    def test_content_errors_block_record_and_show_in_verify(self, _):
        project = make_project(self.root, 4)
        run("briefs", self.root, "--pages", "2,3")
        write_svg(project, 2)
        write_svg(project, 3)
        self.content.side_effect = lambda proj, pids, **_: {pid: "Unbound SVG text: x" for pid in pids if pid == "P03"}
        self.assertEqual(run("record", self.root, "--pages", "2,3"), 1)
        self.assertEqual(list(Project(self.root).load_state()["pages"]), ["P02"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            main(["verify", str(self.root)])
        self.assertEqual(json.loads(out.getvalue())["content_errors"], {"P03": "Unbound SVG text: x"})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(main(["check", str(self.root), "--pages", "3"]), 1)
        self.assertIn("content: Unbound", out.getvalue())

    def test_accept_lock_records_stale_page(self, _):
        project = make_project(self.root, 2)
        write_svg(project, 1)
        run("record", self.root, "--pages", "1")
        spec = self.root / "design_spec.md"
        spec.write_text(spec.read_text(encoding="utf-8").replace("Tiêu đề 1", "Tiêu đề 1 mới"), encoding="utf-8")
        self.assertEqual(run("record", self.root, "--pages", "1"), 1)
        self.assertEqual(run("record", self.root, "--pages", "1", "--accept-lock"), 0)
        self.assertEqual(classify(Project(self.root))["pages"]["P01"]["status"], "done")


    def test_briefs_keep_an_anchor_drawn_before_the_plan(self, _):
        project = make_project(self.root, 12)
        run("briefs", self.root, "--pages", "5")
        anchor = self.plan()["anchor"]["page"]
        write_svg(project, project.by_id[anchor]["num"])
        run("record", self.root, "--pages", anchor)
        run("briefs", self.root)
        plan = self.plan()
        self.assertEqual((plan["anchor"]["page"], plan["anchor"]["needs_draw"]), (anchor, False))
        self.assertNotIn(anchor, plan["pages"])

if __name__ == "__main__":
    unittest.main()
