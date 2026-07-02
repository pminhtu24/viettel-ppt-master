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
import shutil
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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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
        m = re.match(r"^-\s+([A-Za-z0-9_-]+)\s*:\s*(.+?)\s*$", line)
        if m:
            sections[current][m.group(1)] = m.group(2)
    return sections


def _parse_package_pages(raw_value: str) -> list[str]:
    scope = raw_value.split("|", 1)[0]
    scope = re.sub(r"\([^)]*\)", "", scope)
    pages: list[str] = []

    for match in re.finditer(
        r"[Pp]?(\d{1,3})(?:\s*[-\u2013\u2014]\s*[Pp]?(\d{1,3}))?",
        scope,
    ):
        start = int(match.group(1))
        end = int(match.group(2) or match.group(1))
        if end < start:
            raise ValueError(f"Invalid descending page range in generation_packages: {raw_value!r}")
        for number in range(start, end + 1):
            key = f"P{number:02d}"
            if key not in pages:
                pages.append(key)

    if not pages:
        raise ValueError(f"Could not parse page list in generation_packages value: {raw_value!r}")
    return pages


def _parse_package_runtime(raw_value: str) -> bool | None:
    if "|" not in raw_value:
        return None
    hints = {part.strip().lower().replace("-", "_") for part in raw_value.split("|")[1:]}
    if hints & {"main", "main_agent", "main_agent_package", "mainagent"}:
        return False
    if hints & {"subagent", "sub_agent", "parallel", "spawn"}:
        return True
    return None


def _infer_package_kind(package_id: str, page_keys: list[str], page_by_key: dict[str, PageContract]) -> str:
    slug = re.sub(r"^g\d+[-_]*", "", package_id.lower()).strip("-_")
    if slug:
        return slug.replace("_", "-")
    roles = {page_by_key[key].role for key in page_keys}
    return roles.pop() if len(roles) == 1 else "package"


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


def _build_groups_from_lock(
    pages: list[PageContract],
    lock: dict[str, dict[str, str]],
) -> list[dict[str, Any]] | None:
    package_specs = lock.get("generation_packages") or {}
    if not package_specs:
        return None

    page_by_key = {page.key: page for page in pages}
    groups: list[dict[str, Any]] = []
    owner_by_page: dict[str, str] = {}

    for package_id, raw_value in package_specs.items():
        page_keys = _parse_package_pages(raw_value)
        unknown = [key for key in page_keys if key not in page_by_key]
        if unknown:
            raise ValueError(f"generation_packages {package_id} references unknown pages: {', '.join(unknown)}")

        duplicate = [key for key in page_keys if key in owner_by_page]
        if duplicate:
            owners = ", ".join(f"{key} already in {owner_by_page[key]}" for key in duplicate)
            raise ValueError(f"generation_packages {package_id} overlaps previous packages: {owners}")

        runtime = _parse_package_runtime(raw_value)
        if runtime is None:
            standalone = all(page_by_key[key].role in {"cover", "toc", "ending"} for key in page_keys)
            runtime = not standalone

        group = {
            "id": package_id,
            "kind": _infer_package_kind(package_id, page_keys, page_by_key),
            "pages": page_keys,
            "parallel_eligible": runtime,
            "internal_order": "serial",
        }
        groups.append(group)
        for key in page_keys:
            owner_by_page[key] = package_id
            page_by_key[key].group_id = package_id

    missing = [page.key for page in pages if page.key not in owner_by_page]
    if missing:
        raise ValueError(f"generation_packages missing expected pages: {', '.join(missing)}")

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

    groups = _build_groups_from_lock(pages, lock) or _build_groups(pages)
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
        "- Sub-agent work packages may run concurrently; pages inside one package stay serial.",
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


