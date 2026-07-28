"""Find SVG files in a project directory."""

from __future__ import annotations

from pathlib import Path


def find_svg_files(project_path: Path) -> tuple[list[Path], str]:
    """Return sorted SVG files from the canonical svg_output directory."""
    svg_dir = project_path / "svg_output"
    if not svg_dir.is_dir():
        return [], "svg_output"
    return sorted(svg_dir.glob("*.svg")), "svg_output"
