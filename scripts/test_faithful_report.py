from __future__ import annotations

import html
import importlib.util
import json
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("faithful_report", ROOT / "scripts/faithful_report.py")
faithful_report = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = faithful_report
SPEC.loader.exec_module(faithful_report)


def _project(tmp_path: Path, source_text: str) -> Path:
    project = tmp_path / "project"
    sources = project / "sources"
    (project / "svg_output").mkdir(parents=True)
    sources.mkdir()
    source = sources / "report.md"
    source.write_text(source_text, encoding="utf-8")
    faithful_report.prepare(project, [source])
    return project


def _contract(project: Path) -> tuple[dict, list[dict]]:
    inventory = json.loads((project / "source_inventory.json").read_text(encoding="utf-8"))
    ids = [block["id"] for block in inventory["blocks"]]
    joined = ",".join(ids)
    project.joinpath("spec_lock.md").write_text(
        "## content_mode\n- mode: faithful_report\n- source_inventory: source_inventory.json\n- coverage_required: 100\n\n"
        f"## page_sources\n- P01: {joined}\n",
        encoding="utf-8",
    )
    claims: list[dict] = []
    claim_no = 0
    for block in inventory["blocks"]:
        if block["kind"] == "image":
            claim_no += 1
            claims.append(
                {
                    "id": f"P01-C{claim_no:02d}", "page": "P01", "text": "", "type": "asset",
                    "source_ids": [block["id"]], "fact_ids": [],
                }
            )
        for fact in block["facts"]:
            claim_no += 1
            claims.append(
                {
                    "id": f"P01-C{claim_no:02d}", "page": "P01", "text": fact["source_span"], "type": "mechanical",
                    "source_ids": [block["id"]], "fact_ids": [fact["id"]],
                }
            )
    claim_ids = ",".join(claim["id"] for claim in claims)
    project.joinpath("design_spec.md").write_text(
        f"## IX. Content Outline\n\n#### Slide 01 - Báo cáo\n- **Source Blocks**: {joined}\n- **Claims**: {claim_ids}\n"
        "\n## X. Technical Constraints\n- viewBox: 0 0 1280 720\n",
        encoding="utf-8",
    )
    _write_claims(project, claims, "forbidden", validate=False)
    return inventory, claims


def _write_claims(project: Path, claims: list[dict], policy: str, validate: bool = True) -> dict | None:
    project.joinpath("claim_manifest.json").write_text(
        json.dumps({"content_mode": "faithful_report", "derived_content": policy, "claims": claims}, ensure_ascii=False),
        encoding="utf-8",
    )
    return faithful_report.validate_spec(project) if validate else None


def _svg(project: Path, claims: list[dict]) -> None:
    groups = []
    for claim in claims:
        attrs = f'data-source-ids="{claim["source_ids"][0]}" data-claim-ids="{claim["id"]}"'
        if claim["type"] == "asset":
            groups.append(f"<g {attrs}><image href=\"asset.png\"/></g>")
        else:
            groups.append(f"<g {attrs}><text>{html.escape(claim['text'])}</text></g>")
    project.joinpath("svg_output/01_report.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg">' + "".join(groups) + "</svg>", encoding="utf-8"
    )


def test_source_only_spec_and_svg_gate(tmp_path):
    project = _project(
        tmp_path,
        "# BÁO CÁO GIAO BAN TUẦN\n\n## Kết quả thực hiện\n\n- KPI 4G đạt 127/361 vị trí, 35% kế hoạch.\n\n"
        "## Nhiệm vụ trọng tâm\n\n- Dự kiến hoàn thành 50 cổng ngày 31/8/2026.\n",
    )
    inventory, claims = _contract(project)
    assert inventory["version"] == 2
    assert all("facts" in block for block in inventory["blocks"])
    assert faithful_report.validate_spec(project)["status"] == "pass"
    _svg(project, claims)
    assert faithful_report.validate_svg(project)["status"] == "pass"

    claims[-1]["text"] = "Dự kiến hoàn thành 50 cổng ngày 30/8/2026."
    assert _write_claims(project, claims, "forbidden")["status"] == "fail"


