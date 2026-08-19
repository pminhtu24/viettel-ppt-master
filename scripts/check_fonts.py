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
import getpass
import json
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path, PureWindowsPath

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
WINDOWS_FONT_REGISTRY_SUBKEY = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
_FOLDERID_LOCAL_APP_DATA = (
    0xF1B32785,
    0x6FBA,
    0x4FCF,
    (0x9D, 0x55, 0x7B, 0x8E, 0x7F, 0x15, 0x70, 0x91),
)


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def normalize_font_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _is_absolute_windows_path(value: str | None) -> bool:
    """Reject shell placeholders and cwd-relative Windows install targets."""
    if not value or "%" in value:
        return False
    return PureWindowsPath(value).is_absolute() or Path(value).is_absolute()


def _windows_directory() -> Path:
    configured = os.environ.get("WINDIR")
    if _is_absolute_windows_path(configured):
        return Path(configured)
    buffer = ctypes.create_unicode_buffer(32768)
    length = ctypes.windll.kernel32.GetWindowsDirectoryW(buffer, len(buffer))
    if not length or length >= len(buffer):
        raise RuntimeError("Windows directory could not be resolved")
    return Path(buffer.value)


def _windows_local_app_data() -> tuple[Path, str]:
    configured = os.environ.get("LOCALAPPDATA")
    if _is_absolute_windows_path(configured):
        return Path(configured), "environment"

    data1, data2, data3, data4 = _FOLDERID_LOCAL_APP_DATA
    folder_id = _GUID(data1, data2, data3, (ctypes.c_ubyte * 8)(*data4))
    output = ctypes.c_wchar_p()
    known_folder = ctypes.windll.shell32.SHGetKnownFolderPath
    known_folder.argtypes = [
        ctypes.POINTER(_GUID),
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_wchar_p),
    ]
    known_folder.restype = ctypes.c_long
    result = known_folder(
        ctypes.byref(folder_id), 0, None, ctypes.byref(output)
    )
    if result != 0 or not output.value:
        raise RuntimeError("Local AppData could not be resolved from Windows Known Folders")
    try:
        return Path(output.value), "known-folder"
    finally:
        free_memory = ctypes.windll.ole32.CoTaskMemFree
        free_memory.argtypes = [ctypes.c_void_p]
        free_memory(ctypes.cast(output, ctypes.c_void_p))


def _windows_font_dirs() -> tuple[Path, Path | None, str | None]:
    system_dir = _windows_directory() / "Fonts"
    try:
        local_app_data, source = _windows_local_app_data()
    except (AttributeError, OSError, RuntimeError):
        return system_dir, None, None
    return system_dir, local_app_data / "Microsoft/Windows/Fonts", source


def _windows_is_elevated() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


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
    if system == "Windows":
        system_dir, user_dir, _ = _windows_font_dirs()
        return [system_dir, *([user_dir] if user_dir else [])]
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


def _windows_registry_entries() -> list[tuple[str, str, str]]:
    """Return (scope, display name, data) without parsing localized reg.exe output."""
    try:
        import winreg
    except ImportError:
        return []

    entries: list[tuple[str, str, str]] = []
    for scope, hive in (("user", winreg.HKEY_CURRENT_USER), ("system", winreg.HKEY_LOCAL_MACHINE)):
        try:
            key = winreg.OpenKey(hive, WINDOWS_FONT_REGISTRY_SUBKEY)
        except OSError:
            continue
        with key:
            index = 0
            while True:
                try:
                    name, data, _ = winreg.EnumValue(key, index)
                except OSError:
                    break
                index += 1
                if isinstance(name, str) and isinstance(data, str):
                    entries.append((scope, name, data))
    return entries


def _registry_font_candidates(
    scope: str,
    data: str,
    system_dir: Path,
    user_dir: Path | None,
) -> list[Path]:
    expanded = os.path.expandvars(data).strip().strip('"')
    path = Path(expanded)
    if path.is_absolute() or PureWindowsPath(expanded).is_absolute():
        return [path]
    if scope == "user":
        candidates = [user_dir / expanded] if user_dir else []
        return [*candidates, system_dir / expanded]
    return [system_dir / expanded]


def _faces_from_windows_registry(
    font_dirs: list[Path] | None = None,
) -> dict[str, str]:
    dirs = font_dirs or _font_dirs("Windows")
    system_dir = dirs[0] if dirs else _windows_directory() / "Fonts"
    user_dir = dirs[1] if len(dirs) > 1 else None
    found: dict[str, str] = {}
    for scope, _display_name, data in _windows_registry_entries():
        candidates = _registry_font_candidates(scope, data, system_dir, user_dir)
        for path in candidates:
            face = _font_file_face(path)
            if face:
                found.setdefault(face, str(path))
                break
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
        dirs = font_dirs or _font_dirs(system)
        found = _faces_from_windows_registry(dirs)
        for face, path in _faces_from_font_dirs(dirs).items():
            found.setdefault(face, path)
        return found
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


