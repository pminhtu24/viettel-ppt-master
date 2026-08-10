#!/usr/bin/env python3
"""Regression checks for FS Magistral discovery, auto-install, and export gate."""

from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from check_fonts import (
    VIETTEL_REQUIRED_FACES,
    _faces_from_windows_registry,
    _faces_from_font_dirs,
    _font_file_face,
    _install_viettel_bundle,
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

    registry = "\n".join(
        f"FS Magistral {face} (TrueType)    REG_SZ    C:\\Fonts\\{filename}"
        for face, filename in VIETTEL_REQUIRED_FACES.items()
    )
    with patch("check_fonts._run_command", return_value=registry):
        assert set(_faces_from_windows_registry()) == set(VIETTEL_REQUIRED_FACES)

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        renamed = root / "unrelated-name.ttf"
        shutil.copy2(bundled / VIETTEL_REQUIRED_FACES["Book"], renamed)
        assert _faces_from_font_dirs([root]) == {"Book": str(renamed)}

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
        assert len(install.call_args.args[0]) == 3

        with (
            patch("check_fonts.scan_installed_viettel_faces", side_effect=[{}, {}]),
            patch("check_fonts._install_viettel_bundle", side_effect=RuntimeError("registry denied")),
        ):
            report = ensure_viettel_fonts(root)
        assert report["status"] == "degraded"
        assert report["install_error"] == "registry denied"

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

        windows_root = root / "windows"
        with patch.dict("check_fonts.os.environ", {"LOCALAPPDATA": str(windows_root)}), patch(
            "check_fonts._register_windows"
        ) as register:
            paths = _install_viettel_bundle(bundle, "Windows")
        register.assert_called_once_with(paths)

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