def _write_plan(project: Path, concurrency: int) -> tuple[dict[str, Any], Path]:
    pages, groups = _build_page_contracts(project)
    out_dir = project / "parallel_generation"
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "version": 1,
        "mode": "chapter_parallel",
        "created_at": _utc_now(),
        "project": project.name,
        "concurrency": concurrency,
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
    return manifest, out_dir


def cmd_plan(args: argparse.Namespace) -> int:
    project = args.project_path.resolve()
    if not project.exists():
        print(f"[ERROR] Project path does not exist: {project}")
        return 1
    if args.concurrency < 1 or args.concurrency > 8:
        print("[ERROR] --concurrency must be between 1 and 8")
        return 1

    manifest, out_dir = _write_plan(project, args.concurrency)
    print(f"[OK] Wrote parallel generation plan: {out_dir}")
    print(
        f"[OK] Pages: {len(manifest['pages'])} | "
        f"Groups: {len(manifest['groups'])} | Concurrency: {args.concurrency}"
    )
    for group in manifest["groups"]:
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


def _run_dir(project: Path, requested: str | None = None) -> Path:
    runs_dir = project / "parallel_generation" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    base = requested or _timestamp()
    candidate = runs_dir / base
    if not candidate.exists():
        candidate.mkdir(parents=True)
        return candidate

    suffix = 2
    while True:
        alternate = runs_dir / f"{base}-{suffix}"
        if not alternate.exists():
            alternate.mkdir(parents=True)
            return alternate
        suffix += 1


def _load_run_manifest(project: Path, run_id: str) -> tuple[Path, dict[str, Any]]:
    run_dir = project / "parallel_generation" / "runs" / run_id
    run_manifest_path = run_dir / "run_manifest.json"
    if not run_manifest_path.exists():
        raise FileNotFoundError(f"run_manifest.json not found: {run_manifest_path}")
    return run_dir, json.loads(run_manifest_path.read_text(encoding="utf-8"))


def _page_lookup(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(page["key"]): page for page in manifest.get("pages", [])}


def _page_number(page_key: str) -> int:
    m = re.fullmatch(r"[Pp](\d{2,3})", str(page_key))
    if not m:
        raise ValueError(f"Invalid page key: {page_key}")
    return int(m.group(1))


def _expected_numbers(page_keys: list[str]) -> list[int]:
    return sorted(_page_number(page) for page in page_keys)


def _render_package_prompt(
    project: Path,
    run_dir: Path,
    group: dict[str, Any],
    manifest: dict[str, Any],
) -> str:
    pages_by_key = _page_lookup(manifest)
    package_id = str(group["id"])
    work_dir = run_dir / "work" / package_id
    svg_dir = work_dir / "svg_output"
    report_path = work_dir / "package_report.json"

    page_lines: list[str] = []
    contract_blocks: list[str] = []
    for page_key in group.get("pages", []):
        page = pages_by_key.get(str(page_key), {})
        number = _page_number(str(page_key))
        title = page.get("title") or "(untitled)"
        layout = page.get("layout") or "none"
        rhythm = page.get("rhythm") or "unspecified"
        chart = page.get("chart") or "none"
        contract_path = project / "parallel_generation" / "page_contracts" / f"{page_key}.md"
        contract_text = contract_path.read_text(encoding="utf-8") if contract_path.exists() else ""
        page_lines.append(
            f"- `{page_key}`: expected filename prefix `{number:02d}_`, "
            f"title `{title}`, layout `{layout}`, rhythm `{rhythm}`, chart `{chart}`"
        )
        contract_blocks.append(
            f"## Contract {page_key}\n\nSource: `{contract_path}`\n\n{contract_text}".rstrip()
        )

    return "\n".join(
        [
            "# Viettel PPT Work Package Task",
            "",
            "You are an isolated OpenClaw sub-agent assigned to one work package from run_manifest.subagent_groups.",
            "Generate only the SVG pages listed in this prompt.",
            "",
            "## Scope",
            "",
            f"- Project path: `{project}`",
            f"- Run directory: `{run_dir}`",
            f"- Package ID: `{package_id}`",
            f"- Package kind: `{group.get('kind', 'unknown')}`",
            f"- Staging SVG directory: `{svg_dir}`",
            f"- Required report file: `{report_path}`",
            "- Do not write directly to `<project_path>/svg_output/`.",
            "- Do not edit any page outside this package.",
            "- Keep pages inside this package serial and visually continuous.",
            "- Hand-write SVG files; do not script-generate page markup.",
            "",
            "## Required Reads",
            "",
            "- Read `<project_path>/design_spec.md`.",
            "- Read `<project_path>/spec_lock.md` before each page.",
            "- Cross-check `<project_path>/parallel_generation/spec_lock_snapshot.md`.",
            "- Read `<project_path>/parallel_generation/parallel_context.md`.",
            "- Use only the page contracts embedded below for page scope.",
            "",
            "## Assigned Pages",
            "",
            *page_lines,
            "",
            "## Quality Gate",
            "",
            "- After each staged SVG, run:",
            f"  `python3 {SCRIPT_DIR}/svg_quality_checker.py <staged_svg_file>`",
            "- Fix any checker `error` before moving to the next page.",
            "- At completion, write `package_report.json` with keys: "
            "`status`, `package_id`, `pages`, `generated_files`, `checker_errors`, `notes`.",
            "- Use `status: \"passed\"` only if all assigned pages exist in staging and have no checker errors.",
            "",
            "## Page Contracts",
            "",
            "\n\n---\n\n".join(contract_blocks),
            "",
        ]
    )


