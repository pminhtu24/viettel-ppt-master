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
<use data-icon="tabler-filled/layout-cards" x="40" y="40" width="48" height="48" fill="#000000"/>
<text x="80" y="120" font-family="FS Magistral" font-size="32" font-weight="400">Book</text>
<text x="80" y="180" font-family="FS Magistral" font-size="32" font-weight="500">Medium</text>
<text x="80" y="240" font-family="FS Magistral" font-size="32" font-weight="700">Bold</text>
</svg>"""


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        output_dir = project / "svg_output"
        output_dir.mkdir()
        (output_dir / "01_smoke.svg").write_text(SVG, encoding="utf-8")
        (project / "spec_lock.md").write_text(
            '## brand\n- profile: viettel_default\n\n'
            '## typography\n- font_family: "FS Magistral"\n',
            encoding="utf-8",
        )
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
            slide_xml = archive.read("ppt/slides/slide1.xml").decode()
            presentation_xml = archive.read("ppt/presentation.xml").decode()
            presentation_rels = archive.read("ppt/_rels/presentation.xml.rels").decode()
            content_types = archive.read("[Content_Types].xml").decode()
        assert not any("notesSlide" in name for name in names)
        assert not any(
            name.lower().endswith((".mp3", ".wav", ".m4a"))
            for name in names
        )
        for face in ("Book", "Medium", "Bold"):
            typeface = f"FS Magistral {face}"
            assert f'typeface="{typeface}"' in slide_xml
            assert f'<p:font typeface="{typeface}"' in presentation_xml
        assert 'saveSubsetFonts="0"' in presentation_xml
        assert 'typeface="FS Magistral"' not in slide_xml
        assert ' b="1"' not in slide_xml
        assert presentation_rels.count("/relationships/font") == 3
        assert content_types.count('Extension="fntdata"') == 1
        font_parts = [name for name in names if name.startswith("ppt/fonts/fontData")]
        assert len(font_parts) == 3
        with zipfile.ZipFile(pptx_path) as archive:
            assert all(archive.read(name) for name in font_parts)

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
