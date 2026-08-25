#!/usr/bin/env python3
"""Prepare and validate source-complete faithful-report slide projects."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path
from xml.etree import ElementTree as ET

BLOCK_ID_RE = re.compile(r"SRC\d{2}-B\d{4}")
FACT_ID_RE = re.compile(r"SRC\d{2}-B\d{4}-F\d{2,4}")
SLIDE_RE = re.compile(r"^####\s+Slide\s+(\d{1,3})\b", re.I)
SOURCE_BLOCKS_RE = re.compile(r"^-\s+\*\*Source Blocks\*\*:\s*(.+)$", re.I)
NUMBER_RE = re.compile(r"(?<![\w])\d+(?:[.,/]\d+)*(?:\s*%)?|\d+(?=[GgKk]\b)")
ALLOWED_EXCLUSIONS = {"exact_duplicate", "decorative_asset", "header_footer_artifact"}
REPORT_MARKERS = (
    "báo cáo",
    "giao ban",
    "kết quả thực hiện",
    "nhiệm vụ trọng tâm",
    "tuần sau",
    "weekly report",
    "monthly report",
    "status report",
    "operations report",
)
CHROME_KINDS = {"brand_chrome", "page_number"}


def _kind(line: str) -> str:
    stripped = line.lstrip()
    if re.match(r"^#{1,6}\s", stripped):
        return "heading"
    if re.match(r"^!\[[^]]*\]\([^)]+\)", stripped):
        return "image"
    if stripped.startswith("|") and stripped.endswith("|"):
        return "table_row"
    if re.match(r"^(?:[-+*]|\d+[.)])\s+", stripped):
        return "list_item"
    return "paragraph"


def _is_table_separator(line: str) -> bool:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def _blocks(text: str) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    buffer: list[str] = []
    start = 0
    buffer_kind = "paragraph"

    def flush(end: int) -> None:
        nonlocal buffer, start, buffer_kind
        if buffer:
            result.append({"kind": buffer_kind, "text": "\n".join(buffer).strip(), "line_start": start, "line_end": end})
            buffer = []

    for line_no, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            flush(line_no - 1)
            continue
        if _is_table_separator(line):
            flush(line_no - 1)
            continue
        kind = _kind(line)
        standalone = kind in {"heading", "image", "table_row", "list_item"}
        if standalone:
            flush(line_no - 1)
            buffer = [line]
            start = line_no
            buffer_kind = kind
            if kind != "list_item":
                flush(line_no)
        elif buffer and buffer_kind == "list_item":
            buffer.append(line)
        else:
            if not buffer:
                start = line_no
                buffer_kind = "paragraph"
            buffer.append(line)
    flush(len(text.splitlines()))
    return result


def _plain_text(text: str, kind: str = "paragraph") -> str:
    text = re.sub(r"\\([\\.*_()\-])", r"\1", text)
    text = re.sub(r"!\[([^]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    if kind == "heading":
        text = re.sub(r"^\s*#{1,6}\s+", "", text)
    elif kind == "list_item" or re.match(r"^\s*(?:[-+*]|\d+[.)])\s+", text):
        text = re.sub(r"^\s*(?:[-+*]|\d+[.)])\s+", "", text)
    elif kind == "table_row":
        text = " ".join(cell.strip() for cell in text.strip().strip("|").split("|") if cell.strip())
    text = re.sub(r"[`*_]", "", text).replace("~~", "")
    return re.sub(r"\s+", " ", text).strip()


def _lexemes(text: str) -> list[str]:
    return re.findall(r"\d+(?:[.,/]\d+)*(?:\s*%)?|[~≈]|[^\W_]+(?:[-'][^\W_]+)*", text, re.UNICODE)


def _token_counter(text: str) -> Counter[str]:
    return Counter(token.casefold().replace(" ", "") for token in _lexemes(text))


def _fact_spans(block: dict[str, object]) -> list[str]:
    kind = str(block["kind"])
    if kind == "image":
        return []
    plain = _plain_text(str(block["text"]), kind)
    if not plain:
        return []
    if kind == "table_row":
        cells = [_plain_text(cell) for cell in str(block["text"]).strip().strip("|").split("|")]
        return [cell for cell in cells if cell]
    if kind in {"paragraph", "list_item"}:
        spans = [part.strip() for part in re.split(r"(?<=[.!?;])\s+|\n+", plain) if part.strip()]
        return spans or [plain]
    return [plain]


def _facts(block: dict[str, object]) -> list[dict[str, object]]:
    facts: list[dict[str, object]] = []
    for fact_no, span in enumerate(_fact_spans(block), 1):
        lexemes = _lexemes(span)
        facts.append(
            {
                "id": f"{block['id']}-F{fact_no:02d}",
                "source_span": span,
                "protected_tokens": lexemes,
            }
        )
    return facts


def _profile(blocks: list[dict[str, object]]) -> dict[str, object]:
    joined = "\n".join(str(block["text"]) for block in blocks).lower()
    kinds = Counter(str(block["kind"]) for block in blocks)
    report_hits = sorted(marker for marker in REPORT_MARKERS if marker in joined)
    numeric_blocks = sum(bool(NUMBER_RE.search(str(block["text"]))) for block in blocks)
    structured = kinds["heading"] >= 3 or kinds["list_item"] >= 15 or kinds["table_row"] >= 5
    dense = len(blocks) >= 60 or numeric_blocks >= 20 or kinds["table_row"] >= 10
    recommended = len(report_hits) >= 2 and structured and dense
    return {
        "recommended_mode": "faithful_report" if recommended else "standard",
        "report_markers": report_hits,
        "block_count": len(blocks),
        "numeric_block_count": numeric_blocks,
        "kind_counts": dict(kinds),
    }


def prepare(project: Path, sources: list[Path]) -> Path:
    if not sources:
        sources = sorted((project / "sources").glob("*.md"))
    if not sources:
        raise ValueError("no Markdown sources found")

    inventory: dict[str, object] = {"version": 2, "sources": [], "blocks": [], "profile": {}}
    all_blocks: list[dict[str, object]] = []
    for source_no, source in enumerate(sources, 1):
        source = source.resolve()
        text = source.read_text(encoding="utf-8")
        parsed = _blocks(text)
        source_id = f"SRC{source_no:02d}"
        inventory["sources"].append(
            {
                "id": source_id,
                "path": str(source.relative_to(project.resolve())) if source.is_relative_to(project.resolve()) else str(source),
                "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        )
        for block_no, block in enumerate(parsed, 1):
            block.update(
                {
                    "id": f"{source_id}-B{block_no:04d}",
                    "source_id": source_id,
                    "required": True,
                    "exclusion_reason": None,
                }
            )
            block["facts"] = _facts(block)
            all_blocks.append(block)
    inventory["blocks"] = all_blocks
    inventory["profile"] = _profile(all_blocks)
    output = project / "source_inventory.json"
    output.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] {output} | recommended_mode={inventory['profile']['recommended_mode']} blocks={len(all_blocks)}")
    return output


def _section(text: str, name: str) -> list[str]:
    lines: list[str] = []
    active = False
    for line in text.splitlines():
        if line.startswith("## "):
            active = line[3:].strip().lower() == name.lower()
            continue
        if active:
            lines.append(line)
    return lines


def _expand_ids(value: str, ordered_ids: list[str]) -> tuple[list[str], list[str]]:
    index = {block_id: i for i, block_id in enumerate(ordered_ids)}
    expanded: list[str] = []
    invalid: list[str] = []
    for raw in value.replace("`", "").split(","):
        token = raw.strip()
        ids = BLOCK_ID_RE.findall(token)
        if len(ids) == 1 and token == ids[0]:
            expanded.append(ids[0])
        elif len(ids) == 2 and (".." in token or f"{ids[0]}-{ids[1]}" == token):
            start, end = ids
            if start in index and end in index and start[:5] == end[:5] and index[start] <= index[end]:
                expanded.extend(ordered_ids[index[start] : index[end] + 1])
            else:
                invalid.append(token)
        else:
            invalid.append(token)
    return expanded, invalid


def _page_sources(lock_text: str, ordered_ids: list[str]) -> tuple[dict[str, list[str]], list[str]]:
    pages: dict[str, list[str]] = {}
    invalid: list[str] = []
    for line in _section(lock_text, "page_sources"):
        match = re.match(r"^-\s+(P\d{2,3}):\s*(.+)$", line.strip())
        if not match:
            continue
        ids, bad = _expand_ids(match.group(2), ordered_ids)
        pages[match.group(1)] = ids
        invalid.extend(bad)
    return pages, invalid


def _design_pages(text: str, ordered_ids: list[str]) -> tuple[dict[str, dict[str, object]], list[str]]:
    pages: dict[str, dict[str, object]] = {}
    invalid: list[str] = []
    current: str | None = None
    in_outline = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_outline = bool(re.match(r"^##\s+IX\.", line, re.I))
            current = None
            continue
        if not in_outline:
            continue
        slide = SLIDE_RE.match(line)
        if slide:
            current = f"P{int(slide.group(1)):02d}"
            pages[current] = {"ids": [], "content": []}
            continue
        if not current:
            continue
        source_blocks = SOURCE_BLOCKS_RE.match(line)
        if source_blocks:
            ids, bad = _expand_ids(source_blocks.group(1), ordered_ids)
            pages[current]["ids"] = ids
            invalid.extend(bad)
        elif not re.match(r"^-\s+\*\*(?:Layout|Visualization|Source Blocks|Claims)\*\*:", line, re.I):
            pages[current]["content"].append(line)
    return pages, invalid


def _tokens(text: str) -> set[str]:
    text = re.sub(r"\\([\\.*_()\-])", r"\1", text)
    return {re.sub(r"\s+", "", token).lower() for token in NUMBER_RE.findall(text)}


def _numeric_mismatch_count(errors: list[str]) -> int:
    return sum(
        bool(re.search(r"\d", error)) and any(marker in error for marker in ("token mismatch", "formula", "numeric"))
        for error in errors
    )


def _load(project: Path) -> tuple[dict[str, object], list[dict[str, object]], list[str]]:
    inventory = json.loads((project / "source_inventory.json").read_text(encoding="utf-8"))
    blocks = inventory["blocks"]
    ids = [str(block["id"]) for block in blocks]
    return inventory, blocks, ids


def _fact_index(blocks: list[dict[str, object]]) -> dict[str, tuple[str, dict[str, object]]]:
    return {
        str(fact["id"]): (str(block["id"]), fact)
        for block in blocks
        for fact in block.get("facts", [])
    }


def _expected_facts(
    blocks: list[dict[str, object]], lock_pages: dict[str, list[str]]
) -> dict[str, dict[str, dict[str, object]]]:
    by_block = {str(block["id"]): block for block in blocks}
    return {
        page: {
            str(fact["id"]): fact
            for block_id in block_ids
            if block_id in by_block
            for fact in by_block[block_id].get("facts", [])
        }
        for page, block_ids in lock_pages.items()
    }


def validate_spec(project: Path, write_report: bool = True) -> dict[str, object]:
    inventory, blocks, ordered_ids = _load(project)
    by_id = {str(block["id"]): block for block in blocks}
    lock_text = (project / "spec_lock.md").read_text(encoding="utf-8")
    design_text = (project / "design_spec.md").read_text(encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []

    content_mode = "\n".join(_section(lock_text, "content_mode"))
    if not re.search(r"^-\s+mode:\s*faithful_report\s*$", content_mode, re.M):
        errors.append("spec_lock content_mode.mode must be faithful_report")
    if not re.search(r"^-\s+coverage_required:\s*100\s*$", content_mode, re.M):
        errors.append("spec_lock coverage_required must be 100")
    if not re.search(r"^-\s+source_inventory:\s*source_inventory\.json\s*$", content_mode, re.M):
        errors.append("spec_lock source_inventory must be source_inventory.json")

    exclusions = [block for block in blocks if not block.get("required", True)]
    for block in exclusions:
        if block.get("exclusion_reason") not in ALLOWED_EXCLUSIONS:
            errors.append(f"{block['id']}: invalid exclusion_reason")

    lock_pages, invalid = _page_sources(lock_text, ordered_ids)
    design_pages, design_invalid = _design_pages(design_text, ordered_ids)
    errors.extend(f"invalid source range: {token}" for token in invalid + design_invalid)
    if not lock_pages:
        errors.append("spec_lock page_sources is empty")
    for page, ids in lock_pages.items():
        design_ids = design_pages.get(page, {}).get("ids", [])
        if ids != design_ids:
            errors.append(f"{page}: design_spec Source Blocks do not match spec_lock page_sources")
    for page in sorted(set(design_pages) - set(lock_pages)):
        errors.append(f"{page}: design_spec slide missing from spec_lock page_sources")

    mapped = [block_id for ids in lock_pages.values() for block_id in ids]
    mapped_set = set(mapped)
    required_order = [str(block["id"]) for block in blocks if block.get("required", True)]
    required = set(required_order)
    missing = sorted(required - mapped_set)
    unknown = sorted(mapped_set - set(ordered_ids))
    if missing:
        errors.append(f"missing required blocks: {', '.join(missing)}")
    if unknown:
        errors.append(f"unknown blocks: {', '.join(unknown)}")
    duplicates = sorted(block_id for block_id, count in Counter(mapped).items() if count > 1)
    if duplicates:
        warnings.append(f"duplicate mappings: {', '.join(duplicates)}")
    first_occurrences: list[str] = []
    seen: set[str] = set()
    for page in sorted(lock_pages, key=lambda value: int(value[1:])):
        for block_id in lock_pages[page]:
            if block_id in required and block_id not in seen:
                first_occurrences.append(block_id)
                seen.add(block_id)
    if first_occurrences != required_order:
        errors.append("page_sources must preserve required source-block order")

    if (project / "claim_manifest.json").exists():
        warnings.append("legacy claim_manifest.json ignored by faithful_report V2")

    for page, page_data in design_pages.items():
        source_text = " ".join(str(by_id[block_id]["text"]) for block_id in page_data["ids"] if block_id in by_id)
        extra = sorted(_tokens("\n".join(page_data["content"])) - _tokens(source_text))
        if extra:
            errors.append(f"{page}: factual tokens not found in mapped source: {', '.join(extra)}")

    report = {
        "phase": "spec",
        "recommended_mode": inventory["profile"]["recommended_mode"],
        "required_blocks": len(required),
        "mapped_blocks": len(required & mapped_set),
        "coverage_percent": round(100 * len(required & mapped_set) / len(required), 2) if required else 100,
        "source_mapping_coverage": round(100 * len(required & mapped_set) / len(required), 2) if required else 100,
        "fact_fidelity": "pass" if not errors else "fail",
        "unsupported_claims": sum("factual tokens" in error for error in errors),
        "numeric_mismatches": _numeric_mismatch_count(errors),
        "chart_mismatches": sum("chart" in error.lower() for error in errors),
        "layout_errors": 0,
        "render_backend": None,
        "release_status": "DRAFT",
        "facts_expected": sum(len(facts) for facts in _expected_facts(blocks, lock_pages).values()),
        "facts_rendered": 0,
        "excluded_blocks": [block["id"] for block in exclusions],
        "duplicates": duplicates,
        "errors": errors,
        "warnings": warnings,
        "status": "pass" if not errors else "fail",
    }
    if write_report:
        (project / "coverage_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _svg_page(path: Path) -> str | None:
    match = re.search(r"(?:^|_)(\d{1,3})(?:_|\.|$)", path.name)
    return f"P{int(match.group(1)):02d}" if match else None


def validate_svg(project: Path) -> dict[str, object]:
    spec_report = validate_spec(project, write_report=False)
    _, blocks, ordered_ids = _load(project)
    by_block = {str(block["id"]): block for block in blocks}
    by_fact = _fact_index(blocks)
    lock_text = (project / "spec_lock.md").read_text(encoding="utf-8")
    lock_pages, _ = _page_sources(lock_text, ordered_ids)
    chart_pages = {
        match.group(1)
        for line in _section(lock_text, "page_charts")
        if (match := re.match(r"^\s*-\s+(P\d{2,3}):", line))
    }
    expected_facts = _expected_facts(blocks, lock_pages)
    expected_pages: dict[str, set[str]] = defaultdict(set)
    for page, ids in lock_pages.items():
        for block_id in ids:
            expected_pages[block_id].add(page)
    found_ids: set[str] = set()
    found_page: dict[str, set[str]] = defaultdict(set)
    fact_text: dict[tuple[str, str], list[str]] = defaultdict(list)
    found_assets: set[tuple[str, str]] = set()
    errors = list(spec_report["errors"])
    warnings = list(spec_report["warnings"])

    def parse_fact_ids(raw: str) -> tuple[list[str], list[str]]:
        values = [value.strip() for value in raw.split(",") if value.strip()]
        return [value for value in values if FACT_ID_RE.fullmatch(value)], [value for value in values if not FACT_ID_RE.fullmatch(value)]

    def walk(
        elem: ET.Element,
        svg_name: str,
        page: str | None,
        inherited_sources: list[str],
        inherited_facts: list[str],
        inherited_kind: str,
    ) -> None:
        sources = inherited_sources
        if elem.get("data-source-ids"):
            sources, bad = _expand_ids(str(elem.get("data-source-ids")), ordered_ids)
            errors.extend(f"{svg_name}: invalid data-source-ids token {token}" for token in bad)
            for block_id in sources:
                if block_id not in by_block:
                    errors.append(f"{svg_name}: unknown source id {block_id}")
                elif not page or block_id not in lock_pages.get(page, []):
                    errors.append(f"{svg_name}: {block_id} is not mapped to {page or '<unknown page>'}")
                else:
                    found_ids.add(block_id)
                    found_page[block_id].add(page)
        fact_ids = inherited_facts
        if elem.get("data-fact-ids"):
            fact_ids, bad_facts = parse_fact_ids(str(elem.get("data-fact-ids")))
            errors.extend(f"{svg_name}: invalid data-fact-ids token {token}" for token in bad_facts)
            for fact_id in fact_ids:
                if fact_id not in by_fact:
                    errors.append(f"{svg_name}: unknown fact id {fact_id}")
                    continue
                block_id = by_fact[fact_id][0]
                if block_id not in sources:
                    errors.append(f"{svg_name}: {fact_id} does not belong to data-source-ids")
                if not page or fact_id not in expected_facts.get(page, {}):
                    errors.append(f"{svg_name}: {fact_id} is not mapped to {page or '<unknown page>'}")
        content_kind = str(elem.get("data-content-kind") or inherited_kind)
        tag = elem.tag.rsplit("}", 1)[-1]
        if tag == "image" and content_kind == "source_asset" and page:
            for block_id in sources:
                if block_id in by_block and by_block[block_id]["kind"] == "image":
                    found_assets.add((page, block_id))
                elif block_id in by_block:
                    errors.append(f"{svg_name}: source_asset {block_id} is not an image block")
        if tag == "text":
            visible = " ".join(part.strip() for part in elem.itertext() if part.strip())
            if visible and content_kind == "page_number" and not re.fullmatch(r"\s*\d+(?:\s*/\s*\d+)?\s*", visible):
                errors.append(f"{svg_name}: invalid page_number chrome text: {visible[:80]}")
            elif visible and content_kind == "brand_chrome" and set(_token_counter(visible)) - {"viettel"}:
                errors.append(f"{svg_name}: unsupported brand_chrome text: {visible[:80]}")
            elif visible and content_kind == "source_asset":
                errors.append(f"{svg_name}: source_asset may not exempt visible text: {visible[:80]}")
            elif visible and content_kind not in CHROME_KINDS:
                if len(fact_ids) != 1:
                    errors.append(f"{svg_name}: visible text must resolve to exactly one data-fact-ids value: {visible[:80]}")
                elif page and fact_ids[0] in expected_facts.get(page, {}):
                    fact_text[(page, fact_ids[0])].append(visible)
        for child in elem:
            walk(child, svg_name, page, sources, fact_ids, content_kind)

    for svg in sorted((project / "svg_output").glob("*.svg")):
        page = _svg_page(svg)
        try:
            root = ET.parse(svg).getroot()
        except ET.ParseError as exc:
            errors.append(f"{svg.name}: invalid XML: {exc}")
            continue
        if not page:
            errors.append(f"{svg.name}: cannot resolve page number from filename")
        walk(root, svg.name, page, [], [], "")

    required = {str(block["id"]) for block in blocks if block.get("required", True)}
    missing = sorted(required - found_ids)
    if missing:
        errors.append(f"SVG missing required blocks: {', '.join(missing)}")
    for block_id, pages in found_page.items():
        if block_id in expected_pages and pages != expected_pages[block_id]:
            errors.append(f"{block_id}: annotated on {sorted(pages)}, expected {sorted(expected_pages[block_id])}")
    expected_assets = {
        (page, block_id)
        for page, block_ids in lock_pages.items()
        for block_id in block_ids
        if block_id in by_block and by_block[block_id]["kind"] == "image"
    }
    for page, block_id in sorted(expected_assets - found_assets):
        errors.append(f"{page}:{block_id}: SVG missing source asset")

    matched_facts = 0
    for page, facts in expected_facts.items():
        for fact_id, fact in facts.items():
            visible = " ".join(fact_text.get((page, fact_id), []))
            expected = str(fact["source_span"])
            expected_tokens = _token_counter(expected)
            visible_tokens = _token_counter(visible)
            if visible_tokens == expected_tokens:
                matched_facts += 1
                continue
            missing_tokens = list((expected_tokens - visible_tokens).elements())
            extra_tokens = list((visible_tokens - expected_tokens).elements())
            prefix = "chart " if page in chart_pages else ""
            errors.append(f"{page}:{fact_id}: SVG {prefix}fact token mismatch; missing={missing_tokens}, extra={extra_tokens}")

    facts_expected = sum(len(facts) for facts in expected_facts.values())

    report = {
        "phase": "svg",
        "required_blocks": len(required),
        "rendered_blocks": len(required & found_ids),
        "coverage_percent": round(100 * len(required & found_ids) / len(required), 2) if required else 100,
        "source_mapping_coverage": round(100 * len(required & found_ids) / len(required), 2) if required else 100,
        "fact_fidelity": "pass" if not errors else "fail",
        "unsupported_claims": sum(
            any(marker in error for marker in ("visible text", "fact token mismatch", "unsupported brand_chrome"))
            for error in errors
        ),
        "numeric_mismatches": _numeric_mismatch_count(errors),
        "chart_mismatches": sum("chart" in error.lower() for error in errors),
        "layout_errors": 0,
        "render_backend": None,
        "release_status": "DRAFT",
        "facts_expected": facts_expected,
        "facts_rendered": matched_facts,
        "errors": errors,
        "warnings": warnings,
        "status": "pass" if not errors else "fail",
    }
    (project / "coverage_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def renderer_candidates(
    system: str | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> list[tuple[str, str]]:
    system = system or platform.system()
    candidates: list[tuple[str, str]] = []
    if system == "Windows":
        powershell = which("powershell") or which("pwsh")
        if powershell:
            candidates.append(("microsoft_powerpoint", str(powershell)))
    elif system == "Darwin":
        osascript = which("osascript")
        if osascript:
            candidates.append(("microsoft_powerpoint", str(osascript)))
    soffice = which("libreoffice") or which("soffice")
    if soffice:
        candidates.append(("libreoffice", str(soffice)))
    return candidates


def _render_windows(executable: str, pptx: Path, pdf: Path, work: Path) -> str:
    script = work / "render_powerpoint.ps1"
    script.write_text(
        "param([string]$InputPath,[string]$OutputPath)\n"
        "$app = New-Object -ComObject PowerPoint.Application\n"
        "try {\n"
        "  $deck = $app.Presentations.Open($InputPath, $true, $false, $false)\n"
        "  $deck.SaveAs($OutputPath, 32)\n"
        "  Write-Output $app.Version\n"
        "} finally {\n"
        "  if ($deck) { $deck.Close() }\n"
        "  $app.Quit()\n"
        "}\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [executable, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(script), str(pptx), str(pdf)],
        capture_output=True, text=True, timeout=180, check=True,
    )
    return result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "unknown"


def _render_macos(executable: str, pptx: Path, pdf: Path, work: Path) -> str:
    script = work / "render_powerpoint.applescript"
    script.write_text(
        "on run argv\n"
        "  set inputPath to item 1 of argv\n"
        "  set outputPath to item 2 of argv\n"
        "  set inputFile to POSIX file inputPath\n"
        "  set outputFile to POSIX file outputPath\n"
        "  tell application \"Microsoft PowerPoint\"\n"
        "    open inputFile\n"
        "    set deck to active presentation\n"
        "    save deck in outputFile as save as PDF\n"
        "    close deck saving no\n"
        "    return version\n"
        "  end tell\n"
        "end run\n",
        encoding="utf-8",
    )
    result = subprocess.run([executable, str(script), str(pptx), str(pdf)], capture_output=True, text=True, timeout=180, check=True)
    return result.stdout.strip() or "unknown"


def _render_libreoffice(executable: str, pptx: Path, pdf: Path, work: Path) -> str:
    profile = work / "lo-profile"
    profile.mkdir()
    result = subprocess.run(
        [executable, f"-env:UserInstallation={profile.resolve().as_uri()}", "--headless", "--convert-to", "pdf", "--outdir", str(work), str(pptx)],
        capture_output=True, text=True, timeout=180, check=True,
    )
    generated = work / f"{pptx.stem}.pdf"
    if not generated.exists():
        raise RuntimeError(result.stderr.strip() or "LibreOffice did not produce a PDF")
    shutil.copy2(generated, pdf)
    version = subprocess.run([executable, "--version"], capture_output=True, text=True, timeout=15, check=False)
    return version.stdout.strip() or "unknown"


def _pptx_page_count(pptx: Path) -> int:
    with zipfile.ZipFile(pptx) as archive:
        return sum(bool(re.fullmatch(r"ppt/slides/slide\d+\.xml", name)) for name in archive.namelist())


def _pdf_page_count(pdf: Path) -> int:
    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo:
        result = subprocess.run([pdfinfo, str(pdf)], capture_output=True, text=True, timeout=30, check=True)
        match = re.search(r"^Pages:\s*(\d+)", result.stdout, re.M)
        if match:
            return int(match.group(1))
    return len(re.findall(rb"/Type\s*/Page\b", pdf.read_bytes()))


def _render_previews(pdf: Path, output: Path) -> list[str]:
    output.mkdir(parents=True, exist_ok=True)
    for stale in [*output.glob("page-*.png"), output / "montage.png"]:
        if stale.exists():
            stale.unlink()
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        return []
    prefix = output / "page"
    subprocess.run([pdftoppm, "-png", "-r", "100", str(pdf), str(prefix)], capture_output=True, text=True, timeout=180, check=True)
    pages = sorted(output.glob("page-*.png"))
    magick = shutil.which("magick")
    if magick and pages:
        subprocess.run([magick, "montage", *map(str, pages), "-thumbnail", "320x180", "-tile", "4x", "-geometry", "+8+8", str(output / "montage.png")], capture_output=True, text=True, timeout=180, check=False)
    return [str(page) for page in pages]


def _pdf_text_presence(project: Path, pdf: Path) -> tuple[str, list[str]]:
    pdftotext = shutil.which("pdftotext")
    if not pdftotext or not (project / "source_inventory.json").exists() or not (project / "spec_lock.md").exists():
        return "unavailable", []
    result = subprocess.run([pdftotext, str(pdf), "-"], capture_output=True, text=True, timeout=60, check=True)
    _, blocks, ordered_ids = _load(project)
    lock_pages, _ = _page_sources((project / "spec_lock.md").read_text(encoding="utf-8"), ordered_ids)
    expected = _expected_facts(blocks, lock_pages)
    pages = result.stdout.rstrip("\f\n").split("\f")
    ordered_pages = sorted(lock_pages, key=lambda value: int(value[1:]))
    missing: list[str] = []
    if len(pages) == len(ordered_pages):
        for page, text in zip(ordered_pages, pages):
            visible = _token_counter(text)
            for fact_id, fact in expected.get(page, {}).items():
                tokens = _token_counter(str(fact["source_span"]))
                if tokens - visible:
                    missing.append(f"{page}:{fact_id}")
                else:
                    visible -= tokens
    else:
        visible = _token_counter(result.stdout)
        for page in ordered_pages:
            for fact_id, fact in expected.get(page, {}).items():
                tokens = _token_counter(str(fact["source_span"]))
                if tokens - visible:
                    missing.append(f"{page}:{fact_id}")
                else:
                    visible -= tokens
    return ("fail", missing) if missing else ("pass", [])


def _status_copy(pptx: Path, status: str, output_dir: Path | None = None) -> Path:
    stem = re.sub(r"_(?:DRAFT|REVIEW|FINAL)$", "", pptx.stem, flags=re.I)
    target_dir = output_dir or pptx.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    output = target_dir / f"{stem}_{status}.pptx"
    if pptx.resolve() != output.resolve():
        shutil.copy2(pptx, output)
    return output


def _sync_coverage(project: Path, render_report: dict[str, object]) -> None:
    path = project / "coverage_report.json"
    coverage = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    coverage.update(
        {
            "layout_errors": len(render_report.get("layout_errors", [])),
            "render_backend": render_report.get("backend"),
            "release_status": render_report.get("release_status", "DRAFT"),
        }
    )
    path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_check(project: Path, pptx: Path, fast: bool = False) -> dict[str, object]:
    if not pptx.exists():
        raise ValueError(f"PPTX does not exist: {pptx}")
    expected = _pptx_page_count(pptx)
    report: dict[str, object] = {
        "platform": platform.system(), "backend": None, "backend_version": None,
        "pages_expected": expected, "pages_rendered": 0, "text_presence": "not_run",
        "missing_facts": [], "visual_review": "pending", "layout_errors": [],
        "fallbacks": [], "errors": [], "release_status": "DRAFT",
    }
    try:
        content_report = validate_svg(project)
        if content_report["status"] != "pass":
            report["errors"] = ["content/SVG gate failed before render"]
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        report["errors"] = [f"content/SVG gate unavailable: {exc}"]
    if fast:
        report["errors"].append("render gate skipped by --fast")  # type: ignore[union-attr]
        report["output_pptx"] = str(_status_copy(pptx, "DRAFT", project / "exports"))
        (project / "render_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _sync_coverage(project, report)
        return report

    if report["errors"]:
        report["output_pptx"] = str(_status_copy(pptx, "DRAFT", project / "exports"))
        (project / "render_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _sync_coverage(project, report)
        return report

    candidates = renderer_candidates()
    if not candidates:
        report["errors"] = ["no supported renderer found; install Microsoft PowerPoint or LibreOffice"]
        report["output_pptx"] = str(_status_copy(pptx, "DRAFT", project / "exports"))
        (project / "render_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _sync_coverage(project, report)
        return report

    render_root = project / "render_output"
    render_root.mkdir(parents=True, exist_ok=True)
    pdf = render_root / "rendered.pdf"
    for backend, executable in candidates:
        if pdf.exists():
            pdf.unlink()
        try:
            with tempfile.TemporaryDirectory(prefix="faithful-render-") as temp:
                work = Path(temp)
                if backend == "microsoft_powerpoint" and platform.system() == "Windows":
                    version = _render_windows(executable, pptx.resolve(), pdf.resolve(), work)
                elif backend == "microsoft_powerpoint":
                    version = _render_macos(executable, pptx.resolve(), pdf.resolve(), work)
                else:
                    version = _render_libreoffice(executable, pptx.resolve(), pdf.resolve(), work)
            report["backend"] = backend
            report["backend_version"] = version
            break
        except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
            if pdf.exists():
                pdf.unlink()
            report["fallbacks"].append(f"{backend}: {exc}")  # type: ignore[union-attr]
    if not pdf.exists():
        report["errors"] = ["all render backends failed"]
        report["output_pptx"] = str(_status_copy(pptx, "DRAFT", project / "exports"))
    else:
        rendered = _pdf_page_count(pdf)
        text_presence, missing_facts = _pdf_text_presence(project, pdf)
        pages = _render_previews(pdf, render_root / "pages")
        report.update(
            {
                "pages_rendered": rendered,
                "text_presence": text_presence,
                "missing_facts": missing_facts,
                "pdf": str(pdf),
                "preview_pages": pages,
                "montage": str(render_root / "pages/montage.png") if (render_root / "pages/montage.png").exists() else None,
            }
        )
        if rendered != expected:
            report["errors"].append(f"rendered {rendered} pages, expected {expected}")  # type: ignore[union-attr]
        if text_presence == "fail":
            report["errors"].append(f"rendered output is missing facts: {', '.join(missing_facts)}")  # type: ignore[union-attr]
        report["output_pptx"] = str(_status_copy(pptx, "DRAFT", project / "exports"))
    (project / "render_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _sync_coverage(project, report)
    return report


def render_review(project: Path, passed: bool, layout_errors: list[str]) -> dict[str, object]:
    path = project / "render_report.json"
    if not path.exists():
        raise ValueError("render_report.json is missing; run render-check first")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("backend") is None or report.get("errors"):
        raise ValueError("render-check has not passed; REVIEW is not allowed")
    report["visual_review"] = "pass" if passed else "fail"
    report["layout_errors"] = layout_errors
    report["release_status"] = "REVIEW" if passed and not layout_errors else "DRAFT"
    source = Path(str(report["output_pptx"]))
    report["output_pptx"] = str(_status_copy(source, str(report["release_status"])))
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _sync_coverage(project, report)
    return report


def approve_final(project: Path) -> dict[str, object]:
    path = project / "render_report.json"
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("release_status") != "REVIEW":
        raise ValueError("only a REVIEW deck can be approved as FINAL")
    report["release_status"] = "FINAL"
    report["output_pptx"] = str(_status_copy(Path(str(report["output_pptx"])), "FINAL"))
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _sync_coverage(project, report)
    return report


def _print_report(report: dict[str, object]) -> int:
    print(f"[{report['status'].upper()}] {report['phase']} coverage={report['coverage_percent']}%")
    for warning in report["warnings"]:
        print(f"  warning: {warning}")
    for error in report["errors"]:
        print(f"  error: {error}")
    return 0 if report["status"] == "pass" else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("project", type=Path)
    prepare_parser.add_argument("sources", nargs="*", type=Path)
    for name in ("validate-spec", "validate-svg", "validate"):
        command = sub.add_parser(name)
        command.add_argument("project", type=Path)
    render_parser = sub.add_parser("render-check")
    render_parser.add_argument("project", type=Path)
    render_parser.add_argument("pptx", type=Path)
    render_parser.add_argument("--fast", action="store_true")
    review_parser = sub.add_parser("render-review")
    review_parser.add_argument("project", type=Path)
    review_group = review_parser.add_mutually_exclusive_group(required=True)
    review_group.add_argument("--pass", dest="passed", action="store_true")
    review_group.add_argument("--fail", dest="passed", action="store_false")
    review_parser.add_argument("--layout-error", action="append", default=[])
    final_parser = sub.add_parser("approve-final")
    final_parser.add_argument("project", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare(args.project, args.sources)
            return
        if args.command == "validate-spec":
            raise SystemExit(_print_report(validate_spec(args.project)))
        if args.command == "validate-svg":
            raise SystemExit(_print_report(validate_svg(args.project)))
        if args.command == "render-check":
            report = render_check(args.project, args.pptx, args.fast)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return
        if args.command == "render-review":
            report = render_review(args.project, args.passed, args.layout_error)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return
        if args.command == "approve-final":
            report = approve_final(args.project)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return
        spec_code = _print_report(validate_spec(args.project))
        svg_code = _print_report(validate_svg(args.project))
        raise SystemExit(max(spec_code, svg_code))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
