#!/usr/bin/env python3
"""Project font preflight for PPT Master decks.

Checks which font families declared in spec_lock.md are installed on the host,
which are available in the project's local font bundle, and whether any stack
is already falling back to a later family.

Writes a machine-readable report to <project>/font_preflight.json and prints a
short human-readable summary. This script never installs fonts.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

try:
    from update_spec import parse_lock
except ImportError:
    print("error: unable to import parse_lock from update_spec.py", file=sys.stderr)
    sys.exit(2)


GENERIC_FAMILIES = {
    "sans-serif",
    "serif",
    "monospace",
    "system-ui",
    "cursive",
    "fantasy",
}

STYLE_SUFFIX_RE = re.compile(
    r"[-_ ](?:xthin|thin|light|book|bbook|regular|medium|semibold|bold|black|extrabold)"
    r"(?:[-_ ]italic)?$",
    re.IGNORECASE,
)


def normalize_font_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def family_aliases_from_name(value: str) -> set[str]:
    aliases = set()
    stripped = value.strip().strip("\"'")
    if not stripped:
        return aliases
    aliases.add(normalize_font_name(stripped))
    stem = STYLE_SUFFIX_RE.sub("", stripped)
    aliases.add(normalize_font_name(stem))
    aliases.add(normalize_font_name(stem.replace(" ", "")))
    aliases.add(normalize_font_name(stem.replace("-", " ")))
    return {alias for alias in aliases if alias}


def parse_font_stack(stack: str) -> list[str]:
    parts = []
    for raw in stack.split(","):
        family = raw.strip().strip("\"'")
        if not family or family.lower() in GENERIC_FAMILIES:
            continue
        parts.append(family)
    return parts


def collect_required_stacks(lock: dict[str, dict[str, str]]) -> list[dict[str, object]]:
    typography = lock.get("typography", {})
    stacks: list[dict[str, object]] = []
    seen: set[str] = set()
    for key in ("font_family", "title_family", "body_family", "emphasis_family", "code_family"):
        stack = (typography.get(key) or "").strip()
        if not stack:
            continue
        if stack in seen:
            continue
        seen.add(stack)
        stacks.append(
            {
                "key": key,
                "stack": stack,
                "families": parse_font_stack(stack),
            }
        )
    return stacks


def _run_command(cmd: list[str]) -> str:
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
    except (OSError, ValueError):
        return ""
    return proc.stdout if proc.returncode == 0 else ""


def collect_installed_fonts() -> tuple[set[str], list[str]]:
    aliases: set[str] = set()
    sources: list[str] = []

    fc_list = _run_command(["fc-list", ":", "family", "file"])
    if fc_list:
        sources.append("fc-list")
        for line in fc_list.splitlines():
            parts = [part.strip() for part in line.split(":", 1)]
            payload = parts[1] if len(parts) == 2 else parts[0]
            for chunk in payload.split(","):
                aliases.update(family_aliases_from_name(chunk))

    system = platform.system()
    font_dirs: list[Path] = []
    home = Path.home()
    if system == "Linux":
        font_dirs.extend(
            [
                home / ".fonts",
                home / ".local/share/fonts",
                Path("/usr/share/fonts"),
                Path("/usr/local/share/fonts"),
            ]
        )
    elif system == "Darwin":
        font_dirs.extend(
            [
                home / "Library/Fonts",
                Path("/Library/Fonts"),
                Path("/System/Library/Fonts"),
            ]
        )
    elif system == "Windows":
        win_dir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        font_dirs.extend(
            [
                win_dir / "Fonts",
                home / "AppData/Local/Microsoft/Windows/Fonts",
            ]
        )
    else:
        font_dirs.append(home / ".fonts")

    for font_dir in font_dirs:
        if not font_dir.exists():
            continue
        sources.append(str(font_dir))
        for ext in ("*.ttf", "*.otf", "*.ttc", "*.otc"):
            for font_file in font_dir.rglob(ext):
                aliases.update(family_aliases_from_name(font_file.stem))

    return aliases, sources


def collect_bundled_fonts(project_path: Path) -> tuple[dict[str, list[str]], list[str]]:
    bundle_aliases: dict[str, list[str]] = {}
    bundle_dirs: list[str] = []
    candidates = [
        project_path / "fonts",
        project_path / "templates" / "fonts",
    ]
    for font_dir in candidates:
        if not font_dir.exists():
            continue
        bundle_dirs.append(str(font_dir))
        for ext in ("*.ttf", "*.otf", "*.ttc", "*.otc"):
            for font_file in sorted(font_dir.rglob(ext)):
                for alias in family_aliases_from_name(font_file.stem):
                    bundle_aliases.setdefault(alias, []).append(str(font_file))
    return bundle_aliases, bundle_dirs


def classify_stack(
    stack: dict[str, object],
    installed_aliases: set[str],
    bundled_aliases: dict[str, list[str]],
) -> dict[str, object]:
    families = stack["families"]
    assert isinstance(families, list)
    family_rows = []
    active_family = None
    active_index = None

    for idx, family in enumerate(families):
        aliases = family_aliases_from_name(family)
        installed = any(alias in installed_aliases for alias in aliases)
        bundled_files: list[str] = []
        for alias in aliases:
            bundled_files.extend(bundled_aliases.get(alias, []))
        bundled_files = sorted(set(bundled_files))
        row = {
            "family": family,
            "installed": installed,
            "bundled": bool(bundled_files),
            "bundle_files": bundled_files,
        }
        family_rows.append(row)
        if installed and active_family is None:
            active_family = family
            active_index = idx

    if active_family is None:
        status = "missing"
    elif active_index == 0:
        status = "installed"
    else:
        status = "fallback in use"

    missing_before_active = []
    if active_index is not None and active_index > 0:
        missing_before_active = [row["family"] for row in family_rows[:active_index]]

    return {
        "key": stack["key"],
        "stack": stack["stack"],
        "status": status,
        "active_family": active_family,
        "missing_before_active": missing_before_active,
        "families": family_rows,
    }


def install_hint(project_path: Path) -> dict[str, object]:
    bundle_dir = project_path / "fonts"
    system = platform.system()
    if system == "Linux":
        command = f'mkdir -p ~/.local/share/fonts && cp "{bundle_dir}"/* ~/.local/share/fonts/ && fc-cache -f'
        note = "May require adjusting the target directory on distro-managed desktops."
    elif system == "Darwin":
        command = f'cp "{bundle_dir}"/* ~/Library/Fonts/'
        note = "Font Book install is also acceptable if the user prefers a GUI flow."
    elif system == "Windows":
        command = f'Copy-Item "{bundle_dir}\\*" "$env:LOCALAPPDATA\\Microsoft\\Windows\\Fonts"'
        note = "Registry-backed per-user font registration may still be required on some Windows builds."
    else:
        command = f'Copy fonts from "{bundle_dir}" into your user font directory, then refresh the font cache.'
        note = "Unknown OS; do not auto-install."
    return {
        "os": system,
        "command": command,
        "note": note,
    }


def build_report(project_path: Path) -> dict[str, object]:
    lock_path = project_path / "spec_lock.md"
    if not lock_path.exists():
        raise FileNotFoundError(f"spec_lock.md not found at {lock_path}")
    lock = parse_lock(lock_path)
    stacks = collect_required_stacks(lock)
    installed_aliases, installed_sources = collect_installed_fonts()
    bundled_aliases, bundle_dirs = collect_bundled_fonts(project_path)

    stack_reports = [
        classify_stack(stack, installed_aliases, bundled_aliases)
        for stack in stacks
    ]

    family_reports = []
    seen_families: set[str] = set()
    for stack_report in stack_reports:
        for family_row in stack_report["families"]:
            family = family_row["family"]
            if family in seen_families:
                continue
            seen_families.add(family)
            family_reports.append(family_row)

    degraded = any(report["status"] != "installed" for report in stack_reports)
    installable = sorted(
        {
            row["family"]
            for row in family_reports
            if (not row["installed"]) and row["bundled"]
        }
    )
    missing_total = sorted(
        {
            row["family"]
            for row in family_reports
            if (not row["installed"]) and (not row["bundled"])
        }
    )

    return {
        "project": str(project_path),
        "summary": {
            "brand_fidelity": "degraded" if degraded else "ok",
            "installed": sorted([row["family"] for row in family_reports if row["installed"]]),
            "missing": missing_total,
            "fallback_in_use": [report["key"] for report in stack_reports if report["status"] == "fallback in use"],
            "installable_from_bundle": installable,
        },
        "bundle": {
            "dirs": bundle_dirs,
        },
        "environment": {
            "os": platform.system(),
            "installed_font_sources": installed_sources,
        },
        "stacks": stack_reports,
        "install_hint": install_hint(project_path),
    }


def print_summary(report: dict[str, object]) -> None:
    summary = report["summary"]
    assert isinstance(summary, dict)
    print(f"Font preflight: brand fidelity {summary['brand_fidelity']}")
    installed = ", ".join(summary["installed"]) if summary["installed"] else "(none)"
    missing = ", ".join(summary["missing"]) if summary["missing"] else "(none)"
    print(f"Installed: {installed}")
    print(f"Missing: {missing}")

    fallback = summary["fallback_in_use"]
    assert isinstance(fallback, list)
    if fallback:
        print(f"Fallback in use: {', '.join(fallback)}")

    installable = summary["installable_from_bundle"]
    assert isinstance(installable, list)
    if installable:
        print(f"Available in bundle: {', '.join(installable)}")
        hint = report["install_hint"]
        assert isinstance(hint, dict)
        print("Local install available with user approval:")
        print(f"  {hint['command']}")
        print(f"  Note: {hint['note']}")

    for stack_report in report["stacks"]:
        assert isinstance(stack_report, dict)
        active = stack_report["active_family"] or "(none)"
        print(f"- {stack_report['key']}: {stack_report['status']} | active={active}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_path", type=Path, help="Project directory containing spec_lock.md")
    parser.add_argument("--json-only", action="store_true", help="Print only the report path after writing JSON")
    args = parser.parse_args()

    project_path = args.project_path.resolve()
    try:
        report = build_report(project_path)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    output_path = project_path / "font_preflight.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json_only:
        print(str(output_path))
        return 0

    print_summary(report)
    print(f"Report written: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
