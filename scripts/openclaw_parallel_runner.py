#!/usr/bin/env python3
"""OpenClaw multi-session runner for experimental chapter-parallel SVG generation.

This script does not generate SVG markup. It creates per-package worker prompts,
spawns the configured OpenClaw command for each package, stages worker output,
merges successful packages into svg_output/, and runs the existing validators.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
PLAN_SCRIPT = SCRIPT_DIR / "parallel_generation.py"
QUALITY_SCRIPT = SCRIPT_DIR / "svg_quality_checker.py"


@dataclass
class PackageRun:
    package_id: str
    kind: str
    pages: list[str]
    prompt_file: str
    work_dir: str
    command: list[str] | None
    status: str = "pending"
    started_at: str | None = None
    finished_at: str | None = None
    elapsed_seconds: float | None = None
    returncode: int | None = None
    stdout_file: str | None = None
    stderr_file: str | None = None
    error: str | None = None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _project(path: Path) -> Path:
    project = path.resolve()
    if not project.exists():
        raise FileNotFoundError(f"Project path does not exist: {project}")
    if not (project / "design_spec.md").exists():
        raise FileNotFoundError(f"design_spec.md not found in project: {project}")
    if not (project / "spec_lock.md").exists():
        raise FileNotFoundError(f"spec_lock.md not found in project: {project}")
    return project


def _run_plan(project: Path, concurrency: int) -> None:
    cmd = [
        sys.executable,
        str(PLAN_SCRIPT),
        "plan",
        str(project),
        "--concurrency",
        str(concurrency),
    ]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        if proc.stdout:
            print(proc.stdout, end="")
        if proc.stderr:
            print(proc.stderr, end="", file=sys.stderr)
        raise RuntimeError(f"parallel_generation.py plan failed with exit code {proc.returncode}")


def _load_manifest(project: Path) -> dict[str, Any]:
    manifest_path = project / "parallel_generation" / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")
    return _read_json(manifest_path)


def _make_run_dir(project: Path, requested: str | None) -> Path:
    runs_dir = project / "parallel_generation" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    base = requested or _timestamp()
    run_dir = runs_dir / base
    if not run_dir.exists():
        run_dir.mkdir(parents=True)
        return run_dir

    suffix = 2
    while True:
        candidate = runs_dir / f"{base}-{suffix}"
        if not candidate.exists():
            candidate.mkdir(parents=True)
            return candidate
        suffix += 1


def _pages_by_key(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(page["key"]): page for page in manifest.get("pages", [])}


def _svg_prefix(page_key: str) -> str:
    m = re.fullmatch(r"[Pp](\d{2,3})", page_key)
    if not m:
        raise ValueError(f"Invalid page key in manifest: {page_key}")
    return f"{int(m.group(1)):02d}_"


def _render_prompt(
    project: Path,
    run_dir: Path,
    group: dict[str, Any],
    manifest: dict[str, Any],
) -> str:
    pages_by_key = _pages_by_key(manifest)
    page_lines = []
    contract_blocks = []
    for page_key in group.get("pages", []):
        page = pages_by_key.get(page_key, {})
        prefix = _svg_prefix(page_key)
        title = page.get("title") or "(untitled)"
        layout = page.get("layout") or "none"
        rhythm = page.get("rhythm") or "unspecified"
        chart = page.get("chart") or "none"
        contract_path = project / "parallel_generation" / "page_contracts" / f"{page_key}.md"
        contract_text = contract_path.read_text(encoding="utf-8") if contract_path.exists() else ""
        page_lines.append(
            f"- `{page_key}`: prefix `{prefix}`, title `{title}`, layout `{layout}`, "
            f"rhythm `{rhythm}`, chart `{chart}`"
        )
        contract_blocks.append(
            f"## Contract {page_key}\n\nSource: `{contract_path}`\n\n{contract_text}".rstrip()
        )

    package_id = str(group["id"])
    work_dir = run_dir / "work" / package_id
    svg_stage = work_dir / "svg_output"
    worker_report = work_dir / "worker_report.json"

    return "\n".join(
        [
            "# OpenClaw Chapter-Parallel Worker Prompt",
            "",
            "You are the main SVG author for this assigned package only.",
            "This is not a SubAgent handoff inside the original context; this is an independent OpenClaw session scoped to one package.",
            "",
            "## Hard Scope",
            "",
            f"- Repo root: `{REPO_ROOT}`",
            f"- Project path: `{project}`",
            f"- Run directory: `{run_dir}`",
            f"- Package ID: `{package_id}`",
            f"- Package kind: `{group.get('kind', 'unknown')}`",
            f"- Staging SVG output directory: `{svg_stage}`",
            f"- Worker report path: `{worker_report}`",
            "- Generate only the pages listed in this prompt.",
            "- Do not edit any other package directory.",
            "- Do not write directly to `<project_path>/svg_output/`.",
            "- Keep pages inside this package serial and visually continuous.",
            "- Hand-write SVG files; do not script-generate page markup.",
            "",
            "## Required Context",
            "",
            "- Read `<project_path>/design_spec.md`.",
            "- Read `<project_path>/spec_lock.md` before every page.",
            "- Cross-check against `<project_path>/parallel_generation/spec_lock_snapshot.md`.",
            "- Read `<project_path>/parallel_generation/parallel_context.md`.",
            "- Use only the page contracts listed below for page scope.",
            "",
            "## Assigned Pages",
            "",
            *page_lines,
            "",
            "## Generation Rules",
            "",
            "- Create the staging directory before writing SVG.",
            "- SVG filenames must start with the expected page prefix, for example `03_title.svg`.",
            "- After writing each SVG, run:",
            f"  `python3 {QUALITY_SCRIPT} <staged_svg_file>`",
            "- If the checker reports any error, fix that SVG before moving to the next page.",
            "- At the end, write `worker_report.json` with keys: `status`, `package_id`, `pages`, `generated_files`, `started_at`, `finished_at`, `elapsed_seconds`, `checker_errors`, `notes`.",
            "- Use `status: \"passed\"` only when all assigned SVGs exist in staging and have no checker errors.",
            "",
            "## Page Contracts",
            "",
            "\n\n---\n\n".join(contract_blocks),
            "",
        ]
    )


def _format_command(template: str, values: dict[str, str]) -> list[str]:
    try:
        rendered = template.format(**values)
    except KeyError as exc:
        allowed = ", ".join(sorted(values))
        raise ValueError(f"Unknown worker-command placeholder {exc!s}. Allowed: {allowed}") from exc
    return shlex.split(rendered)


def _prepare_packages(
    project: Path,
    run_dir: Path,
    manifest: dict[str, Any],
    worker_command: str | None,
) -> list[PackageRun]:
    prompts_dir = run_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    packages: list[PackageRun] = []

    for group in manifest.get("groups", []):
        package_id = str(group["id"])
        work_dir = run_dir / "work" / package_id
        (work_dir / "svg_output").mkdir(parents=True, exist_ok=True)
        prompt_file = prompts_dir / f"{package_id}.md"
        prompt_file.write_text(_render_prompt(project, run_dir, group, manifest), encoding="utf-8")

        command = None
        if worker_command:
            command = _format_command(
                worker_command,
                {
                    "repo_root": str(REPO_ROOT),
                    "project_path": str(project),
                    "run_dir": str(run_dir),
                    "package_id": package_id,
                    "prompt_file": str(prompt_file),
                    "work_dir": str(work_dir),
                },
            )

        packages.append(
            PackageRun(
                package_id=package_id,
                kind=str(group.get("kind", "unknown")),
                pages=[str(page) for page in group.get("pages", [])],
                prompt_file=str(prompt_file),
                work_dir=str(work_dir),
                command=command,
            )
        )

    return packages


def _write_run_manifest(
    run_dir: Path,
    project: Path,
    concurrency: int,
    dry_run: bool,
    packages: list[PackageRun],
    status: str = "prepared",
) -> None:
    _write_json(
        run_dir / "run_manifest.json",
        {
            "version": 1,
            "status": status,
            "created_at": _utc_now(),
            "project_path": str(project),
            "concurrency": concurrency,
            "dry_run": dry_run,
            "packages": [asdict(package) for package in packages],
        },
    )


def _update_package_status(run_dir: Path, package: PackageRun) -> None:
    _write_json(Path(package.work_dir) / "orchestrator_status.json", asdict(package))


def _run_worker(package: PackageRun) -> PackageRun:
    if not package.command:
        package.status = "skipped"
        package.error = "No worker command configured"
        return package

    work_dir = Path(package.work_dir)
    logs_dir = work_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    stdout_file = logs_dir / "stdout.log"
    stderr_file = logs_dir / "stderr.log"
    package.stdout_file = str(stdout_file)
    package.stderr_file = str(stderr_file)
    package.status = "running"
    package.started_at = _utc_now()
    started = time.monotonic()
    _update_package_status(work_dir.parent.parent, package)

    with stdout_file.open("w", encoding="utf-8") as out, stderr_file.open("w", encoding="utf-8") as err:
        proc = subprocess.run(package.command, cwd=REPO_ROOT, text=True, stdout=out, stderr=err, check=False)

    package.returncode = proc.returncode
    package.elapsed_seconds = round(time.monotonic() - started, 3)
    package.finished_at = _utc_now()
    if proc.returncode == 0:
        package.status = "passed"
    else:
        package.status = "failed"
        package.error = f"Worker command exited with {proc.returncode}"
    _update_package_status(work_dir.parent.parent, package)
    return package


def _expected_numbers_for_pages(pages: list[str]) -> set[int]:
    numbers = set()
    for page in pages:
        m = re.fullmatch(r"[Pp](\d{2,3})", page)
        if not m:
            raise ValueError(f"Invalid page key: {page}")
        numbers.add(int(m.group(1)))
    return numbers


def _discover_staged_svgs(package: PackageRun) -> dict[int, list[Path]]:
    svg_dir = Path(package.work_dir) / "svg_output"
    files: dict[int, list[Path]] = {}
    for path in sorted(svg_dir.glob("*.svg")):
        m = re.match(r"^(\d{2,3})(?:[_-].*)?\.svg$", path.name)
        if not m:
            files.setdefault(-1, []).append(path)
            continue
        files.setdefault(int(m.group(1)), []).append(path)
    return files


def _validate_staging(packages: list[PackageRun]) -> list[str]:
    errors: list[str] = []
    owner_by_number: dict[int, str] = {}

    for package in packages:
        if package.status != "passed":
            errors.append(f"{package.package_id}: package status is {package.status}")
            continue

        report_path = Path(package.work_dir) / "worker_report.json"
        if not report_path.exists():
            errors.append(f"{package.package_id}: missing worker_report.json")
        else:
            try:
                report = _read_json(report_path)
            except json.JSONDecodeError as exc:
                errors.append(f"{package.package_id}: invalid worker_report.json: {exc}")
            else:
                if report.get("status") != "passed":
                    errors.append(
                        f"{package.package_id}: worker_report.json status is {report.get('status')!r}, expected 'passed'"
                    )

        expected = _expected_numbers_for_pages(package.pages)
        staged = _discover_staged_svgs(package)
        if -1 in staged:
            errors.append(
                f"{package.package_id}: unnumbered SVG file(s): "
                + ", ".join(path.name for path in staged[-1])
            )

        actual = {number for number in staged if number >= 0}
        for number in sorted(expected - actual):
            errors.append(f"{package.package_id}: missing staged SVG for P{number:02d}")
        for number in sorted(actual - expected):
            errors.append(f"{package.package_id}: generated out-of-scope SVG number {number:02d}")
        for number in sorted(actual & expected):
            paths = staged[number]
            if len(paths) > 1:
                errors.append(
                    f"{package.package_id}: duplicate staged SVGs for P{number:02d}: "
                    + ", ".join(path.name for path in paths)
                )
            if number in owner_by_number:
                errors.append(
                    f"P{number:02d}: generated by both {owner_by_number[number]} and {package.package_id}"
                )
            owner_by_number[number] = package.package_id

    return errors


def _backup_existing_svg_output(project: Path, run_dir: Path) -> None:
    svg_dir = project / "svg_output"
    if not svg_dir.exists() or not any(svg_dir.glob("*.svg")):
        svg_dir.mkdir(parents=True, exist_ok=True)
        return

    backup_dir = run_dir / "backup" / "svg_output_before_merge"
    backup_dir.parent.mkdir(parents=True, exist_ok=True)
    if backup_dir.exists():
        raise RuntimeError(f"Backup directory already exists: {backup_dir}")
    shutil.move(str(svg_dir), str(backup_dir))
    svg_dir.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Backed up existing svg_output/ to {backup_dir}")


def _merge_outputs(project: Path, run_dir: Path, packages: list[PackageRun], replace_output: bool) -> None:
    errors = _validate_staging(packages)
    if errors:
        raise RuntimeError("Staging validation failed:\n  - " + "\n  - ".join(errors))

    target_dir = project / "svg_output"
    if replace_output:
        _backup_existing_svg_output(project, run_dir)
    else:
        target_dir.mkdir(parents=True, exist_ok=True)

    copied_numbers: set[int] = set()
    for package in packages:
        staged = _discover_staged_svgs(package)
        for number in sorted(_expected_numbers_for_pages(package.pages)):
            src = staged[number][0]
            dst = target_dir / src.name
            if number in copied_numbers:
                raise RuntimeError(f"P{number:02d}: duplicate package merge attempt")
            if dst.exists():
                raise RuntimeError(
                    f"Refusing to overwrite existing SVG: {dst}. "
                    "Use --replace-output to back up current svg_output/ first."
                )
            shutil.copy2(src, dst)
            copied_numbers.add(number)


def _run_validator(project: Path) -> None:
    cmd = [sys.executable, str(PLAN_SCRIPT), "validate", str(project)]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"parallel_generation.py validate failed with exit code {proc.returncode}")


def _load_run_manifest(project: Path, run_id: str | None) -> tuple[Path, dict[str, Any]]:
    runs_dir = project / "parallel_generation" / "runs"
    if run_id:
        run_dir = runs_dir / run_id
    else:
        candidates = sorted(
            [path for path in runs_dir.glob("*") if (path / "run_manifest.json").exists()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            raise FileNotFoundError(f"No OpenClaw parallel runs found under {runs_dir}")
        run_dir = candidates[0]

    manifest_path = run_dir / "run_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing run_manifest.json: {manifest_path}")
    return run_dir, _read_json(manifest_path)


def cmd_run(args: argparse.Namespace) -> int:
    project = _project(args.project_path)
    if args.concurrency < 1 or args.concurrency > 8:
        print("[ERROR] --concurrency must be between 1 and 8")
        return 1
    if not args.dry_run and not args.worker_command:
        print("[ERROR] --worker-command is required unless --dry-run is set")
        return 1

    try:
        if not args.reuse_plan:
            _run_plan(project, args.concurrency)
        manifest = _load_manifest(project)
        run_dir = _make_run_dir(project, args.run_id)
        packages = _prepare_packages(project, run_dir, manifest, None if args.dry_run else args.worker_command)
        _write_run_manifest(run_dir, project, args.concurrency, args.dry_run, packages)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"[ERROR] {exc}")
        return 1

    print(f"[OK] Prepared OpenClaw parallel run: {run_dir}")
    print(f"[OK] Packages: {len(packages)} | Concurrency: {args.concurrency} | Dry-run: {args.dry_run}")

    if args.dry_run:
        for package in packages:
            print(f"  - {package.package_id}: prompt={package.prompt_file}")
        return 0

    results: list[PackageRun] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = {pool.submit(_run_worker, package): package for package in packages}
        for future in concurrent.futures.as_completed(futures):
            package = future.result()
            results.append(package)
            marker = "[OK]" if package.status == "passed" else "[ERROR]"
            print(f"{marker} {package.package_id}: {package.status} ({package.elapsed_seconds}s)")

    results.sort(key=lambda item: packages.index(next(p for p in packages if p.package_id == item.package_id)))
    _write_run_manifest(run_dir, project, args.concurrency, False, results, status="workers_complete")

    failed = [package for package in results if package.status != "passed"]
    if failed:
        print("[ERROR] Worker failure(s); merge skipped")
        return 1

    try:
        _merge_outputs(project, run_dir, results, args.replace_output)
        _write_run_manifest(run_dir, project, args.concurrency, False, results, status="merged")
        print(f"[OK] Merged staged SVGs into {project / 'svg_output'}")
        _run_validator(project)
        _write_run_manifest(run_dir, project, args.concurrency, False, results, status="validated")
    except RuntimeError as exc:
        print(f"[ERROR] {exc}")
        return 1

    print("[OK] OpenClaw multi-session run completed and validated")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    try:
        project = _project(args.project_path)
        run_dir, manifest = _load_run_manifest(project, args.run_id)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[ERROR] {exc}")
        return 1

    print(f"Run: {run_dir.name}")
    print(f"Status: {manifest.get('status', 'unknown')}")
    print(f"Project: {manifest.get('project_path', project)}")
    print(f"Concurrency: {manifest.get('concurrency', 'unknown')}")
    print("Packages:")
    for package in manifest.get("packages", []):
        status = package.get("status", "unknown")
        elapsed = package.get("elapsed_seconds")
        elapsed_text = f", {elapsed}s" if elapsed is not None else ""
        print(f"  - {package.get('package_id')}: {status}{elapsed_text}")
        if package.get("error"):
            print(f"    error: {package['error']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="spawn configured OpenClaw workers and merge validated output")
    run.add_argument("project_path", type=Path)
    run.add_argument("--concurrency", type=int, default=2)
    run.add_argument("--worker-command", default=None)
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--reuse-plan", action="store_true", help="reuse existing parallel_generation/manifest.json")
    run.add_argument("--run-id", default=None, help="optional deterministic run folder name")
    run.add_argument(
        "--replace-output",
        action="store_true",
        help="back up existing svg_output/ before merging staged worker output",
    )
    run.set_defaults(func=cmd_run)

    status = sub.add_parser("status", help="show the latest or selected OpenClaw parallel run")
    status.add_argument("project_path", type=Path)
    status.add_argument("--run-id", default=None)
    status.set_defaults(func=cmd_status)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
