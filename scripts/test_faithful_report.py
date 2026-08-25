from __future__ import annotations

import html
import importlib.util
import json
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace


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


def _contract(project: Path) -> dict:
    inventory = json.loads((project / "source_inventory.json").read_text(encoding="utf-8"))
    joined = ",".join(block["id"] for block in inventory["blocks"])
    project.joinpath("spec_lock.md").write_text(
        "## content_mode\n- mode: faithful_report\n- source_inventory: source_inventory.json\n- coverage_required: 100\n\n"
        f"## page_sources\n- P01: {joined}\n",
        encoding="utf-8",
    )
    project.joinpath("design_spec.md").write_text(
        f"## IX. Content Outline\n\n#### Slide 01 - Báo cáo\n- **Source Blocks**: {joined}\n"
        "\n## X. Technical Constraints\n- viewBox: 0 0 1280 720\n",
        encoding="utf-8",
    )
    return inventory


def _svg(project: Path, inventory: dict, split_fact: str | None = None) -> None:
    groups: list[str] = []
    for block in inventory["blocks"]:
        if block["kind"] == "image":
            groups.append(
                f'<g data-source-ids="{block["id"]}" data-content-kind="source_asset"><image href="asset.png"/></g>'
            )
        for fact in block["facts"]:
            text = str(fact["source_span"])
            if fact["id"] == split_fact:
                words = text.split()
                cut = max(1, len(words) // 2)
                visible = f"<text>{html.escape(' '.join(words[:cut]))}</text><text>{html.escape(' '.join(words[cut:]))}</text>"
            else:
                visible = f"<text>{html.escape(text)}</text>"
            groups.append(
                f'<g data-source-ids="{block["id"]}" data-fact-ids="{fact["id"]}">{visible}</g>'
            )
    project.joinpath("svg_output/01_report.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg">' + "".join(groups) + "</svg>", encoding="utf-8"
    )


def test_source_only_spec_and_svg_gate_without_claim_manifest(tmp_path):
    project = _project(
        tmp_path,
        "# BÁO CÁO GIAO BAN TUẦN\n\n## Kết quả thực hiện\n\n- KPI 4G đạt 127/361 vị trí, 35% kế hoạch.\n\n"
        "## Nhiệm vụ trọng tâm\n\n- Dự kiến hoàn thành 50 cổng ngày 31/8/2026.\n",
    )
    inventory = _contract(project)
    assert inventory["version"] == 2
    assert not project.joinpath("claim_manifest.json").exists()
    assert faithful_report.validate_spec(project)["status"] == "pass"
    split = next(fact["id"] for block in inventory["blocks"] for fact in block["facts"] if "127/361" in fact["source_span"])
    _svg(project, inventory, split)
    report = faithful_report.validate_svg(project)
    assert report["status"] == "pass"
    assert report["facts_expected"] == report["facts_rendered"]


def test_status_tuple_and_derived_changes_fail(tmp_path):
    project = _project(
        tmp_path,
        "# Báo cáo giao ban\n\n- Cosite đạt 43% KH Q3.\n- Cloud đạt 9,7/23,3 PB lũy kế.\n"
        "- UPS: 6/36 về đầu tháng 11, đủ 36 vào 20/11.\n- Tiến độ phủ lõm 21/75/160.\n",
    )
    inventory = _contract(project)
    replacements = {
        "Cosite đạt 43% KH Q3.": "Cosite vượt 43% KH Q3.",
        "Cloud đạt 9,7/23,3 PB lũy kế.": "Cloud đạt khoảng 73% lũy kế.",
        "UPS: 6/36 về đầu tháng 11, đủ 36 vào 20/11.": "UPS: 30/36 về đầu tháng 11, đủ 36 vào 20/11.",
        "Tiến độ phủ lõm 21/75/160.": "Tiến độ phủ lõm 21/160.",
    }
    for source, changed in replacements.items():
        _svg(project, inventory)
        svg = project / "svg_output/01_report.svg"
        svg.write_text(svg.read_text(encoding="utf-8").replace(source, changed), encoding="utf-8")
        assert faithful_report.validate_svg(project)["status"] == "fail"


def test_unsupported_deadline_and_ratio_fail(tmp_path):
    project = _project(tmp_path, "# Báo cáo giao ban\n\n- Gửi báo cáo tiến độ.\n- Cloud 9,7 PB trên kế hoạch 23,3 PB.\n")
    inventory = _contract(project)
    for source, changed in [
        ("Gửi báo cáo tiến độ.", "Gửi báo cáo tiến độ trước 31/8."),
        ("Cloud 9,7 PB trên kế hoạch 23,3 PB.", "Cloud 9,7 PB trên kế hoạch 23,3 PB, đạt ≈42%."),
    ]:
        _svg(project, inventory)
        svg = project / "svg_output/01_report.svg"
        svg.write_text(svg.read_text(encoding="utf-8").replace(source, changed), encoding="utf-8")
        assert faithful_report.validate_svg(project)["status"] == "fail"

    _svg(project, inventory)
    svg = project / "svg_output/01_report.svg"
    svg.write_text(
        svg.read_text(encoding="utf-8").replace(
            "</svg>", '<text data-content-kind="brand_chrome">Deadline 31/8</text></svg>'
        ),
        encoding="utf-8",
    )
    assert any("unsupported brand_chrome" in error for error in faithful_report.validate_svg(project)["errors"])


def test_svg_requires_direct_fact_provenance(tmp_path):
    project = _project(tmp_path, "# Báo cáo giao ban\n\n- Cosite đạt 43% KH Q3.\n- UPS đủ 36 vào 20/11.\n")
    inventory = _contract(project)
    facts = [fact for block in inventory["blocks"] for fact in block["facts"]]
    blocks = inventory["blocks"]
    _svg(project, inventory)
    svg = project / "svg_output/01_report.svg"
    content = svg.read_text(encoding="utf-8").replace(f' data-fact-ids="{facts[0]["id"]}"', "", 1)
    svg.write_text(content, encoding="utf-8")
    assert faithful_report.validate_svg(project)["status"] == "fail"

    _svg(project, inventory)
    content = svg.read_text(encoding="utf-8").replace(
        f'data-source-ids="{blocks[0]["id"]}" data-fact-ids="{facts[0]["id"]}"',
        f'data-source-ids="{blocks[1]["id"]}" data-fact-ids="{facts[0]["id"]}"',
        1,
    )
    svg.write_text(content, encoding="utf-8")
    report = faithful_report.validate_svg(project)
    assert report["status"] == "fail"
    assert any("does not belong" in error for error in report["errors"])

    _svg(project, inventory)
    svg.rename(project / "svg_output/02_report.svg")
    report = faithful_report.validate_svg(project)
    assert report["status"] == "fail"
    assert any("not mapped to P02" in error for error in report["errors"])


def test_chart_uses_same_fact_gate_and_needs_all_tokens(tmp_path):
    project = _project(tmp_path, "# Báo cáo giao ban\n\n- Cloud đạt 9,7 PB kế hoạch 23,3 PB trong Q3.\n")
    inventory = _contract(project)
    lock = project / "spec_lock.md"
    lock.write_text(lock.read_text(encoding="utf-8") + "\n## page_charts\n- P01: bar_chart\n", encoding="utf-8")
    _svg(project, inventory)
    assert faithful_report.validate_svg(project)["status"] == "pass"
    svg = project / "svg_output/01_report.svg"
    svg.write_text(svg.read_text(encoding="utf-8").replace(" trong Q3", ""), encoding="utf-8")
    report = faithful_report.validate_svg(project)
    assert report["status"] == "fail"
    assert report["chart_mismatches"] > 0


def test_source_asset_and_legacy_manifest_behavior(tmp_path):
    project = _project(tmp_path, "# Báo cáo giao ban\n\n![Sơ đồ](diagram.png)\n")
    inventory = _contract(project)
    project.joinpath("claim_manifest.json").write_text("{}", encoding="utf-8")
    design = project / "design_spec.md"
    design.write_text(design.read_text(encoding="utf-8").replace("- **Source Blocks**", "- **Claims**: P01-C01\n- **Source Blocks**"), encoding="utf-8")
    report = faithful_report.validate_spec(project)
    assert report["status"] == "pass"
    assert "legacy claim_manifest.json ignored by faithful_report V2" in report["warnings"]
    _svg(project, inventory)
    assert faithful_report.validate_svg(project)["status"] == "pass"


def test_table_header_can_repeat_across_pages(tmp_path):
    project = _project(
        tmp_path,
        "# Báo cáo giao ban\n\n| Hạng mục | Kết quả |\n|---|---|\n| A | Hoàn thành |\n| B | Đang triển khai |\n",
    )
    inventory = json.loads((project / "source_inventory.json").read_text(encoding="utf-8"))
    heading = inventory["blocks"][0]
    header, row_a, row_b = [block for block in inventory["blocks"] if block["kind"] == "table_row"]
    page_blocks = {"P01": [heading, header, row_a], "P02": [header, row_b]}
    project.joinpath("spec_lock.md").write_text(
        "## content_mode\n- mode: faithful_report\n- source_inventory: source_inventory.json\n- coverage_required: 100\n\n## page_sources\n"
        + "\n".join(f"- {page}: {','.join(block['id'] for block in blocks)}" for page, blocks in page_blocks.items())
        + "\n",
        encoding="utf-8",
    )
    project.joinpath("design_spec.md").write_text(
        "## IX. Content Outline\n\n"
        + "\n\n".join(
            f"#### Slide {int(page[1:]):02d} - Bảng\n- **Source Blocks**: {','.join(block['id'] for block in blocks)}"
            for page, blocks in page_blocks.items()
        )
        + "\n\n## X. Technical Constraints\n",
        encoding="utf-8",
    )
    assert "duplicate mappings" in faithful_report.validate_spec(project)["warnings"][0]
    for page, blocks in page_blocks.items():
        groups = [
            f'<g data-source-ids="{block["id"]}" data-fact-ids="{fact["id"]}"><text>{html.escape(str(fact["source_span"]))}</text></g>'
            for block in blocks
            for fact in block["facts"]
        ]
        project.joinpath(f"svg_output/{int(page[1:]):02d}_table.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg">' + "".join(groups) + "</svg>", encoding="utf-8"
        )
    assert faithful_report.validate_svg(project)["status"] == "pass"


def test_missing_block_fails_and_narrative_source_stays_standard(tmp_path):
    project = _project(tmp_path, "# A reflective essay\n\nThis is a long-form narrative without operational KPIs.\n")
    inventory = _contract(project)
    assert inventory["profile"]["recommended_mode"] == "standard"
    project.joinpath("spec_lock.md").write_text(
        "## content_mode\n- mode: faithful_report\n- source_inventory: source_inventory.json\n- coverage_required: 100\n\n"
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


def test_pdf_text_presence_checks_facts_per_page(tmp_path, monkeypatch):
    project = _project(tmp_path, "# Báo cáo giao ban\n\n- Cosite đạt 43% KH Q3.\n")
    _contract(project)
    pdf = tmp_path / "deck.pdf"
    pdf.write_bytes(b"pdf")
    monkeypatch.setattr(faithful_report.shutil, "which", lambda name: "/usr/bin/pdftotext" if name == "pdftotext" else None)
    monkeypatch.setattr(
        faithful_report.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(stdout="Báo cáo giao ban\nCosite đạt 43% KH Q3.\f", stderr=""),
    )
    assert faithful_report._pdf_text_presence(project, pdf) == ("pass", [])
    monkeypatch.setattr(
        faithful_report.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(stdout="Báo cáo giao ban\nCosite vượt 43% KH Q3.\f", stderr=""),
    )
    status, missing = faithful_report._pdf_text_presence(project, pdf)
    assert status == "fail"
    assert missing


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
    inventory = _contract(project)
    _svg(project, inventory)
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