def cmd_prepare_subagents(args: argparse.Namespace) -> int:
    project = args.project_path.resolve()
    if not project.exists():
        print(f"[ERROR] Project path does not exist: {project}")
        return 1
    if args.concurrency < 1 or args.concurrency > 8:
        print("[ERROR] --concurrency must be between 1 and 8")
        return 1

    try:
        manifest, _ = _write_plan(project, args.concurrency)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] {exc}")
        return 1

    run_dir = _run_dir(project, args.run_id)
    prompts_dir = run_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    subagent_groups: list[dict[str, Any]] = []
    main_agent_groups: list[dict[str, Any]] = []
    spawn_snippets: list[str] = []

    for group in manifest.get("groups", []):
        if group.get("parallel_eligible"):
            package_id = str(group["id"])
            work_dir = run_dir / "work" / package_id
            svg_dir = work_dir / "svg_output"
            svg_dir.mkdir(parents=True, exist_ok=True)
            prompt_file = prompts_dir / f"{package_id}.md"
            prompt_file.write_text(
                _render_package_prompt(project, run_dir, group, manifest),
                encoding="utf-8",
            )
            raw_task_name = f"ppt_{project.name}_{run_dir.name}_{package_id}"
            task_name = re.sub(r"[^A-Za-z0-9_]+", "_", raw_task_name).strip("_")
            spawn_task = f"Read and execute the package prompt at {prompt_file}. Do not work outside that scope."
            package = {
                "id": package_id,
                "kind": group.get("kind", "unknown"),
                "pages": group.get("pages", []),
                "task_name": task_name,
                "prompt_file": str(prompt_file),
                "work_dir": str(work_dir),
                "svg_output_dir": str(svg_dir),
                "package_report": str(work_dir / "package_report.json"),
                "spawn_request": {
                    "task": spawn_task,
                    "taskName": task_name,
                    "runtime": "subagent",
                    "mode": "run",
                    "context": "isolated",
                    "cleanup": "keep",
                    "timeoutSeconds": 1800,
                },
            }
            subagent_groups.append(package)
            spawn_snippets.append(
                "sessions_spawn({\n"
                f"  task: \"{spawn_task}\",\n"
                f"  taskName: \"{task_name}\",\n"
                "  runtime: \"subagent\",\n"
                "  mode: \"run\",\n"
                "  context: \"isolated\",\n"
                "  cleanup: \"keep\",\n"
                "  timeoutSeconds: 1800\n"
                "})"
            )
        else:
            main_agent_groups.append(
                {
                    "id": group["id"],
                    "kind": group.get("kind", "unknown"),
                    "pages": group.get("pages", []),
                }
            )

    run_manifest = {
        "version": 1,
        "mode": "openclaw_subagents",
        "created_at": _utc_now(),
        "project": project.name,
        "project_path": str(project),
        "run_id": run_dir.name,
        "concurrency": args.concurrency,
        "source_manifest": str(project / "parallel_generation" / "manifest.json"),
        "subagent_groups": subagent_groups,
        "main_agent_groups": main_agent_groups,
    }
    (run_dir / "run_manifest.json").write_text(
        json.dumps(run_manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    runbook = [
        "# OpenClaw Sub-Agent Spawn Runbook",
        "",
        f"- Project: `{project}`",
        f"- Run ID: `{run_dir.name}`",
        f"- Concurrency: `{args.concurrency}`",
        "",
        "## Main-Agent Packages",
        "",
    ]
    for group in main_agent_groups:
        runbook.append(f"- `{group['id']}` ({group['kind']}): {', '.join(group['pages'])}")
    runbook.extend(
        [
            "",
            "## Spawn Commands",
            "",
            "Call one `sessions_spawn` per package. Do not combine multiple package prompts in one sub-agent.",
            "",
        ]
    )
    if spawn_snippets:
        for batch_index, start in enumerate(range(0, len(spawn_snippets), args.concurrency), start=1):
            batch = spawn_snippets[start : start + args.concurrency]
            runbook.extend([f"### Batch {batch_index}", ""])
            runbook.extend(batch)
            runbook.extend(["", "Wait for this batch before starting the next one:", "", "```js\nsessions_yield()\n```", ""])
    else:
        runbook.append("_No sub-agent eligible groups found._")
    runbook.extend(
        [
            "",
            "## After Yield",
            "",
            f"1. Run `python3 {SCRIPT_DIR}/parallel_generation.py merge {project} --run-id {run_dir.name}`.",
            f"2. Run `python3 {SCRIPT_DIR}/parallel_generation.py validate {project}`.",
            "",
        ]
    )
    (run_dir / "sessions_spawn_runbook.md").write_text("\n\n".join(runbook), encoding="utf-8")

    print(f"[OK] Prepared OpenClaw sub-agent run: {run_dir}")
    print(f"[OK] Sub-agent work packages: {len(subagent_groups)} | Main-agent packages: {len(main_agent_groups)}")
    print(f"[OK] Runbook: {run_dir / 'sessions_spawn_runbook.md'}")
    for package in subagent_groups:
        print(f"  - {package['id']}: {', '.join(package['pages'])} -> {package['prompt_file']}")
    return 0


def _discover_svg_numbers(svg_dir: Path) -> dict[int, list[Path]]:
    numbers: dict[int, list[Path]] = {}
    for path in sorted(svg_dir.glob("*.svg")):
        m = re.match(r"^(\d{2,3})(?:[_-].*)?\.svg$", path.name)
        if not m:
            continue
        numbers.setdefault(int(m.group(1)), []).append(path)
    return numbers


def _staged_package_errors(package: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    package_id = str(package.get("id", "unknown"))
    svg_dir = Path(str(package["svg_output_dir"]))
    report_path = Path(str(package["package_report"]))

    if not report_path.exists():
        errors.append(f"{package_id}: missing package_report.json")
    else:
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{package_id}: invalid package_report.json: {exc}")
        else:
            if report.get("status") != "passed":
                errors.append(f"{package_id}: package_report status is {report.get('status')!r}, expected 'passed'")

    if not svg_dir.exists():
        errors.append(f"{package_id}: staging svg_output/ not found: {svg_dir}")
        return errors

    expected = _expected_numbers([str(page) for page in package.get("pages", [])])
    staged = _discover_svg_numbers(svg_dir)
    unnumbered = [
        path.name
        for path in sorted(svg_dir.glob("*.svg"))
        if not re.match(r"^(\d{2,3})(?:[_-].*)?\.svg$", path.name)
    ]
    if unnumbered:
        errors.append(f"{package_id}: unnumbered staged SVG file(s): {', '.join(unnumbered)}")

    actual = sorted(staged)
    for number in sorted(set(expected) - set(actual)):
        errors.append(f"{package_id}: missing staged SVG for P{number:02d}")
    for number in sorted(set(actual) - set(expected)):
        errors.append(f"{package_id}: generated out-of-scope SVG number {number:02d}")
    for number in expected:
        if len(staged.get(number, [])) > 1:
            names = ", ".join(path.name for path in staged[number])
            errors.append(f"{package_id}: duplicate staged SVGs for P{number:02d}: {names}")

    return errors


def cmd_merge(args: argparse.Namespace) -> int:
    project = args.project_path.resolve()
    try:
        run_dir, run_manifest = _load_run_manifest(project, args.run_id)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[ERROR] {exc}")
        return 1

    packages = run_manifest.get("subagent_groups") or []
    if not packages:
        print("[WARN] No sub-agent packages to merge")
        return 0

    errors: list[str] = []
    owner_by_number: dict[int, str] = {}
    for package in packages:
        errors.extend(_staged_package_errors(package))
        for number in _expected_numbers([str(page) for page in package.get("pages", [])]):
            owner = owner_by_number.get(number)
            if owner:
                errors.append(f"P{number:02d}: assigned to both {owner} and {package['id']}")
            owner_by_number[number] = str(package["id"])

    if errors:
        print("[ERROR] Staged sub-agent output validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    target_dir = project / "svg_output"
    target_dir.mkdir(parents=True, exist_ok=True)
    existing_by_number = _discover_svg_numbers(target_dir)
    backup_dir = run_dir / "backup" / "svg_output_conflicts"

    for package in packages:
        staged_by_number = _discover_svg_numbers(Path(str(package["svg_output_dir"])))
        for number in _expected_numbers([str(page) for page in package.get("pages", [])]):
            src = staged_by_number[number][0]
            existing = existing_by_number.get(number, [])
            if existing and not args.replace_output:
                names = ", ".join(path.name for path in existing)
                print(
                    f"[ERROR] Refusing to merge P{number:02d}; existing svg_output file(s): {names}. "
                    "Use --replace-output to back up and replace package conflicts."
                )
                return 1
            if existing and args.replace_output:
                backup_dir.mkdir(parents=True, exist_ok=True)
                for old in existing:
                    shutil.move(str(old), str(backup_dir / old.name))
            shutil.copy2(src, target_dir / src.name)

    print(f"[OK] Merged {len(owner_by_number)} sub-agent SVG(s) into {target_dir}")
    if backup_dir.exists():
        print(f"[OK] Backed up replaced package SVG(s) to {backup_dir}")
    return 0


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

    prepare = sub.add_parser("prepare-subagents", help="create OpenClaw sub-agent package prompts and staging dirs")
    prepare.add_argument("project_path", type=Path)
    prepare.add_argument("--concurrency", type=int, default=2)
    prepare.add_argument("--run-id", default=None)
    prepare.set_defaults(func=cmd_prepare_subagents)

    merge = sub.add_parser("merge", help="merge validated sub-agent staged SVGs into svg_output/")
    merge.add_argument("project_path", type=Path)
    merge.add_argument("--run-id", required=True)
    merge.add_argument(
        "--replace-output",
        action="store_true",
        help="back up and replace conflicting package SVG numbers in svg_output/",
    )
    merge.set_defaults(func=cmd_merge)

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