def test_status_and_tuple_changes_fail(tmp_path):
    project = _project(
        tmp_path,
        "# Báo cáo giao ban\n\n- Cosite đạt 43% KH Q3.\n- Cloud đạt 9,7/23,3 PB lũy kế.\n"
        "- UPS: 6/36 về đầu tháng 11, đủ 36 vào 20/11.\n- Tiến độ phủ lõm 21/75/160.\n",
    )
    _, claims = _contract(project)
    replacements = {
        "Cosite đạt 43% KH Q3.": "Cosite vượt 43% KH Q3.",
        "Cloud đạt 9,7/23,3 PB lũy kế.": "Cloud đạt khoảng 73% lũy kế.",
        "UPS: 6/36 về đầu tháng 11, đủ 36 vào 20/11.": "UPS: 30/36 về đầu tháng 11, đủ 36 vào 20/11.",
        "Tiến độ phủ lõm 21/75/160.": "Tiến độ phủ lõm 21/160.",
    }
    for source, changed in replacements.items():
        mutated = [dict(claim) for claim in claims]
        next(claim for claim in mutated if claim["text"] == source)["text"] = changed
        assert _write_claims(project, mutated, "forbidden")["status"] == "fail"


def test_unsupported_deadline_and_derived_content_fail(tmp_path):
    project = _project(tmp_path, "# Báo cáo giao ban\n\n- Gửi báo cáo tiến độ.\n- Cloud 9,7 PB trên kế hoạch 23,3 PB.\n")
    _, claims = _contract(project)
    deadline_claim = next(claim for claim in claims if claim["text"] == "Gửi báo cáo tiến độ.")
    deadline_claim["text"] = "Gửi báo cáo tiến độ trước 31/8."
    assert _write_claims(project, claims, "forbidden")["status"] == "fail"

    _, claims = _contract(project)
    cloud = next(claim for claim in claims if "9,7 PB" in claim["text"])
    cloud.update({"type": "derived", "text": "Cloud 41,6% kế hoạch.", "formula": "9.7 / 23.3 * 100"})
    assert _write_claims(project, claims, "forbidden")["status"] == "fail"
    assert _write_claims(project, claims, "allowed")["status"] == "pass"


def test_svg_requires_claim_provenance(tmp_path):
    project = _project(tmp_path, "# Báo cáo giao ban\n\n- Cosite đạt 43% KH Q3.\n")
    _, claims = _contract(project)
    _svg(project, claims)
    svg = project.joinpath("svg_output/01_report.svg")
    svg.write_text(svg.read_text(encoding="utf-8").replace("đạt", "vượt"), encoding="utf-8")
    report = faithful_report.validate_svg(project)
    assert report["status"] == "fail"
    assert any("SVG claim token mismatch" in error for error in report["errors"])

    _svg(project, claims)
    svg.write_text(svg.read_text(encoding="utf-8").replace("</svg>", '<text data-content-kind="brand_chrome">Deadline 31/8</text></svg>'), encoding="utf-8")
    report = faithful_report.validate_svg(project)
    assert report["status"] == "fail"
    assert any("unsupported brand_chrome" in error for error in report["errors"])


