#!/usr/bin/env python3
"""Experimental chapter-parallel generation planner and validator.

This tool does not generate SVG pages. It creates deterministic work packages
for hand-written SVG generation and validates the resulting svg_output/ before
export.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from update_spec import parse_lock
except ImportError:  # pragma: no cover - fallback for unusual invocation paths
    parse_lock = None

try:
    from svg_quality_checker import SVGQualityChecker
except ImportError:  # pragma: no cover
    SVGQualityChecker = None


SLIDE_HEADING_RE = re.compile(
    r"^#{3,6}\s+Slide\s+(\d{1,3})\s+(?:[-\u2013\u2014])\s+(.+?)\s*$",
    re.MULTILINE,
)


@dataclass
class PageContract:
    key: str
    number: int
    title: str
    role: str
    group_id: str
    rhythm: str = ""
    layout: str = ""
    chart: str = ""
    outline: str = ""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_spec_lock(lock_path: Path) -> dict[str, dict[str, str]]:
    if parse_lock is not None:
        return parse_lock(lock_path)

    sections: dict[str, dict[str, str]] = {}
    current: str | None = None
    for raw in _read_text(lock_path).splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            current = line[3:].strip()
            sections.setdefault(current, {})
            continue
        if current is None:
            continue
        m = re.match(r"^-\s+([A-Za-z0-9_]+)\s*:\s*(.+?)\s*$", line)
        if m:
            sections[current][m.group(1)] = m.group(2)
    return sections


def _extract_slide_blocks(design_spec: str) -> dict[int, tuple[str, str]]:
    matches = list(SLIDE_HEADING_RE.finditer(design_spec))
    slides: dict[int, tuple[str, str]] = {}
    for idx, match in enumerate(matches):
        number = int(match.group(1))
        title = match.group(2).strip()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(design_spec)
        block = design_spec[match.start():end].strip()
        slides[number] = (title, block)
    return slides


def _extract_page_count(design_spec: str) -> int | None:
    patterns = [
        r"\*\*Page Count\*\*\s*\|\s*(\d+)",
        r"\bPage Count\b[^|\n]*\|\s*(\d+)",
        r"\bpages?\s*[:=]\s*(\d+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, design_spec, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None


def _extract_expected_numbers(
    project: Path,
    design_spec: str,
    lock: dict[str, dict[str, str]],
) -> list[int]:
    slide_blocks = _extract_slide_blocks(design_spec)
    if slide_blocks:
        return sorted(slide_blocks)

    rhythm = lock.get("page_rhythm", {})
    lock_numbers = sorted(
        int(m.group(1))
        for key in rhythm
        if (m := re.fullmatch(r"P(\d{2,3})", key.strip(), re.IGNORECASE))
    )
    if lock_numbers:
        return lock_numbers

    count = _extract_page_count(design_spec)
    if count:
        return list(range(1, count + 1))

    svg_dir = project / "svg_output"
    svg_numbers = sorted(
        int(m.group(1))
        for path in svg_dir.glob("*.svg")
        if (m := re.match(r"^(\d{2,3})(?:[_-].*)?\.svg$", path.name))
    )
    return svg_numbers


def _classify_page(
    number: int,
    title: str,
    rhythm: str,
    layout: str,
    *,
    is_last: bool,
) -> str:
    title_l = title.lower()
    layout_l = layout.lower()
    rhythm_l = rhythm.lower()

    if number == 1 or "cover" in title_l or layout_l.startswith("01_cover"):
        return "cover"
    if (
        "agenda" in title_l
        or "table of contents" in title_l
        or "toc" in title_l
        or "toc" in layout_l
        or "tong quan noi dung" in title_l
        or "tổng quan nội dung" in title_l
    ):
        return "toc"
    if is_last and any(
        token in title_l
        for token in (
            "ending",
            "closing",
            "thank",
            "key takeaways",
            "takeaways",
            "recommendation",
            "recommendations",
            "ket luan",
            "kết luận",
            "bai hoc",
            "bài học",
        )
    ):
        return "ending"
    if (
        "section divider" in title_l
        or "chapter" in title_l
        or "divider" in layout_l
        or layout_l.startswith("02")
        or (rhythm_l == "breathing" and "section" in title_l)
    ):
        return "chapter"
    return "content"


def _build_groups(pages: list[PageContract]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    def add_group(kind: str, page: PageContract, *, standalone: bool) -> dict[str, Any]:
        group_id = f"g{len(groups) + 1:02d}-{kind}-{page.key.lower()}"
        group = {
            "id": group_id,
            "kind": kind,
            "pages": [],
            "parallel_eligible": not standalone,
            "internal_order": "serial",
        }
        groups.append(group)
        return group

    for page in pages:
        if page.role in {"cover", "toc", "ending"}:
            current = None
            group = add_group(page.role, page, standalone=True)
            group["pages"].append(page.key)
            page.group_id = group["id"]
            continue

        if page.role == "chapter":
            current = add_group("chapter", page, standalone=False)
        elif current is None:
            current = add_group("intro", page, standalone=False)

        current["pages"].append(page.key)
        page.group_id = current["id"]

    return groups


def _build_page_contracts(project: Path) -> tuple[list[PageContract], list[dict[str, Any]]]:
    design_path = project / "design_spec.md"
    lock_path = project / "spec_lock.md"
    if not design_path.exists():
        raise FileNotFoundError(f"design_spec.md not found: {design_path}")
    if not lock_path.exists():
        raise FileNotFoundError(f"spec_lock.md not found: {lock_path}")

    design_spec = _read_text(design_path)
    lock = _load_spec_lock(lock_path)
    slide_blocks = _extract_slide_blocks(design_spec)
    numbers = _extract_expected_numbers(project, design_spec, lock)
    if not numbers:
        raise ValueError("Could not infer expected page roster from design_spec.md, spec_lock.md, or svg_output/")

    rhythm_map = lock.get("page_rhythm", {})
    layout_map = lock.get("page_layouts", {})
    chart_map = lock.get("page_charts", {})
    last_number = max(numbers)

    pages: list[PageContract] = []
    for number in numbers:
        key = f"P{number:02d}"
        title, outline = slide_blocks.get(number, ("", ""))
        rhythm = rhythm_map.get(key, "")
        layout = layout_map.get(key, "")
        chart = chart_map.get(key, "")
        role = _classify_page(number, title, rhythm, layout, is_last=number == last_number)
        pages.append(
            PageContract(
                key=key,
                number=number,
                title=title,
                role=role,
                group_id="",
                rhythm=rhythm,
                layout=layout,
                chart=chart,
                outline=outline,
            )
        )

    groups = _build_groups(pages)
    return pages, groups


def _write_context(
    project: Path,
    out_dir: Path,
    pages: list[PageContract],
    groups: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> None:
    contracts_dir = out_dir / "page_contracts"
    contracts_dir.mkdir(parents=True, exist_ok=True)

    spec_lock_text = _read_text(project / "spec_lock.md")
    (out_dir / "spec_lock_snapshot.md").write_text(spec_lock_text, encoding="utf-8")

    context_lines = [
        "# Parallel Generation Context",
        "",
        f"- Project: `{project.name}`",
        "- Mode: `chapter_parallel`",
        f"- Concurrency: `{manifest['concurrency']}`",
        "- SVG generation remains hand-written; this planner only splits work.",
        "- Cover, TOC/agenda, and ending packages are standalone.",
        "- Chapter packages may run concurrently; pages inside one package stay serial.",
        "",
        "## Groups",
        "",
    ]
    for group in groups:
        eligible = "yes" if group["parallel_eligible"] else "no"
        context_lines.append(
            f"- `{group['id']}` ({group['kind']}, parallel_eligible={eligible}): "
            + ", ".join(group["pages"])
        )
    context_lines.extend(
        [
            "",
            "## Quality Gates",
            "",
            "- After each page: `python3 scripts/svg_quality_checker.py <project_path>/svg_output/<page_file>.svg`",
            "- After all pages: `python3 scripts/svg_quality_checker.py <project_path>`",
            "- Before export: `python3 scripts/parallel_generation.py validate <project_path>`",
            "",
        ]
    )
    (out_dir / "parallel_context.md").write_text("\n".join(context_lines), encoding="utf-8")

    for page in pages:
        contract = [
            f"# Page Contract {page.key}",
            "",
            f"- Expected SVG prefix: `{page.number:02d}_`",
            f"- Group: `{page.group_id}`",
            f"- Role: `{page.role}`",
            f"- Rhythm: `{page.rhythm or 'unspecified'}`",
            f"- Layout template: `{page.layout or 'none'}`",
            f"- Chart template: `{page.chart or 'none'}`",
            "",
            "## Required Rules",
            "",
            "- Re-read `<project_path>/spec_lock.md` before writing this page.",
            "- Cross-check with `parallel_generation/spec_lock_snapshot.md`.",
            "- Hand-write SVG; do not script-generate page markup.",
            "- Run the per-page SVG quality checker before advancing.",
            "",
            "## Outline Excerpt",
            "",
            page.outline or "_No slide outline excerpt found in design_spec.md._",
            "",
        ]
        (contracts_dir / f"{page.key}.md").write_text("\n".join(contract), encoding="utf-8")


def cmd_plan(args: argparse.Namespace) -> int:
    project = args.project_path.resolve()
    if not project.exists():
        print(f"[ERROR] Project path does not exist: {project}")
        return 1
    if args.concurrency < 1 or args.concurrency > 8:
        print("[ERROR] --concurrency must be between 1 and 8")
        return 1

    pages, groups = _build_page_contracts(project)
    out_dir = project / "parallel_generation"
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "version": 1,
        "mode": "chapter_parallel",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project": project.name,
        "concurrency": args.concurrency,
        "source_hashes": {
            "design_spec.md": _sha256(project / "design_spec.md"),
            "spec_lock.md": _sha256(project / "spec_lock.md"),
        },
        "expected_pages": [page.key for page in pages],
        "expected_svg_prefixes": [f"{page.number:02d}_" for page in pages],
        "groups": groups,
        "pages": [asdict(page) for page in pages],
    }

    _write_context(project, out_dir, pages, groups, manifest)
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"[OK] Wrote parallel generation plan: {out_dir}")
    print(f"[OK] Pages: {len(pages)} | Groups: {len(groups)} | Concurrency: {args.concurrency}")
    for group in groups:
        eligible = "parallel" if group["parallel_eligible"] else "standalone"
        print(f"  - {group['id']} [{eligible}]: {', '.join(group['pages'])}")
    return 0


def _load_manifest(project: Path) -> dict[str, Any]:
    manifest_path = project / "parallel_generation" / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"parallel_generation/manifest.json not found. Run `parallel_generation.py plan {project}` first."
        )
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _discover_svg_numbers(svg_dir: Path) -> dict[int, list[Path]]:
    numbers: dict[int, list[Path]] = {}
    for path in sorted(svg_dir.glob("*.svg")):
        m = re.match(r"^(\d{2,3})(?:[_-].*)?\.svg$", path.name)
        if not m:
            continue
        numbers.setdefault(int(m.group(1)), []).append(path)
    return numbers


def _validate_structure(project: Path, manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    svg_dir = project / "svg_output"
    if not svg_dir.exists():
        return [f"svg_output/ not found: {svg_dir}"]

    expected_pages = manifest.get("expected_pages") or []
    expected_numbers = [
        int(str(page).replace("P", "").replace("p", ""))
        for page in expected_pages
        if re.fullmatch(r"[Pp]\d{2,3}", str(page))
    ]
    if not expected_numbers:
        errors.append("manifest has no expected_pages roster")
        return errors

    by_number = _discover_svg_numbers(svg_dir)
    unnumbered = [
        path.name
        for path in sorted(svg_dir.glob("*.svg"))
        if not re.match(r"^(\d{2,3})(?:[_-].*)?\.svg$", path.name)
    ]
    if unnumbered:
        errors.append(
            "unnumbered SVG file(s) in svg_output/: " + ", ".join(unnumbered)
        )

    for number in expected_numbers:
        paths = by_number.get(number, [])
        if not paths:
            errors.append(f"missing SVG for P{number:02d} (expected prefix {number:02d}_)")
        elif len(paths) > 1:
            joined = ", ".join(path.name for path in paths)
            errors.append(f"duplicate SVGs for P{number:02d}: {joined}")

    extra = sorted(set(by_number) - set(expected_numbers))
    for number in extra:
        joined = ", ".join(path.name for path in by_number[number])
        errors.append(f"unexpected extra SVG number {number:02d}: {joined}")

    ordered_numbers = []
    for path in sorted(svg_dir.glob("*.svg")):
        m = re.match(r"^(\d{2,3})(?:[_-].*)?\.svg$", path.name)
        if m:
            ordered_numbers.append(int(m.group(1)))
    if ordered_numbers != expected_numbers:
        errors.append(
            "SVG filename order does not match manifest expected_pages: "
            f"found {ordered_numbers}, expected {expected_numbers}"
        )

    return errors


def _validate_snapshots(project: Path, manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_hashes = manifest.get("source_hashes") or {}
    lock_path = project / "spec_lock.md"
    snapshot_path = project / "parallel_generation" / "spec_lock_snapshot.md"

    if not snapshot_path.exists():
        errors.append("spec_lock snapshot missing: parallel_generation/spec_lock_snapshot.md")
    elif snapshot_path.read_text(encoding="utf-8") != lock_path.read_text(encoding="utf-8"):
        errors.append("spec_lock.md differs from parallel_generation/spec_lock_snapshot.md; rerun plan or resolve drift")

    current_lock_hash = _sha256(lock_path)
    if expected_hashes.get("spec_lock.md") and current_lock_hash != expected_hashes["spec_lock.md"]:
        errors.append("spec_lock.md hash differs from manifest source_hashes; rerun plan after intentional spec changes")

    design_path = project / "design_spec.md"
    current_design_hash = _sha256(design_path)
    if expected_hashes.get("design_spec.md") and current_design_hash != expected_hashes["design_spec.md"]:
        errors.append("design_spec.md hash differs from manifest source_hashes; rerun plan after intentional spec changes")

    return errors


def _run_quality_checker(project: Path) -> int:
    if SVGQualityChecker is None:
        print("[ERROR] Could not import SVGQualityChecker")
        return 1
    checker = SVGQualityChecker()
    checker.check_directory(str(project))
    checker.print_summary()
    return 1 if checker.summary["errors"] > 0 else 0


def cmd_validate(args: argparse.Namespace) -> int:
    project = args.project_path.resolve()
    try:
        manifest = _load_manifest(project)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[ERROR] {exc}")
        return 1

    errors = []
    errors.extend(_validate_snapshots(project, manifest))
    errors.extend(_validate_structure(project, manifest))

    if errors:
        print("[ERROR] Parallel generation structural validation failed:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("[OK] Parallel generation structure and snapshots passed")

    quality_rc = _run_quality_checker(project)
    if quality_rc != 0:
        errors.append("svg_quality_checker.py reported errors")

    if errors:
        print("[ERROR] Parallel generation validate failed")
        return 1
    print("[OK] Parallel generation validate passed")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="create chapter-parallel work packages")
    plan.add_argument("project_path", type=Path)
    plan.add_argument("--concurrency", type=int, default=2)
    plan.set_defaults(func=cmd_plan)

    validate = sub.add_parser("validate", help="validate output after chapter-parallel generation")
    validate.add_argument("project_path", type=Path)
    validate.set_defaults(func=cmd_validate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
