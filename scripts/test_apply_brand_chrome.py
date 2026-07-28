#!/usr/bin/env python3
"""Small CLI regression check for apply_brand_chrome.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("apply_brand_chrome.py")
CHECKER = Path(__file__).with_name("svg_quality_checker.py")
SVG = '<svg width="1280" height="720" viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg"></svg>'


def run(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *(str(arg) for arg in args)],
        text=True,
        capture_output=True,
        check=False,
    )


def check(target: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), str(target)],
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        project = root / "project"
        output = project / "svg_output"
        output.mkdir(parents=True)
        first = output / "01_first.svg"
        second = output / "02_second.svg"
        third = output / "03_third.svg"
        first.write_text(SVG, encoding="utf-8")
        second.write_text(SVG, encoding="utf-8")
        third.write_text(SVG, encoding="utf-8")
        second_before = second.read_bytes()
        third_before = third.read_bytes()
        second_mtime = second.stat().st_mtime_ns
        third_mtime = third.stat().st_mtime_ns

        args = (
            project,
            "--brand-chrome", "viettel",
            "--file", "svg_output/01_first.svg",
            "--slide-number", 1,
        )
        assert run(*args).returncode == 0
        once = first.read_text(encoding="utf-8")
        assert once.count("viettel-logo.png") == 1
        assert once.count(">01</text>") == 1
        assert second.read_bytes() == second_before
        assert third.read_bytes() == third_before
        assert second.stat().st_mtime_ns == second_mtime
        assert third.stat().st_mtime_ns == third_mtime

        assert run(*args).returncode == 0
        assert first.read_text(encoding="utf-8") == once

        assert run(project, "--brand-chrome", "viettel").returncode == 0
        assert second.read_text(encoding="utf-8").count("viettel-logo.png") == 1
        assert third.read_text(encoding="utf-8").count("viettel-logo.png") == 1
        assert check(first).returncode == 0
        assert check(second).returncode == 0
        assert check(third).returncode == 0
        assert check(project).returncode == 0

        assert run(project, "--file", "svg_output/01_first.svg").returncode == 1
        assert run(project, "--file", "svg_output/01_first.svg", "--slide-number", 0).returncode == 1
        assert run(project, "--slide-number", 1).returncode == 1
        assert run(project, "--file", "svg_output/missing.svg", "--slide-number", 1).returncode == 1
        outside = root / "outside.svg"
        outside.write_text(SVG, encoding="utf-8")
        assert run(project, "--file", outside, "--slide-number", 1).returncode == 1

    print("OK: single-file and project-wide brand chrome modes")


if __name__ == "__main__":
    main()