def test_chart_pages_require_source_locked_manifest(tmp_path):
    project = _project(tmp_path, "# Báo cáo giao ban\n\n- Cloud đạt 9,7 PB kế hoạch 23,3 PB trong Q3.\n")
    _, claims = _contract(project)
    lock = project.joinpath("spec_lock.md")
    lock.write_text(lock.read_text(encoding="utf-8") + "\n## page_charts\n- P01: bar_chart\n", encoding="utf-8")
    assert faithful_report.validate_spec(project)["status"] == "fail"

    cloud = next(claim for claim in claims if "9,7 PB" in claim["text"])
    manifest = {
        "content_mode": "faithful_report", "derived_content": "forbidden", "claims": claims,
        "charts": [{
            "id": "P01-CH01", "page": "P01", "source_ids": cloud["source_ids"], "fact_ids": cloud["fact_ids"],
            "series": [{"label": "Cloud", "values": ["9,7"]}, {"label": "kế hoạch", "values": ["23,3"]}],
            "unit": "PB", "period": "Q3",
        }],
    }
    project.joinpath("claim_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    assert faithful_report.validate_spec(project)["status"] == "pass"


def test_missing_block_fails_and_narrative_source_stays_standard(tmp_path):
    project = _project(tmp_path, "# A reflective essay\n\nThis is a long-form narrative without operational KPIs.\n")
    inventory = json.loads((project / "source_inventory.json").read_text(encoding="utf-8"))
    assert inventory["profile"]["recommended_mode"] == "standard"
    _contract(project)
    project.joinpath("spec_lock.md").write_text(
        "## content_mode\n- mode: faithful_report\n- coverage_required: 100\n\n"
        f"## page_sources\n- P01: {inventory['blocks'][0]['id']}\n",
        encoding="utf-8",
    )
    assert faithful_report.validate_spec(project)["status"] == "fail"


def test_structured_report_routes_faithful_and_skips_table_separator(tmp_path):
    rows = "\n".join(f"- KPI {i} đạt {i}/100 trong tuần." for i in range(1, 61))
    project = _project(
        tmp_path,
        f"# BÁO CÁO GIAO BAN TUẦN\n\n## Kết quả thực hiện\n\n{rows}\n\n"
        "## Nhiệm vụ trọng tâm\n\n| Hạng mục | Kết quả |\n|---|---|\n| A | Hoàn thành |\n\n"
        "## Tuần sau\n\n- Tiếp tục triển khai.\n",
    )
    inventory = json.loads((project / "source_inventory.json").read_text(encoding="utf-8"))
    assert inventory["profile"]["recommended_mode"] == "faithful_report"
    assert not any(block["text"] == "|---|---|" for block in inventory["blocks"])
    assert sum(block["kind"] == "table_row" for block in inventory["blocks"]) == 2


def test_renderer_selection_is_cross_platform():
    def which_windows(name):
        return {"powershell": "powershell.exe", "libreoffice": "soffice.exe"}.get(name)

    assert faithful_report.renderer_candidates("Windows", which_windows) == [
        ("microsoft_powerpoint", "powershell.exe"), ("libreoffice", "soffice.exe")
    ]
    assert faithful_report.renderer_candidates("Darwin", lambda name: "/usr/bin/osascript" if name == "osascript" else None) == [
        ("microsoft_powerpoint", "/usr/bin/osascript")
    ]
    assert faithful_report.renderer_candidates("Linux", lambda name: "/usr/bin/soffice" if name == "soffice" else None) == [
        ("libreoffice", "/usr/bin/soffice")
    ]


def test_fast_render_stays_draft(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    pptx = tmp_path / "deck.pptx"
    with zipfile.ZipFile(pptx, "w") as archive:
        archive.writestr("ppt/slides/slide1.xml", "<p:sld/>")
    report = faithful_report.render_check(project, pptx, fast=True)
    assert report["release_status"] == "DRAFT"
    assert str(report["output_pptx"]).endswith("_DRAFT.pptx")
    assert json.loads((project / "coverage_report.json").read_text(encoding="utf-8"))["release_status"] == "DRAFT"


def test_review_then_user_approval_promotes_status(tmp_path):
    project = tmp_path / "project"
    exports = project / "exports"
    exports.mkdir(parents=True)
    draft = exports / "deck_DRAFT.pptx"
    draft.write_bytes(b"pptx")
    project.joinpath("render_report.json").write_text(
        json.dumps({"backend": "microsoft_powerpoint", "errors": [], "output_pptx": str(draft), "release_status": "DRAFT"}),
        encoding="utf-8",
    )
    review = faithful_report.render_review(project, True, [])
    assert review["release_status"] == "REVIEW"
    assert Path(review["output_pptx"]).name == "deck_REVIEW.pptx"
    final = faithful_report.approve_final(project)
    assert final["release_status"] == "FINAL"
    assert Path(final["output_pptx"]).name == "deck_FINAL.pptx"


def test_failed_powerpoint_falls_back_once_to_libreoffice(tmp_path, monkeypatch):
    project = _project(tmp_path, "# Báo cáo giao ban\n\n- Cosite đạt 43% KH Q3.\n")
    _, claims = _contract(project)
    _svg(project, claims)
    pptx = tmp_path / "deck.pptx"
    with zipfile.ZipFile(pptx, "w") as archive:
        archive.writestr("ppt/slides/slide1.xml", "<p:sld/>")

    monkeypatch.setattr(faithful_report, "renderer_candidates", lambda: [("microsoft_powerpoint", "powershell"), ("libreoffice", "soffice")])
    monkeypatch.setattr(faithful_report.platform, "system", lambda: "Windows")
    monkeypatch.setattr(faithful_report, "_render_windows", lambda *_: (_ for _ in ()).throw(RuntimeError("PowerPoint unavailable")))

    def render_lo(_executable, _pptx, pdf, _work):
        pdf.write_bytes(b"%PDF-1.4\n/Type /Page\n")
        return "LibreOffice test"

    monkeypatch.setattr(faithful_report, "_render_libreoffice", render_lo)
    monkeypatch.setattr(faithful_report, "_pdf_page_count", lambda _pdf: 1)
    monkeypatch.setattr(faithful_report, "_pdf_text_presence", lambda _project, _pdf: ("pass", []))
    monkeypatch.setattr(faithful_report, "_render_previews", lambda _pdf, _output: [])
    report = faithful_report.render_check(project, pptx)
    assert report["backend"] == "libreoffice"
    assert len(report["fallbacks"]) == 1
    assert report["errors"] == []
