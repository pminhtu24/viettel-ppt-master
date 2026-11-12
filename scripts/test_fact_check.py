#!/usr/bin/env python3
"""Run with python3 scripts/test_fact_check.py; one synthetic project, one page per rule."""
import json
from pathlib import Path
import tempfile
import unittest

import fact_check as fc
from source_index import build_index

SOURCE = """# Báo cáo định kỳ

## Hạ tầng
* **Trạm 5G** (KH năm: 20.120 trạm)
* **Tiến độ đầu tư mua sắm:**
* Hàng vô tuyến về cảng lũy kế: **7.480/20.120** trạm ~ 37%
* Phát sóng trạm: 1.406/2.191 trạm (64%)
* DA Tòa nhà: Đạt 98/68 DA ~144% KH Quý 3; Lũy kế 355/392 DA ~91% KH năm.

## Sự kiện
* Đảm bảo TTLL cho triển lãm Quốc phòng: 9/9 nhiệm vụ đang chuẩn bị.
* Taskforce: hoàn thành 14/39 nhiệm vụ (35%).
* **Nguy cơ chậm tiến độ:** VTM tích hợp giám sát tập trung.

## TTKTKV
* **[TTKTKV3]**
* **Triển khai swap thiết bị tại Cà Mau (15/9/2026):**
* Swap 4G: lũy kế 1.184/1.191 trạm ~99,4%.
* **Đảm bảo hạ tầng cho APEC (31/12/2026):**
* Kéo cáp 13/180km.

# Nhiệm vụ tuần sau
## Hợp đồng OS
## Nền tảng Cloud
## Hỗ trợ Dominica
"""


def svg(*texts: str) -> str:
    body = "".join(texts)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" data-content-contract="1">'
            f'{body}</svg>')


def t(text: str, claims: str, x=100, y=100, bold=False) -> str:
    weight = ' font-weight="700"' if bold else ""
    return f'<text x="{x}" y="{y}" data-claims="{claims}"{weight}>{text}</text>'


class FactCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = cls.root = Path(cls.tmp.name)
        (root / "sources").mkdir()
        (root / "sources/report.md").write_text(SOURCE, encoding="utf-8")
        build_index(root)
        outline = fc.build_outline(root)
        cls.ids = {b.text[:18]: b.id for b in outline.values()}
        cls.outline = outline

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def block(self, start: str) -> str:
        return next(i for k, i in self.ids.items() if k.startswith(start))

    def audit(self, pages: dict[str, tuple[dict, str]]) -> dict[str, list[dict]]:
        """pages: pid → (facts {id: block-start}, svg body)."""
        (self.root / "svg_output").mkdir(exist_ok=True)
        locks = []
        for n, (pid, (facts, body)) in enumerate(pages.items(), 1):
            name = f"{n:02d}_p.svg"
            (self.root / "svg_output" / name).write_text(svg(body), encoding="utf-8")
            locks.append({"page": pid, "svg": name, "facts": [{"id": f, "sources": [{"ref": self.block(b)}]}
                                                                 for f, b in facts.items()],
                          "derived": [], "conclusions": [{"id": "c", "kind": "editorial", "text": "x", "reason": "x"}],
                          "unresolved": [], "visualizations": [], "required": []})
        fences = "\n".join(f"#### Slide {i:02d} - p\n```content-lock\n{json.dumps(l, ensure_ascii=False)}\n```"
                           for i, l in enumerate(locks, 1))
        (self.root / "design_spec.md").write_text(f"content_contract: 1\n\n{fences}\n", encoding="utf-8")
        findings, _ = fc.audit(self.root)
        out: dict[str, list[dict]] = {pid: [] for pid in pages}
        for f in findings:
            out[f["page"]].append(f)
        return out

    def rules(self, findings, level="error"):
        return sorted({f["rule"] for f in findings if f["level"] == level})

    def test_outline_keeps_sections_of_flat_word_bullets(self):
        apec = self.outline[self.block("Kéo cáp")]
        swap = self.outline[self.block("Swap 4G")]
        self.assertEqual(apec.path[-2:], ["[TTKTKV3]", "Đảm bảo hạ tầng cho APEC (31/12/2026):"])
        self.assertIn("Cà Mau", swap.path[-1])
        radio = self.outline[self.block("Hàng vô tuyến")]
        self.assertEqual(radio.path[-2:], ["Trạm 5G (KH năm: 20.120 trạm)", "Tiến độ đầu tư mua sắm:"])

    def test_free_wording_with_sourced_claims_passes(self):
        found = self.audit({"P01": ({"f1": "Hàng vô tuyến", "f2": "Phát sóng"}, "".join([
            t("Hàng về cảng tăng tốc, sẵn sàng cho đợt lắp đặt mới", "c", y=60, bold=True),
            t("Vô tuyến lũy kế 7.480/20.120 trạm · 37%", "f1", y=120),
            t("Phát sóng 1.406/2.191 trạm (64%)", "f2", y=160)]))})
        self.assertEqual(self.rules(found["P01"]), [])

    def test_invented_and_dropped_period_labels(self):
        found = self.audit({"P01": ({"f1": "Phát sóng", "f2": "DA Tòa"}, "".join([
            t("Phát sóng 1.406/2.191 trạm theo tuần", "f1", y=120),
            t("DA tòa nhà 144%", "f2", y=200)]))})
        self.assertIn("period-invented", self.rules(found["P01"]))
        self.assertIn("period-dropped", self.rules(found["P01"], "warn"))

    def test_label_from_another_clause(self):
        found = self.audit({"P01": ({"f1": "DA Tòa"}, t("DA tòa nhà ~91% KH quý 3", "f1"))})
        self.assertIn("period-other-clause", self.rules(found["P01"]))

    def test_ratio_without_its_noun_reads_as_a_date(self):
        found = self.audit({"P01": ({"f1": "Đảm bảo TTLL"}, t("Triển lãm Quốc phòng 9/9: đang chuẩn bị", "f1"))})
        self.assertIn("ratio-noun", self.rules(found["P01"]))
        ok = self.audit({"P01": ({"f1": "Đảm bảo TTLL"}, t("Triển lãm Quốc phòng: 9/9 nhiệm vụ đang chuẩn bị", "f1"))})
        self.assertEqual(self.rules(ok["P01"]), [])

    def test_heading_names_a_section_its_numbers_do_not_belong_to(self):
        found = self.audit({"P01": ({"f1": "Swap 4G", "f2": "Kéo cáp"}, "<g>" + "".join([
            t("TTKTKV3 — Cà Mau", "f1", x=100, y=100, bold=True),
            t("Swap 4G lũy kế 1.184/1.191 trạm", "f1", x=100, y=140),
            t("Kéo cáp 13/180km", "f2", x=100, y=180)]) + "</g>")})
        hits = [f for f in found["P01"] if f["rule"] == "heading-scope"]
        self.assertEqual(len(hits), 1)
        self.assertIn("13/180", hits[0]["detail"])

    def test_title_count_must_match_the_source_list(self):
        found = self.audit({"P01": ({"f1": "Hợp đồng OS", "f2": "Nền tảng", "f3": "Hỗ trợ"}, "".join([
            t("4 nhiệm vụ trọng tâm tuần sau", "c", y=60, bold=True),
            t("Hợp đồng OS", "f1", y=120), t("Nền tảng Cloud", "f2", y=160), t("Hỗ trợ Dominica", "f3", y=200)]))})
        self.assertIn("count-mismatch", self.rules(found["P01"]))

    def test_status_must_be_said_with_its_hedge(self):
        found = self.audit({"P01": ({"f1": "Taskforce"}, "".join([
            t("Taskforce 14/39 nhiệm vụ", "f1", y=100), t("Chậm tiến độ", "f1", y=140)])),
                            "P02": ({"f1": "Taskforce", "f2": "Nguy cơ"}, "".join([
            t("Taskforce 14/39 nhiệm vụ", "f1", y=100), t("Chậm tiến độ", "f1", y=140),
            t("VTM tích hợp giám sát — chậm tiến độ", "f2", y=180)]))})
        self.assertEqual(self.rules(found["P01"]), ["status-unsourced"])   # a status the source never says
        self.assertEqual(self.rules(found["P02"]), ["hedge-dropped"])      # the source says "nguy cơ chậm"

    def test_numbers_outside_the_source_versus_binding_gaps(self):
        found = self.audit({"P01": ({"f1": "Phát sóng"}, "".join([
            t("Phát sóng 1.406/2.191 trạm, 2.000 trạm mới", "f1", y=100),
            t("Vô tuyến 7.480 trạm", "f1", y=140)]))})
        self.assertIn("number-unsourced", self.rules(found["P01"]))            # 2.000 is nowhere
        self.assertIn("number-unbound", self.rules(found["P01"], "warn"))      # 7.480 is in another block

    def test_review_table_lists_flagged_rows_only_and_draft_fails_on_errors(self):
        self.audit({"P01": ({"f1": "Phát sóng"}, t("Phát sóng 1.406/2.191 trạm theo tuần", "f1")),
                    "P02": ({"f1": "Hàng vô tuyến"}, t("Lũy kế 7.480/20.120 trạm", "f1"))})
        table = fc.review_table(self.root)
        self.assertIn("error:period-invented", table)
        self.assertNotIn("7.480/20.120", table)                                # clean row stays out
        draft = fc.draft_review(self.root, "test-model")
        self.assertEqual((draft["P01"]["status"], draft["P02"]["status"]), ("fail", "pass"))
        self.assertFalse(draft["P01"]["scope_period_status"])
        # a chart page needs its verify-charts note before it can pass
        spec = self.root / "design_spec.md"
        spec.write_text(spec.read_text(encoding="utf-8").replace(
            '"visualizations": []', '"visualizations": [{"id": "v1", "template": "bar_chart"}]'), encoding="utf-8")
        self.assertEqual(fc.draft_review(self.root, "test-model")["P02"]["status"], "fail")
        notes = self.root / "charts.json"
        notes.write_text(json.dumps({"P02": {"v1": "verify-charts: P02 bar heights match 7480/20120"}}), encoding="utf-8")
        self.assertEqual(fc.draft_review(self.root, "test-model", notes)["P02"]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
