#!/usr/bin/env python3
"""Regression check for the native-only PPTX exporter."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("svg_to_pptx.py")
SVG = """<svg width="1280" height="720" viewBox="0 0 1280 720"
xmlns="http://www.w3.org/2000/svg">
<rect width="1280" height="720" fill="#FFFFFF"/>
<text x="80" y="120" font-family="Arial" font-size="32">Native export</text>
</svg>"""


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        output_dir = project / "svg_output"
        output_dir.mkdir()
        (output_dir / "01_smoke.svg").write_text(SVG, encoding="utf-8")
        pptx_path = project / "smoke.pptx"

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                str(project),
                "-o",
                str(pptx_path),
                "-q",
                "-a",
                "none",
                "-t",
                "none",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr or result.stdout
        with zipfile.ZipFile(pptx_path) as archive:
            names = archive.namelist()
        assert not any("notesSlide" in name for name in names)
        assert not any(
            name.lower().endswith((".mp3", ".wav", ".m4a"))
            for name in names
        )

        removed = subprocess.run(
            [sys.executable, str(SCRIPT), str(project), "--svg-snapshot"],
            text=True,
            capture_output=True,
            check=False,
        )
        assert removed.returncode == 2

    print("OK: native-only export")


if __name__ == "__main__":
    main()