def _copy_bundle(
    bundle: dict[str, Path],
    target: Path,
    faces: set[str] | None = None,
) -> dict[str, str]:
    target.mkdir(parents=True, exist_ok=True)
    installed: dict[str, str] = {}
    for face, source in bundle.items():
        if faces is not None and face not in faces:
            continue
        destination = target / source.name
        if destination.exists():
            if _font_file_face(destination) != face:
                raise FileExistsError(f"font target conflicts with bundled face: {destination}")
        else:
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
    """Register copied fonts transactionally and verify GDI accepted each file."""
    import winreg

    access = winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE
    previous: dict[str, tuple[object, int] | None] = {}
    registered: list[str] = []
    key = winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER, WINDOWS_FONT_REGISTRY_SUBKEY, 0, access
    )
    try:
        for face, path in paths.items():
            value_name = f"{VIETTEL_FAMILY} {face} (TrueType)"
            try:
                previous[value_name] = winreg.QueryValueEx(key, value_name)
            except FileNotFoundError:
                previous[value_name] = None
            winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, str(path))
            added = ctypes.windll.gdi32.AddFontResourceExW(str(path), 0, None)
            if not added:
                raise RuntimeError(f"Windows GDI rejected font: {path}")
            registered.append(str(path))
    except Exception:
        for path in reversed(registered):
            ctypes.windll.gdi32.RemoveFontResourceExW(path, 0, None)
        for value_name, old_value in previous.items():
            try:
                if old_value is None:
                    winreg.DeleteValue(key, value_name)
                else:
                    value, value_type = old_value
                    winreg.SetValueEx(key, value_name, 0, value_type, value)
            except OSError:
                pass
        raise
    finally:
        winreg.CloseKey(key)

    result = ctypes.c_ulong()
    ctypes.windll.user32.SendMessageTimeoutW(
        0xFFFF, 0x001D, 0, 0, 0x0002, 5000, ctypes.byref(result)
    )


def _install_windows_bundle(bundle: dict[str, Path]) -> dict[str, str]:
    _, target, _ = _windows_font_dirs()
    if target is None:
        raise RuntimeError("per-user Fonts directory is unavailable")
    created = {
        target / source.name
        for source in bundle.values()
        if not (target / source.name).exists()
    }
    try:
        paths = _copy_bundle(bundle, target)
        _register_windows(paths)
        return paths
    except Exception:
        for path in created:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        raise


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
        return _install_windows_bundle(bundle)
    raise RuntimeError(f"automatic font installation is unsupported on {system}")


def ensure_viettel_fonts(project_path: Path) -> dict[str, object]:
    """Search first, then install only the missing trusted bundled faces."""
    system = platform.system()
    found_before = scan_installed_viettel_faces(system=system)
    missing_before = sorted(set(VIETTEL_REQUIRED_FACES) - set(found_before))
    installed_paths: dict[str, str] = {}
    error = None
    if missing_before:
        try:
            bundle = _viettel_bundle(project_path)
            installed_paths = _install_viettel_bundle(
                {face: bundle[face] for face in missing_before}, system
            )
        except Exception as exc:
            error = str(exc)
    found_after = scan_installed_viettel_faces(system=system) if missing_before else found_before
    missing_after = sorted(set(VIETTEL_REQUIRED_FACES) - set(found_after))
    install_scope = "user" if installed_paths and system == "Windows" else None
    return {
        "required_faces": list(VIETTEL_REQUIRED_FACES),
        "found_before": found_before,
        "missing_before": missing_before,
        "auto_installed": installed_paths,
        "found_after": found_after,
        "missing_after": missing_after,
        "install_error": error,
        "status": "installed" if not missing_after and error is None else "degraded",
        "install_dir": str(Path(next(iter(installed_paths.values()))).parent) if installed_paths else None,
        "install_scope": install_scope,
        "restart_powerpoint": bool(installed_paths and system == "Windows"),
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
        entries = _windows_registry_entries()
        if entries:
            sources.extend(WINDOWS_FONT_REGISTRY_KEYS)
        for _, display_name, _ in entries:
            clean = re.sub(r"\s*\([^)]*Type\)\s*$", "", display_name)
            aliases.update(family_aliases_from_name(clean))
        font_dirs.extend(_font_dirs("Windows"))
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

    environment: dict[str, object] = {
        "os": platform.system(),
        "installed_font_sources": installed_sources,
    }
    if platform.system() == "Windows":
        environment.update({"process_user": getpass.getuser(), "elevated": _windows_is_elevated()})
        try:
            system_dir, user_dir, local_source = _windows_font_dirs()
            environment.update(
                {
                    "windows_font_dir": str(system_dir),
                    "user_font_dir": str(user_dir) if user_dir else None,
                    "local_app_data_source": local_source,
                }
            )
        except RuntimeError as exc:
            environment["windows_font_resolution_error"] = str(exc)

    return {
        "project": str(project_path),
        "brand_profile": lock.get("brand", {}).get("profile"),
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
        "environment": environment,
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
            if face_report.get("install_scope"):
                print(f"Install scope: {face_report['install_scope']}")
            if face_report.get("restart_powerpoint"):
                print("Restart PowerPoint to refresh its font catalog.")
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
