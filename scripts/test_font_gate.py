#!/usr/bin/env python3
"""Regression checks for FS Magistral discovery, auto-install, and export gate."""

from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from check_fonts import (
    VIETTEL_REQUIRED_FACES,
    _is_absolute_windows_path,
    _windows_local_app_data,
    _faces_from_windows_registry,
    _faces_from_font_dirs,
    _font_file_face,
    _install_viettel_bundle,
    _install_windows_bundle,
    _register_windows,
    scan_installed_viettel_faces,
    _viettel_bundle,
    ensure_viettel_fonts,
)
from project_manager import ProjectManager
from svg_to_pptx.pptx_cli import _font_gate_errors


def main() -> None:
    skill_root = Path(__file__).resolve().parent.parent
    bundled = skill_root / "templates/layouts/viettel_default/fonts"
    for face, filename in VIETTEL_REQUIRED_FACES.items():
        assert _font_file_face(bundled / filename) == face

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        system_fonts = root / "Windows/Fonts"
        user_fonts = root / "LocalAppData/Microsoft/Windows/Fonts"
        system_fonts.mkdir(parents=True)
        user_fonts.mkdir(parents=True)
        for filename in VIETTEL_REQUIRED_FACES.values():
            shutil.copy2(bundled / filename, system_fonts / filename)
        registry_entries = [
            ("system", f"FS Magistral {face} Regular (TrueType)", filename)
            for face, filename in VIETTEL_REQUIRED_FACES.items()
        ]
        with patch("check_fonts._windows_registry_entries", return_value=registry_entries):
            found = _faces_from_windows_registry([system_fonts, user_fonts])
        assert set(found) == set(VIETTEL_REQUIRED_FACES)
        assert all(Path(path).parent == system_fonts for path in found.values())
        with patch("check_fonts._windows_registry_entries", return_value=[]):
            found_from_dirs = scan_installed_viettel_faces(
                system="Windows", font_dirs=[system_fonts, user_fonts]
            )
        assert set(found_from_dirs) == set(VIETTEL_REQUIRED_FACES)
        assert not _is_absolute_windows_path("%LOCALAPPDATA%")
        assert not _is_absolute_windows_path(r".\%LOCALAPPDATA%")
        assert _is_absolute_windows_path(r"C:\Users\tester\AppData\Local")

        class FakeWindowsApi:
            def __init__(self, callback):
                self.callback = callback
                self.argtypes = None
                self.restype = None

            def __call__(self, *args):
                return self.callback(*args)

        known_folder = FakeWindowsApi(
            lambda _guid, _flags, _token, output: (
                setattr(output._obj, "value", str(root / "KnownLocalAppData")) or 0
            )
        )
        free_memory = FakeWindowsApi(lambda _pointer: None)
        fake_windll = SimpleNamespace(
            shell32=SimpleNamespace(SHGetKnownFolderPath=known_folder),
            ole32=SimpleNamespace(CoTaskMemFree=free_memory),
        )
        with patch.dict(os.environ, {"LOCALAPPDATA": "%LOCALAPPDATA%"}, clear=True), patch(
            "check_fonts.ctypes.windll", fake_windll, create=True
        ):
            local_app_data, source = _windows_local_app_data()
        assert local_app_data == root / "KnownLocalAppData"
        assert source == "known-folder"

        renamed_dir = root / "renamed"
        renamed_dir.mkdir()
        renamed = renamed_dir / "unrelated-name.ttf"
        shutil.copy2(bundled / VIETTEL_REQUIRED_FACES["Book"], renamed)
        assert _faces_from_font_dirs([renamed_dir]) == {"Book": str(renamed)}

        all_faces = {face: f"/fonts/{filename}" for face, filename in VIETTEL_REQUIRED_FACES.items()}
        with (
            patch("check_fonts.scan_installed_viettel_faces", return_value=all_faces),
            patch("check_fonts._install_viettel_bundle") as install,
        ):
            report = ensure_viettel_fonts(root)
        assert report["status"] == "installed"
        assert not report["auto_installed"]
        install.assert_not_called()

        with (
            patch("check_fonts.scan_installed_viettel_faces", side_effect=[{}, all_faces]),
            patch("check_fonts._viettel_bundle", return_value=_viettel_bundle(root)),
            patch("check_fonts._install_viettel_bundle", return_value=all_faces) as install,
        ):
            report = ensure_viettel_fonts(root)
        assert report["status"] == "installed"
        assert set(report["auto_installed"]) == set(VIETTEL_REQUIRED_FACES)
        assert len(install.call_args.args[0]) == 3

        partial_faces = {face: path for face, path in all_faces.items() if face != "Bold"}
        with (
            patch("check_fonts.scan_installed_viettel_faces", side_effect=[partial_faces, all_faces]),
            patch("check_fonts._install_viettel_bundle", return_value=all_faces) as install,
        ):
            report = ensure_viettel_fonts(root)
        assert report["missing_before"] == ["Bold"]
        assert set(install.call_args.args[0]) == {"Bold"}

        with (
            patch("check_fonts.scan_installed_viettel_faces", side_effect=[{}, {}]),
            patch("check_fonts._install_viettel_bundle", side_effect=RuntimeError("registry denied")),
        ):
            report = ensure_viettel_fonts(root)
        assert report["status"] == "degraded"
        assert report["install_error"] == "registry denied"

        with (
            patch("check_fonts.scan_installed_viettel_faces", side_effect=[{}, all_faces]),
            patch("check_fonts._install_viettel_bundle", side_effect=RuntimeError("GDI rejected")),
        ):
            report = ensure_viettel_fonts(root)
        assert report["status"] == "degraded"

        bad_project = root / "bad-project"
        (bad_project / "fonts").mkdir(parents=True)
        (bad_project / "fonts" / VIETTEL_REQUIRED_FACES["Book"]).write_bytes(b"not a font")
        try:
            _viettel_bundle(bad_project)
        except ValueError as exc:
            assert "metadata mismatch" in str(exc)
        else:
            raise AssertionError("corrupt bundled font was accepted")

        bundle = _viettel_bundle(root)
        linux_home = root / "linux"
        with patch("check_fonts.Path.home", return_value=linux_home), patch("check_fonts._run_checked") as run:
            paths = _install_viettel_bundle(bundle, "Linux")
        assert len(paths) == 3 and all(Path(path).is_file() for path in paths.values())
        run.assert_called_once_with(["fc-cache", "-f"])

        mac_home = root / "mac"
        with patch("check_fonts.Path.home", return_value=mac_home), patch("check_fonts._register_macos") as register:
            paths = _install_viettel_bundle(bundle, "Darwin")
        register.assert_called_once_with(paths)

        windows_system = root / "windows-system"
        windows_user = root / "windows-user"
        user_paths = {
            face: str(windows_user / source.name) for face, source in bundle.items()
        }
        with (
            patch(
                "check_fonts._windows_font_dirs",
                return_value=(windows_system, windows_user, "known-folder"),
            ),
            patch(
                "check_fonts._install_windows_scope",
                side_effect=[PermissionError("system denied"), user_paths],
            ) as install_scope,
        ):
            paths = _install_windows_bundle(bundle)
        assert paths == user_paths
        assert [call.args[2] for call in install_scope.call_args_list] == ["system", "user"]

        registry_state = {}
        fake_winreg = SimpleNamespace(
            HKEY_LOCAL_MACHINE=1,
            HKEY_CURRENT_USER=2,
            KEY_QUERY_VALUE=1,
            KEY_SET_VALUE=2,
            REG_SZ=1,
            CreateKeyEx=lambda *args: object(),
            QueryValueEx=lambda *args: (_ for _ in ()).throw(FileNotFoundError()),
            SetValueEx=lambda key, name, reserved, kind, value: registry_state.__setitem__(name, value),
            DeleteValue=lambda key, name: registry_state.pop(name, None),
            CloseKey=lambda key: None,
        )
        fake_gdi = SimpleNamespace(
            AddFontResourceExW=lambda *args: 0,
            RemoveFontResourceExW=lambda *args: 1,
        )
        fake_windll = SimpleNamespace(gdi32=fake_gdi, user32=SimpleNamespace())
        with patch.dict(sys.modules, {"winreg": fake_winreg}), patch(
            "check_fonts.ctypes.windll", fake_windll, create=True
        ):
            try:
                _register_windows({"Bold": str(bundled / VIETTEL_REQUIRED_FACES["Bold"])})
            except RuntimeError as exc:
                assert "GDI rejected" in str(exc)
            else:
                raise AssertionError("GDI registration failure was accepted")

        fake_gdi.AddFontResourceExW = lambda *args: 1
        fake_user32 = SimpleNamespace(SendMessageTimeoutW=lambda *args: 1)
        fake_windll = SimpleNamespace(gdi32=fake_gdi, user32=fake_user32)
        with patch.dict(sys.modules, {"winreg": fake_winreg}), patch(
            "check_fonts.ctypes.windll", fake_windll, create=True
        ):
            _register_windows(
                {"Bold": str(bundled / VIETTEL_REQUIRED_FACES["Bold"])}, scope="system"
            )
        assert registry_state["FS Magistral Bold (TrueType)"] == "FS Magistral-Bold.ttf"

        init_project = root / "init-project"
        (init_project / "templates").mkdir(parents=True)
        (init_project / "images").mkdir()
        init_report = {
            "auto_installed": all_faces,
            "status": "installed",
            "install_error": None,
            "missing_after": [],
        }
        with patch("project_manager.ensure_viettel_fonts", return_value=init_report) as ensure:
            ProjectManager._install_viettel_default_template(init_project)
        ensure.assert_called_once_with(init_project)
        assert {path.name for path in (init_project / "fonts").glob("*.ttf")} == set(
            VIETTEL_REQUIRED_FACES.values()
        )

        project = root / "project"
        project.mkdir()
        (project / "spec_lock.md").write_text(
            "## brand\n- profile: viettel_default\n\n"
            "## typography\n- font_family: \"FS Magistral\"\n- body: 20\n",
            encoding="utf-8",
        )
        svg_dir = project / "svg_output"
        svg_dir.mkdir()
        slide = svg_dir / "slide.svg"
        slide.write_text(
            '<svg width="1280" height="720" viewBox="0 0 1280 720" '
            'xmlns="http://www.w3.org/2000/svg">'
            '<text x="10" y="30" font-family="Arial" font-size="20">Bad font</text>'
            '</svg>',
            encoding="utf-8",
        )
        missing_report = {
            "brand_profile": "viettel_default",
            "summary": {"brand_fidelity": "degraded"},
            "viettel_faces": {"missing_after": ["Bold"], "install_error": "registry denied"},
            "stacks": [{"key": "font_family", "stack": '"FS Magistral"', "status": "missing", "active_family": None}],
        }
        errors = _font_gate_errors(project, [slide], report=missing_report)
        assert any("missing FS Magistral faces" in error for error in errors), errors
        assert any("[brand-font]" in error for error in errors), errors

        override_errors = _font_gate_errors(
            project, [slide], report=missing_report, allow_font_fallback=True
        )
        assert not any("missing FS Magistral faces" in error for error in override_errors)
        assert any("[brand-font]" in error for error in override_errors)

        slide.write_text(
            slide.read_text(encoding="utf-8").replace('font-family="Arial"', 'font-family="FS Magistral"'),
            encoding="utf-8",
        )
        assert not _font_gate_errors(
            project, [slide], report=missing_report, allow_font_fallback=True
        )

        slide.write_text(
            slide.read_text(encoding="utf-8").replace('font-family="FS Magistral"', 'font-family="fs magistral"'),
            encoding="utf-8",
        )
        casing_errors = _font_gate_errors(
            project, [slide], report=missing_report, allow_font_fallback=True
        )
        assert any("[brand-font]" in error for error in casing_errors), casing_errors

        slide.write_text(
            slide.read_text(encoding="utf-8").replace('font-family="fs magistral"', 'font-family="FS Magistral"'),
            encoding="utf-8",
        )
        lock_text = (project / "spec_lock.md").read_text(encoding="utf-8")
        (project / "spec_lock.md").unlink()
        no_lock_errors = _font_gate_errors(project, [slide], allow_font_fallback=True)
        assert any("requires spec_lock.md" in error for error in no_lock_errors), no_lock_errors
        (project / "spec_lock.md").write_text(lock_text, encoding="utf-8")

        if sys.platform.startswith("linux"):
            isolated_home = root / "isolated-home"
            font_dir = isolated_home / ".local/share/fonts"
            cache_dir = isolated_home / ".cache/fontconfig"
            fontconfig = root / "fonts.conf"
            fontconfig.write_text(
                '<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd">'
                f'<fontconfig><dir>{font_dir}</dir><cachedir>{cache_dir}</cachedir></fontconfig>',
                encoding="utf-8",
            )
            env = dict(os.environ, HOME=str(isolated_home), FONTCONFIG_FILE=str(fontconfig))
            preflight = subprocess.run(
                [sys.executable, str(Path(__file__).with_name("check_fonts.py")), str(project), "--json-only"],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            assert preflight.returncode == 0, preflight.stdout + preflight.stderr
            payload = json.loads((project / "font_preflight.json").read_text(encoding="utf-8"))
            assert set(payload["viettel_faces"]["auto_installed"]) == set(VIETTEL_REQUIRED_FACES)
            assert not payload["viettel_faces"]["missing_after"]

    print("OK: FS Magistral auto-install and export gate")


if __name__ == "__main__":
    main()
