#!/usr/bin/env python3
"""Project font preflight for PPT Master decks.

Checks which font families declared in spec_lock.md are installed on the host.
For Viettel projects it first searches for the required FS Magistral Book,
Medium, and Bold faces and installs the bundled copies for the current user
only when any face is missing.

Writes a machine-readable report to <project>/font_preflight.json and prints a
short human-readable summary.
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import json
import os
import platform
import re
import shutil
import struct
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

VIETTEL_FAMILY = "FS Magistral"
VIETTEL_REQUIRED_FACES = {
    "Book": "FS Magistral-Book.ttf",
    "Medium": "FS Magistral-Medium.ttf",
    "Bold": "FS Magistral-Bold.ttf",
}
WINDOWS_FONT_REGISTRY_KEYS = (
    r"HKCU\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts",
    r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts",
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


def _run_checked(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout).strip() or f"exit code {proc.returncode}"
        raise RuntimeError(f"{' '.join(cmd[:2])} failed: {detail}")


def _ttf_names(path: Path) -> dict[int, set[str]]:
    """Read family/style names from a TTF/OpenType name table using stdlib."""
    data = path.read_bytes()
    if len(data) < 12:
        raise ValueError(f"invalid font file: {path}")
    num_tables = struct.unpack_from(">H", data, 4)[0]
    name_offset = name_length = None
    for index in range(num_tables):
        record = 12 + index * 16
        if record + 16 > len(data):
            break
        tag, _, offset, length = struct.unpack_from(">4sIII", data, record)
        if tag == b"name":
            name_offset, name_length = offset, length
            break
    if name_offset is None or name_offset + 6 > len(data):
        raise ValueError(f"font has no readable name table: {path}")

    _, count, strings_offset = struct.unpack_from(">HHH", data, name_offset)
    strings_base = name_offset + strings_offset
    names: dict[int, set[str]] = {}
    for index in range(count):
        record = name_offset + 6 + index * 12
        if record + 12 > len(data):
            break
        platform_id, _, _, name_id, length, offset = struct.unpack_from(">HHHHHH", data, record)
        start, end = strings_base + offset, strings_base + offset + length
        if end > len(data) or name_id not in {1, 2, 16, 17}:
            continue
        try:
            value = data[start:end].decode("utf-16-be" if platform_id in {0, 3} else "mac_roman")
        except UnicodeDecodeError:
            continue
        if value.strip():
            names.setdefault(name_id, set()).add(value.strip())
    return names


def _font_file_face(path: Path) -> str | None:
    try:
        names = _ttf_names(path)
    except (OSError, ValueError, struct.error):
        return None
    families = names.get(16, set()) | names.get(1, set())
    styles = names.get(17, set()) | names.get(2, set())
    if normalize_font_name(VIETTEL_FAMILY) not in {
        normalize_font_name(value) for value in families
    }:
        return None
    for face in VIETTEL_REQUIRED_FACES:
        if face.casefold() in {value.casefold() for value in styles}:
            return face
    return None


def _font_dirs(system: str, home: Path | None = None) -> list[Path]:
    home = home or Path.home()
    if system == "Linux":
        return [
            home / ".fonts",
            home / ".local/share/fonts",
            Path("/usr/share/fonts"),
            Path("/usr/local/share/fonts"),
        ]
    if system == "Darwin":
        return [home / "Library/Fonts", Path("/Library/Fonts"), Path("/System/Library/Fonts")]
    return []


def _faces_from_font_dirs(font_dirs: list[Path]) -> dict[str, str]:
    found: dict[str, str] = {}
    for font_dir in font_dirs:
        if not font_dir.exists():
            continue
        for pattern in ("*.ttf", "*.otf"):
            for font_file in font_dir.rglob(pattern):
                face = _font_file_face(font_file)
                if face and face not in found:
                    found[face] = str(font_file)
        if len(found) == len(VIETTEL_REQUIRED_FACES):
            break
    return found


def _faces_from_fontconfig() -> dict[str, str]:
    output = _run_command(["fc-list", "--format", "%{file}\t%{family}\t%{style}\n"])
    found: dict[str, str] = {}
    for line in output.splitlines():
        columns = line.split("\t", 2)
        if len(columns) != 3:
            continue
        font_file, families, styles = columns
        if normalize_font_name(VIETTEL_FAMILY) not in {
            normalize_font_name(value) for value in families.split(",")
        }:
            continue
        style_names = {value.strip().casefold() for value in styles.split(",")}
        for face in VIETTEL_REQUIRED_FACES:
            if face.casefold() in style_names and face not in found:
                found[face] = font_file
    return found


def _faces_from_macos_coretext() -> dict[str, str]:
    core_foundation_path = ctypes.util.find_library("CoreFoundation")
    core_text_path = ctypes.util.find_library("CoreText")
    if not core_foundation_path or not core_text_path:
        return {}
    core_foundation = ctypes.CDLL(core_foundation_path)
    core_text = ctypes.CDLL(core_text_path)
    core_text.CTFontManagerCopyAvailableFontURLs.restype = ctypes.c_void_p
    core_foundation.CFArrayGetCount.argtypes = [ctypes.c_void_p]
    core_foundation.CFArrayGetCount.restype = ctypes.c_long
    core_foundation.CFArrayGetValueAtIndex.argtypes = [ctypes.c_void_p, ctypes.c_long]
    core_foundation.CFArrayGetValueAtIndex.restype = ctypes.c_void_p
    core_foundation.CFURLGetFileSystemRepresentation.argtypes = [
        ctypes.c_void_p, ctypes.c_bool, ctypes.POINTER(ctypes.c_char), ctypes.c_long,
    ]
    core_foundation.CFRelease.argtypes = [ctypes.c_void_p]
    urls = core_text.CTFontManagerCopyAvailableFontURLs()
    if not urls:
        return {}
    found: dict[str, str] = {}
    try:
        for index in range(core_foundation.CFArrayGetCount(urls)):
            url = core_foundation.CFArrayGetValueAtIndex(urls, index)
            buffer = ctypes.create_string_buffer(4096)
            if not core_foundation.CFURLGetFileSystemRepresentation(url, True, buffer, len(buffer)):
                continue
            path = Path(os.fsdecode(buffer.value))
            face = _font_file_face(path)
            if face and face not in found:
                found[face] = str(path)
    finally:
        core_foundation.CFRelease(urls)
    return found


def _faces_from_windows_registry() -> dict[str, str]:
    found: dict[str, str] = {}
    for registry_key in WINDOWS_FONT_REGISTRY_KEYS:
        registry = _run_command(["reg", "query", registry_key])
        for line in registry.splitlines():
            columns = re.split(r"\s{2,}", line.strip())
            if len(columns) < 3 or not columns[1].startswith("REG_"):
                continue
            display_name = re.sub(r"\s*\([^)]*Type\)\s*$", "", columns[0])
            normalized = normalize_font_name(display_name)
            for face in VIETTEL_REQUIRED_FACES:
                if normalize_font_name(f"{VIETTEL_FAMILY} {face}") == normalized:
                    found.setdefault(face, columns[2])
    if found:
        gdi_families = _run_command([
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            "Add-Type -AssemblyName System.Drawing; "
            "(New-Object System.Drawing.Text.InstalledFontCollection).Families.Name",
        ])
        if normalize_font_name(VIETTEL_FAMILY) not in {
            normalize_font_name(value) for value in gdi_families.splitlines()
        }:
            return {}
    return found


def scan_installed_viettel_faces(
    *, system: str | None = None, font_dirs: list[Path] | None = None
) -> dict[str, str]:
    """Return installed required faces keyed by Book/Medium/Bold."""
    system = system or platform.system()
    if system == "Linux":
        return _faces_from_fontconfig() or _faces_from_font_dirs(font_dirs or _font_dirs(system))
    if system == "Darwin":
        return _faces_from_macos_coretext() or _faces_from_font_dirs(font_dirs or _font_dirs(system))
    if system == "Windows":
        return _faces_from_windows_registry()
    return _faces_from_font_dirs(font_dirs or _font_dirs(system))


def _viettel_bundle(project_path: Path) -> dict[str, Path]:
    candidates = [
        project_path / "fonts",
        Path(__file__).resolve().parent.parent / "templates/layouts/viettel_default/fonts",
    ]
    bundle: dict[str, Path] = {}
    for face, filename in VIETTEL_REQUIRED_FACES.items():
        path = next((directory / filename for directory in candidates if (directory / filename).is_file()), None)
        if path is None:
            raise FileNotFoundError(f"bundled font missing: {filename}")
        actual_face = _font_file_face(path)
        if actual_face != face:
            raise ValueError(f"bundled font metadata mismatch: {filename} expected {face}, got {actual_face}")
        bundle[face] = path
    return bundle


def _copy_bundle(bundle: dict[str, Path], target: Path) -> dict[str, str]:
    target.mkdir(parents=True, exist_ok=True)
    installed: dict[str, str] = {}
    for face, source in bundle.items():
        destination = target / source.name
        if not destination.exists() or _font_file_face(destination) != face:
            shutil.copy2(source, destination)
        installed[face] = str(destination)
    return installed


def _register_macos(paths: dict[str, str]) -> None:
    core_foundation_path = ctypes.util.find_library("CoreFoundation")
    core_text_path = ctypes.util.find_library("CoreText")
    if not core_foundation_path or not core_text_path:
        raise RuntimeError("CoreText frameworks are unavailable")
    core_foundation = ctypes.CDLL(core_foundation_path)
    core_text = ctypes.CDLL(core_text_path)
    core_foundation.CFURLCreateFromFileSystemRepresentation.restype = ctypes.c_void_p
    core_foundation.CFURLCreateFromFileSystemRepresentation.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p, ctypes.c_long, ctypes.c_bool,
    ]
    core_foundation.CFRelease.argtypes = [ctypes.c_void_p]
    core_text.CTFontManagerRegisterFontsForURL.argtypes = [
        ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p),
    ]
    core_text.CTFontManagerRegisterFontsForURL.restype = ctypes.c_bool
    for path in paths.values():
        raw = os.fsencode(path)
        url = core_foundation.CFURLCreateFromFileSystemRepresentation(None, raw, len(raw), False)
        if not url:
            raise RuntimeError(f"CoreText could not open font URL: {path}")
        error = ctypes.c_void_p()
        core_text.CTFontManagerRegisterFontsForURL(url, 2, ctypes.byref(error))
        core_foundation.CFRelease(url)
        if error:
            core_foundation.CFRelease(error)


def _register_windows(paths: dict[str, str]) -> None:
    registry_key = WINDOWS_FONT_REGISTRY_KEYS[0]
    for face, path in paths.items():
        _run_checked([
            "reg", "add", registry_key, "/v", f"{VIETTEL_FAMILY} {face} (TrueType)",
            "/t", "REG_SZ", "/d", path, "/f",
        ])
        ctypes.windll.gdi32.AddFontResourceExW(str(path), 0, None)
    result = ctypes.c_ulong()
    ctypes.windll.user32.SendMessageTimeoutW(
        0xFFFF, 0x001D, 0, 0, 0x0002, 5000, ctypes.byref(result)
    )


def _install_viettel_bundle(bundle: dict[str, Path], system: str) -> dict[str, str]:
    home = Path.home()
    if system == "Linux":
        paths = _copy_bundle(bundle, home / ".local/share/fonts")
        _run_checked(["fc-cache", "-f"])
        return paths
    if system == "Darwin":
        paths = _copy_bundle(bundle, home / "Library/Fonts")
        _register_macos(paths)
        return paths
    if system == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise RuntimeError("LOCALAPPDATA is not set")
        paths = _copy_bundle(bundle, Path(local_app_data) / "Microsoft/Windows/Fonts")
        _register_windows(paths)
        return paths
    raise RuntimeError(f"automatic font installation is unsupported on {system}")


def ensure_viettel_fonts(project_path: Path) -> dict[str, object]:
    """Search first, then install all three trusted bundled faces when needed."""
    system = platform.system()
    found_before = scan_installed_viettel_faces(system=system)
    missing_before = sorted(set(VIETTEL_REQUIRED_FACES) - set(found_before))
    installed_paths: dict[str, str] = {}
    error = None
    if missing_before:
        try:
            installed_paths = _install_viettel_bundle(_viettel_bundle(project_path), system)
        except Exception as exc:
            error = str(exc)
    found_after = scan_installed_viettel_faces(system=system) if missing_before else found_before
    missing_after = sorted(set(VIETTEL_REQUIRED_FACES) - set(found_after))
    return {
        "required_faces": list(VIETTEL_REQUIRED_FACES),
        "found_before": found_before,
        "missing_before": missing_before,
        "auto_installed": installed_paths,
        "found_after": found_after,
        "missing_after": missing_after,
        "install_error": error,
        "status": "installed" if not missing_after else "degraded",
        "install_dir": str(Path(next(iter(installed_paths.values()))).parent) if installed_paths else None,
    }


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
        for registry_key in WINDOWS_FONT_REGISTRY_KEYS:
            registry = _run_command(["reg", "query", registry_key])
            if not registry:
                continue
            sources.append(registry_key)
            for line in registry.splitlines():
                columns = re.split(r"\s{2,}", line.strip())
                if len(columns) >= 3 and columns[1].startswith("REG_"):
                    display_name = re.sub(r"\s*\([^)]*Type\)\s*$", "", columns[0])
                    aliases.update(family_aliases_from_name(display_name))
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
        Path(__file__).resolve().parent.parent / "templates/layouts/viettel_default/fonts",
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


def build_report(project_path: Path) -> dict[str, object]:
    lock_path = project_path / "spec_lock.md"
    if not lock_path.exists():
        raise FileNotFoundError(f"spec_lock.md not found at {lock_path}")
    lock = parse_lock(lock_path)
    stacks = collect_required_stacks(lock)
    viettel_requested = (
        lock.get("brand", {}).get("profile") == "viettel_default"
        or any(
            normalize_font_name(VIETTEL_FAMILY) in {
                normalize_font_name(family) for family in stack["families"]
            }
            for stack in stacks
        )
    )
    face_report = ensure_viettel_fonts(project_path) if viettel_requested else None
    installed_aliases, installed_sources = collect_installed_fonts()
    if face_report and face_report["status"] == "installed":
        installed_aliases.add(normalize_font_name(VIETTEL_FAMILY))
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

    degraded = (
        any(report["status"] != "installed" for report in stack_reports)
        or bool(face_report and face_report["status"] != "installed")
    )
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
            if not row["installed"]
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
        "viettel_faces": face_report,
        "stacks": stack_reports,
    }


def print_summary(report: dict[str, object]) -> None:
    summary = report["summary"]
    assert isinstance(summary, dict)
    print(f"Font preflight: brand fidelity {summary['brand_fidelity']}")
    installed = ", ".join(summary["installed"]) if summary["installed"] else "(none)"
    missing = ", ".join(summary["missing"]) if summary["missing"] else "(none)"
    print(f"Installed: {installed}")
    print(f"Missing from host: {missing}")

    face_report = report.get("viettel_faces")
    if isinstance(face_report, dict):
        required = ", ".join(face_report["required_faces"])
        found = ", ".join(face_report["found_after"]) or "(none)"
        print(f"Required Viettel faces: {required}")
        print(f"Detected Viettel faces: {found}")
        if face_report["auto_installed"]:
            installed_faces = ", ".join(face_report["auto_installed"])
            print(f"Auto-installed from bundle: {installed_faces}")
            print(f"Install directory: {face_report['install_dir']}")
        if face_report["install_error"]:
            print(f"Automatic install failed: {face_report['install_error']}")
        if face_report["missing_after"]:
            print(f"Missing after install: {', '.join(face_report['missing_after'])}")

    fallback = summary["fallback_in_use"]
    assert isinstance(fallback, list)
    if fallback:
        print(f"Fallback in use: {', '.join(fallback)}")

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
        return 1 if report["summary"]["brand_fidelity"] == "degraded" else 0

    print_summary(report)
    print(f"Report written: {output_path}")
    return 1 if report["summary"]["brand_fidelity"] == "degraded" else 0


if __name__ == "__main__":
    raise SystemExit(main())
