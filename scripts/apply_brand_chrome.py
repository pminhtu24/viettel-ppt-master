#!/usr/bin/env python3
"""Apply deck-level brand chrome to PPT Master SVG pages."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path
from xml.etree import ElementTree as ET


COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
VIETTEL_FONT_STACK = '&quot;FS Magistral&quot;'


def strip_svg_comments(svg: str) -> str:
    return COMMENT_RE.sub("", svg)


def ensure_viettel_logo(project_dir: Path, skill_dir: Path) -> None:
    images_dir = project_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    target = images_dir / "viettel-logo.png"
    if target.exists():
        return
    source = skill_dir / "templates" / "layouts" / "viettel_default" / "viettel-logo.png"
    if source.exists():
        shutil.copy2(source, target)


def _has_viettel_top_bar(svg: str) -> bool:
    return bool(re.search(
        r'<rect\b(?=[^>]*\bx=["\']0["\'])(?=[^>]*\by=["\']0["\'])'
        r'(?=[^>]*\bwidth=["\']1280["\'])(?=[^>]*\bheight=["\']5["\'])'
        r'(?=[^>]*\bfill=["\']#EE0033["\'])',
        svg,
        re.IGNORECASE,
    ))


def _has_viettel_logo(svg: str) -> bool:
    return bool(re.search(
        r'<image\b(?=[^>]*(?:href|xlink:href)=["\'][^"\']*viettel-logo\.png["\'])'
        r'(?=[^>]*\bx=["\']1088["\'])(?=[^>]*\by=["\']28["\'])'
        r'(?=[^>]*\bwidth=["\']128["\'])(?=[^>]*\bheight=["\']42["\'])',
        svg,
        re.IGNORECASE,
    ))


def _has_viettel_page_number(svg: str) -> bool:
    """Detect existing Viettel footer/page-number treatment.

    Shell pages use either a red badge at x=1174/y=684 or a small bottom-right
    number. Treat both as authoritative so post-processing does not duplicate
    slide numbers.
    """
    has_badge = bool(re.search(
        r'<rect\b(?=[^>]*\bx=["\']1174["\'])(?=[^>]*\by=["\']684["\'])'
        r'(?=[^>]*\bwidth=["\']42["\'])(?=[^>]*\bheight=["\']26["\'])',
        svg,
        re.IGNORECASE,
    ))
    if has_badge:
        return True
    try:
        root = ET.fromstring(svg)
    except ET.ParseError:
        return False
    for elem in root.iter():
        if _local_name(elem.tag) != "text":
            continue
        text = "".join(elem.itertext()).strip().replace(" ", "")
        if text != "{{PAGE_NUM}}" and not re.fullmatch(r"\d{1,3}(?:/\d{1,3})?", text):
            continue
        x = _float_attr(elem, "x")
        y = _float_attr(elem, "y")
        if x >= 1140 and y >= 640:
            return True
    return False


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _float_attr(elem: ET.Element, name: str) -> float:
    raw = (elem.get(name) or "").strip()
    if raw.endswith("px"):
        raw = raw[:-2]
    try:
        return float(raw)
    except ValueError:
        return 0.0


def viettel_chrome_svg(
    slide_number: int | None = None,
    *,
    include_top_bar: bool = True,
    include_logo: bool = True,
    include_page_number: bool = True,
) -> str:
    page = "" if slide_number is None else f"{slide_number:02d}"
    page_text = (
        f'<text x="1216" y="704" text-anchor="end" '
        f'font-family="{VIETTEL_FONT_STACK}" '
        f'font-size="11" font-weight="400" fill="#44494D">{page}</text>'
        if page and include_page_number
        else ""
    )
    top_bar = (
        '<rect x="0" y="0" width="1280" height="5" fill="#EE0033"/>'
        if include_top_bar
        else ""
    )
    logo = (
        '<image href="../images/viettel-logo.png" x="1088" y="28" width="128" height="42" preserveAspectRatio="xMidYMid meet"/>'
        if include_logo
        else ""
    )
    return (
        '\n<g id="viettel-brand-chrome" data-brand="viettel">'
        f"{top_bar}"
        f"{logo}"
        f"{page_text}"
        "</g>\n"
    )


def apply_viettel_chrome(svg: str, slide_number: int | None = None) -> str:
    if 'id="viettel-brand-chrome"' in svg:
        return svg
    marker = "</svg>"
    if marker not in svg:
        return svg
    include_top_bar = not _has_viettel_top_bar(svg)
    include_logo = not _has_viettel_logo(svg)
    include_page_number = not _has_viettel_page_number(svg)
    if not any((include_top_bar, include_logo, include_page_number)):
        return svg
    chrome = viettel_chrome_svg(
        slide_number,
        include_top_bar=include_top_bar,
        include_logo=include_logo,
        include_page_number=include_page_number,
    )
    return svg.replace(marker, chrome + marker, 1)


def process_svg_file(
    svg_file: Path,
    *,
    brand_chrome: str | None = None,
    strip_comments: bool = False,
    slide_number: int | None = None,
) -> bool:
    original = svg_file.read_text(encoding="utf-8")
    updated = original
    if strip_comments:
        updated = strip_svg_comments(updated)
    if brand_chrome == "viettel":
        updated = apply_viettel_chrome(updated, slide_number)
    if updated == original:
        return False
    svg_file.write_text(updated, encoding="utf-8")
    return True


def process_project(
    project_dir: Path,
    *,
    brand_chrome: str | None = None,
    strip_comments: bool = False,
    skill_dir: Path | None = None,
) -> int:
    svg_dirs = [
        path
        for path in (project_dir / "svg_output", project_dir / "svg_final")
        if path.exists()
    ]
    if brand_chrome == "viettel" and skill_dir is not None:
        ensure_viettel_logo(project_dir, skill_dir)
    count = 0
    for svg_dir in svg_dirs:
        for index, svg_file in enumerate(sorted(svg_dir.glob("*.svg")), start=1):
            if process_svg_file(
                svg_file,
                brand_chrome=brand_chrome,
                strip_comments=strip_comments,
                slide_number=index,
            ):
                count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply optional brand chrome to PPT Master SVG pages.")
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--brand-chrome", choices=["viettel"], help="Brand chrome to inject")
    parser.add_argument("--strip-comments", action="store_true", help="Remove XML comments from SVG files")
    args = parser.parse_args()
    skill_dir = Path(__file__).resolve().parent.parent
    count = process_project(
        args.project_dir,
        brand_chrome=args.brand_chrome,
        strip_comments=args.strip_comments,
        skill_dir=skill_dir,
    )
    print(f"Processed {count} SVG file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
