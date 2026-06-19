#!/usr/bin/env python3
"""
PPT Master - SVG Quality Check Tool

Checks whether SVG files comply with project technical specifications.

Usage:
    python3 scripts/svg_quality_checker.py <svg_file>
    python3 scripts/svg_quality_checker.py <directory>
    python3 scripts/svg_quality_checker.py --all examples
"""

from __future__ import annotations

import sys
import re
import json
import html
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict
from xml.etree import ElementTree as ET

try:
    from project_utils import CANVAS_FORMATS
    from error_helper import ErrorHelper
except ImportError:
    print("Warning: Unable to import dependency modules")
    CANVAS_FORMATS = {}
    ErrorHelper = None

try:
    from update_spec import parse_lock as _parse_spec_lock
except ImportError:
    _parse_spec_lock = None  # spec_lock drift check will be skipped

try:
    from svg_to_pptx.animation_config import (
        load_animation_config as _load_animation_config,
        validate_animation_config as _validate_animation_config,
    )
except ImportError:
    _load_animation_config = None
    _validate_animation_config = None


HEX_VALUE_RE = re.compile(r"#[0-9A-Fa-f]{3,8}")
VIETTEL_BRAND_PROFILE = "viettel_default"
VIETTEL_CUSTOM_OVERRIDE_PROFILE = "custom_override"
VIETTEL_VIEWBOX = "0 0 1280 720"
VIETTEL_FONT_STACK = '"FS Magistral"'
VIETTEL_ALLOWED_FONT_WEIGHTS = {"", "normal", "400", "500", "bold", "700"}
VIETTEL_DEEP_BLUE = "#12436D"
VIETTEL_BLUE_SCOPES = {"chart", "diagram", "icon"}
VIETTEL_ALLOWED_COLORS = {
    "#000000",
    "#12436D",
    "#28A197",
    "#44494D",
    "#6B7280",
    "#999999",
    "#C00028",
    "#E6E6E6",
    "#EE0033",
    "#F2F2F2",
    "#F46A25",
    "#FFFFFF",
}
NON_RENDER_TAGS = {
    "defs",
    "title",
    "desc",
    "metadata",
    "linearGradient",
    "radialGradient",
    "stop",
    "filter",
    "clipPath",
    "marker",
}
VISIBLE_PRIMITIVE_TAGS = {
    "circle",
    "ellipse",
    "image",
    "line",
    "path",
    "polygon",
    "polyline",
    "rect",
    "text",
    "use",
}
WHITE_FILLS = {"#FFFFFF", "#FFF", "WHITE", "RGB(255,255,255)"}

# Ramp envelope for font-size drift detection.
# From design_spec_reference.md §IV — Font Size Hierarchy: the ramp spans
# from page-number floor (0.5x body) to cover-title ceiling (5.0x body).
# Intermediate px values within this envelope are permitted per
# executor-base.md §2.1 ("Executor may use an intermediate size ... provided
# the size's ratio to body falls within the corresponding role's band"); only
# values outside every band — i.e. outside this envelope — are drift.
RAMP_MIN_RATIO = 0.5
RAMP_MAX_RATIO = 5.0


def _local_name(tag: str) -> str:
    """Return the XML local-name for a possibly namespaced tag."""
    return tag.rsplit('}', 1)[-1] if '}' in tag else tag


def _float_attr(elem: ET.Element, name: str, default: float = 0.0) -> float:
    """Parse a numeric SVG attribute, tolerating px suffixes and blanks."""
    raw = elem.get(name)
    if raw is None:
        return default
    raw = raw.strip()
    if raw.endswith('px'):
        raw = raw[:-2]
    try:
        return float(raw)
    except ValueError:
        return default


def _parse_style_attr(elem: ET.Element, prop: str) -> str | None:
    """Read a simple inline style declaration from an SVG element."""
    style = elem.get('style') or ''
    for part in style.split(';'):
        if ':' not in part:
            continue
        key, value = part.split(':', 1)
        if key.strip() == prop:
            return value.strip()
    return None


def _get_svg_attr(elem: ET.Element, name: str, default: str = '') -> str:
    """Read presentation attributes, with inline style fallback."""
    return elem.get(name) or _parse_style_attr(elem, name) or default


def _estimate_svg_text_width(text: str, font_size: float, font_weight: str = '400') -> float:
    """Estimate text width in SVG pixels for layout-risk checks."""
    width = 0.0
    for ch in text:
        cp = ord(ch)
        is_cjk = (
            0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF or
            0x2E80 <= cp <= 0x2EFF or 0x3000 <= cp <= 0x303F or
            0xFF00 <= cp <= 0xFFEF or 0xF900 <= cp <= 0xFAFF
        )
        if is_cjk:
            width += font_size
        elif ch == ' ':
            width += font_size * 0.3
        elif ch in 'mMwWOQ':
            width += font_size * 0.75
        elif ch in 'iIlj1!|':
            width += font_size * 0.3
        else:
            width += font_size * 0.55

    if font_weight in ('bold', '600', '700', '800', '900'):
        width *= 1.08
    return width


def _parse_translate(transform: str) -> tuple[float, float]:
    """Parse translate(x[, y]) from a transform attribute."""
    if not transform:
        return 0.0, 0.0
    match = re.search(r'translate\(\s*([-\d.]+)(?:[\s,]+([-\d.]+))?', transform)
    if not match:
        return 0.0, 0.0
    return float(match.group(1)), float(match.group(2) or 0.0)


def _normalize_hex_color(value: str | None) -> str | None:
    """Return #RRGGBB for simple HEX colors, otherwise None."""
    if not value:
        return None
    raw = value.strip().upper()
    if raw in {"NONE", "TRANSPARENT"}:
        return None
    match = re.fullmatch(r"#([0-9A-F]{3}|[0-9A-F]{6}|[0-9A-F]{8})", raw)
    if not match:
        return None
    token = match.group(1)
    if len(token) == 3:
        token = "".join(ch * 2 for ch in token)
    if len(token) == 8:
        token = token[:6]
    return f"#{token}"


def _contrast_ratio(fg: str, bg: str) -> float:
    """Compute WCAG-style contrast ratio for #RRGGBB colors."""
    def channel(value: int) -> float:
        c = value / 255.0
        if c <= 0.03928:
            return c / 12.92
        return ((c + 0.055) / 1.055) ** 2.4

    def luminance(hex_color: str) -> float:
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)

    l1 = luminance(fg)
    l2 = luminance(bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _parse_placeholders_fallback(block: str) -> Dict[str, Tuple[str, ...]]:
    """Tiny YAML-free reader for the documented ``placeholders:`` shape.

    Used only when PyYAML is unavailable. Recognized lines (indentation-aware,
    two-space indent assumed):

    .. code-block:: yaml

        placeholders:
          01_cover: ["{{TITLE}}", "{{LOGO}}"]
          03_content: []
          03a_content_two_col:
            - "{{LEFT_TITLE}}"
            - "{{RIGHT_TITLE}}"

    Anything outside this minimal grammar is silently skipped — designers who
    rely on advanced YAML should install pyyaml.
    """
    out: Dict[str, Tuple[str, ...]] = {}
    inline_re = re.compile(
        r"^\s{2}([A-Za-z0-9_]+)\s*:\s*\[(.*)\]\s*$"
    )
    empty_re = re.compile(r"^\s{2}([A-Za-z0-9_]+)\s*:\s*\[\s*\]\s*$")
    block_header_re = re.compile(r"^\s{2}([A-Za-z0-9_]+)\s*:\s*$")
    item_re = re.compile(r'^\s{4}-\s*"?([^"]+)"?\s*$')

    in_section = False
    current_block_key: str | None = None
    current_items: List[str] = []

    def _flush_block() -> None:
        nonlocal current_block_key, current_items
        if current_block_key is not None:
            out[current_block_key] = tuple(current_items)
            current_block_key = None
            current_items = []

    for line in block.splitlines():
        if line.startswith("placeholders:"):
            in_section = True
            continue
        if not in_section:
            continue

        # End of section: dedent to a non-key line.
        if line and not line.startswith(" "):
            _flush_block()
            in_section = False
            continue

        if current_block_key is not None:
            m = item_re.match(line)
            if m:
                value = m.group(1).strip().strip('"').strip("'")
                if value:
                    current_items.append(value)
                continue
            # Block ended.
            _flush_block()

        if empty_re.match(line):
            key = empty_re.match(line).group(1)
            out[key] = ()
            continue

        m = inline_re.match(line)
        if m:
            key, raw = m.group(1), m.group(2)
            items = [p.strip().strip('"').strip("'") for p in raw.split(",")]
            out[key] = tuple(item for item in items if item)
            continue

        m = block_header_re.match(line)
        if m:
            current_block_key = m.group(1)
            current_items = []
            continue

    _flush_block()
    return out


class SVGQualityChecker:
    """SVG quality checker"""

    # Default placeholder convention per page-type prefix. This is a *hint*,
    # not a hard contract: templates may define their own placeholder vocabulary
    # via `placeholders:` in design_spec.md frontmatter (see
    # references/template-designer.md §4). Missing default placeholders surface
    # as warnings, never errors — designers may legitimately swap
    # `{{THANK_YOU}}` for `{{CLOSING_MESSAGE}}`, omit `{{DATE}}` when irrelevant,
    # or build content variants with bespoke slot vocabularies.
    #
    # Variants reuse the parent type's expectation (`03a_content_two_col.svg`
    # is matched by the same `03_content` rules as `03_content.svg`).
    DEFAULT_PLACEHOLDER_CONVENTION = {
        "01_cover": ("{{TITLE}}",),  # only the title is universally expected
        "02_chapter": ("{{CHAPTER_TITLE}}",),
        "02_toc": (),  # TOC layouts vary too widely to assert anything
        "03_content": ("{{PAGE_TITLE}}",),
        "04_ending": (),  # ending pages legitimately use varied vocabularies
    }

    def __init__(self, *, template_mode: bool = False):
        self.template_mode = template_mode
        self.results = []
        self.summary = {
            'total': 0,
            'passed': 0,
            'warnings': 0,
            'errors': 0
        }
        self.issue_types = defaultdict(int)
        # spec_lock drift state (populated only when _parse_spec_lock is available
        # and a spec_lock.md is found near the SVG)
        self._lock_cache: Dict[Path, Dict] = {}
        self._drift_summary: Dict[str, Dict[str, set]] = {
            'colors': defaultdict(set),
            'fonts': defaultdict(set),
            'sizes': defaultdict(set),
        }
        self._lock_seen = False  # True once we locate at least one spec_lock.md
        self._source_manifest_cache: Dict[Path, Dict] = {}
        # Template-mode aggregation (populated by check_directory when
        # template_mode=True). Each entry is (severity, kind, message) where
        # severity is 'error' or 'warning'. Printed in print_summary.
        self._template_issues: List[Tuple[str, str, str]] = []
        self._animation_issues: List[Tuple[str, str]] = []

    def check_file(self, svg_file: str, expected_format: str = None) -> Dict:
        """
        Check a single SVG file

        Args:
            svg_file: SVG file path
            expected_format: Expected canvas format (e.g., 'ppt169')

        Returns:
            Check result dictionary
        """
        svg_path = Path(svg_file)

        if not svg_path.exists():
            return {
                'file': str(svg_file),
                'exists': False,
                'errors': ['File does not exist'],
                'warnings': [],
                'passed': False
            }

        result = {
            'file': svg_path.name,
            'path': str(svg_path),
            'exists': True,
            'errors': [],
            'warnings': [],
            'info': {},
            'passed': True
        }

        try:
            with open(svg_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 0. Check XML well-formedness — every other check assumes the file
            # is valid XML.  Bail early on failure so the regex-based checks
            # below don't produce misleading errors on a broken document.
            if self._check_xml_well_formed(content, result):
                # 1. Check viewBox
                self._check_viewbox(content, result, expected_format)

                # 2. Check forbidden elements
                self._check_forbidden_elements(content, result)

                # 3. Check fonts
                self._check_fonts(content, result)

                # 4. Check width/height consistency with viewBox
                self._check_dimensions(content, result)
                self._check_full_canvas_white_rect_order(content, result)

                # 5. Check text wrapping methods
                self._check_text_elements(content, result)
                self._check_text_layout_risk(content, result)
                self._check_visual_collision_risk(content, result)
                self._check_viettel_brand_layout(content, svg_path, result)

                # 6. Check image references (file existence and resolution)
                self._check_image_references(content, svg_path, result)

                # 7. Check object-level animation anchor quality.
                self._check_animation_group_ids(content, result)

                # 8. Check spec_lock drift (colors / font-family / font-size).
                #    Templates do not ship a spec_lock.md, so skip in template
                #    mode to avoid noise.
                if not self.template_mode:
                    self._check_spec_lock_drift(content, svg_path, result)

                # 9. Check web-sourced image attribution. Templates don't carry
                #    image_sources.json; skip in template mode.
                if not self.template_mode:
                    self._check_sourced_image_attribution(content, svg_path, result)

            # Determine pass/fail
            result['passed'] = len(result['errors']) == 0

        except Exception as e:
            result['errors'].append(f"Failed to read file: {e}")
            result['passed'] = False

        # Update statistics
        self.summary['total'] += 1
        if result['passed']:
            if result['warnings']:
                self.summary['warnings'] += 1
            else:
                self.summary['passed'] += 1
        else:
            self.summary['errors'] += 1

        # Categorize issue types
        for error in result['errors']:
            self.issue_types[self._categorize_issue(error)] += 1

        self.results.append(result)
        return result

    def _check_xml_well_formed(self, content: str, result: Dict) -> bool:
        """Check that the SVG content parses as well-formed XML.

        SVG is strict XML.  AI-generated decks frequently produce content that
        looks fine in HTML5-tolerant previews but fails strict XML parsing —
        common causes are HTML named entities (&nbsp; &mdash; &copy;…) and
        bare XML reserved characters in text (R&D, error < 5%).  Such pages
        cannot be exported to PPTX, so we surface them here as a hard error
        before any downstream check looks at them.

        Returns True when the document is well-formed; False otherwise.
        """
        try:
            ET.fromstring(content)
            return True
        except ET.ParseError as e:
            result['errors'].append(
                f"Invalid XML: {e} — SVG must be well-formed XML. "
                f"Use raw Unicode for typography (—, ©, →, NBSP); "
                f"escape XML reserved chars as &amp; &lt; &gt; &quot; &apos; "
                f"(see references/shared-standards.md §1)."
            )
            return False

    def _check_viewbox(self, content: str, result: Dict, expected_format: str = None):
        """Check viewBox attribute"""
        viewbox_match = re.search(r'viewBox="([^"]+)"', content)

        if not viewbox_match:
            result['errors'].append("Missing viewBox attribute")
            return

        viewbox = viewbox_match.group(1)
        result['info']['viewbox'] = viewbox

        # Check format
        if not re.match(r'0 0 \d+ \d+', viewbox):
            result['warnings'].append(f"Unusual viewBox format: {viewbox}")

        # Check if it matches expected format
        if expected_format and expected_format in CANVAS_FORMATS:
            expected_viewbox = CANVAS_FORMATS[expected_format]['viewbox']
            if viewbox != expected_viewbox:
                result['errors'].append(
                    f"viewBox mismatch: expected '{expected_viewbox}', got '{viewbox}'"
                )

    def _check_forbidden_elements(self, content: str, result: Dict):
        """Check forbidden elements (blocklist)"""
        content_lower = content.lower()

        # ============================================================
        # Forbidden elements blocklist - PPT incompatible
        # ============================================================

        # Clipping / masking
        # clipPath is allowed on <image> elements and on pptx_to_svg-generated
        # nested crop <svg data-pptx-crop="1"> wrappers. Both map back to
        # DrawingML picture geometry in the native converter.
        if '<clippath' in content_lower:
            # clip-path on non-image elements → error
            clip_on_non_image = re.search(
                r'<(?!image\b)(?!svg\b[^>]*\bdata-pptx-crop\s*=\s*["\']1["\'])\w+[^>]*\bclip-path\s*=',
                content,
                re.IGNORECASE,
            )
            if clip_on_non_image:
                result['errors'].append(
                    "clip-path is only allowed on <image> elements or "
                    "pptx_to_svg crop wrappers — for shapes, draw the target "
                    "shape directly instead of clipping")
            # Check that every clip-path reference has a matching <clipPath> def
            clip_refs = re.findall(r'clip-path\s*=\s*["\']url\(#([^)]+)\)', content)
            for ref_id in clip_refs:
                if f'id="{ref_id}"' not in content and f"id='{ref_id}'" not in content:
                    result['errors'].append(
                        f"clip-path references #{ref_id} but no matching "
                        f"<clipPath id=\"{ref_id}\"> definition found")
        if '<mask' in content_lower:
            result['errors'].append("Detected forbidden <mask> element (PPT does not support SVG masks)")

        # Style system
        if '<style' in content_lower:
            result['errors'].append("Detected forbidden <style> element (use inline attributes instead)")
        if re.search(r'\bclass\s*=', content):
            result['errors'].append("Detected forbidden class attribute (use inline styles instead)")
        # id attribute: only report error when <style> also exists (id is harmful only with CSS selectors)
        # id inside <defs> for linearGradient/filter etc. is required, Inkscape also auto-adds id to elements,
        # standalone id attributes have no impact on PPT export
        if '<style' in content_lower and re.search(r'\bid\s*=', content):
            result['errors'].append(
                "Detected id attribute used with <style> (CSS selectors forbidden, use inline styles instead)"
            )
        if re.search(r'<\?xml-stylesheet\b', content_lower):
            result['errors'].append("Detected forbidden xml-stylesheet (external CSS references forbidden)")
        if re.search(r'<link[^>]*rel\s*=\s*["\']stylesheet["\']', content_lower):
            result['errors'].append("Detected forbidden <link rel=\"stylesheet\"> (external CSS references forbidden)")
        if re.search(r'@import\s+', content_lower):
            result['errors'].append("Detected forbidden @import (external CSS references forbidden)")

        # Structure / nesting
        if '<foreignobject' in content_lower:
            result['errors'].append(
                "Detected forbidden <foreignObject> element (use separate <text> lines or data-box/data-wrap)")
        has_symbol = '<symbol' in content_lower
        has_use = re.search(r'<use\b', content_lower) is not None
        if has_symbol and has_use:
            result['errors'].append("Detected forbidden <symbol> + <use> complex usage (use basic shapes or simple <use> instead)")
        # marker-start / marker-end are conditionally allowed (see shared-standards.md §1.1).
        # The converter maps qualifying <marker> defs to native DrawingML <a:headEnd>/<a:tailEnd>.
        # We only warn when a marker is used without an obvious <defs> definition in the same file.
        if re.search(r'\bmarker-(?:start|end)\s*=\s*["\']url\(#([^)]+)\)', content_lower):
            if '<marker' not in content_lower:
                result['errors'].append(
                    "Detected marker-start/marker-end referencing a marker id, "
                    "but no <marker> element found in the file")

        # Text / fonts
        if '<textpath' in content_lower:
            result['errors'].append("Detected forbidden <textPath> element (path text is incompatible with PPT)")
        if '@font-face' in content_lower:
            result['errors'].append("Detected forbidden @font-face (use system font stack)")

        # Animation / interaction
        if re.search(r'<animate', content_lower):
            result['errors'].append("Detected forbidden SMIL animation element <animate*> (SVG animations are not exported)")
        if re.search(r'<set\b', content_lower):
            result['errors'].append("Detected forbidden SMIL animation element <set> (SVG animations are not exported)")
        if '<script' in content_lower:
            result['errors'].append("Detected forbidden <script> element (scripts and event handlers forbidden)")
        if re.search(r'\bon\w+\s*=', content):  # onclick, onload etc.
            result['errors'].append("Detected forbidden event attributes (e.g., onclick, onload)")

        # Other discouraged elements
        if '<iframe' in content_lower:
            result['errors'].append("Detected <iframe> element (should not appear in SVG)")
        if re.search(r'rgba\s*\(', content_lower):
            result['errors'].append("Detected forbidden rgba() color (use fill-opacity/stroke-opacity instead)")
        if re.search(r'<g[^>]*\sopacity\s*=', content_lower):
            result['errors'].append("Detected forbidden <g opacity> (set opacity on each child element individually)")
        if re.search(r'<image[^>]*\sopacity\s*=', content_lower):
            result['errors'].append("Detected forbidden <image opacity> (use overlay mask approach)")

    def _check_fonts(self, content: str, result: Dict):
        """Check font usage.

        PPTX stores a single `typeface` per run with no runtime fallback, so every
        stack must END with a cross-platform pre-installed family. See
        strategist.md §g "PPT-safe font discipline".
        """
        font_matches = re.findall(
            r'font-family[:\s]*["\']([^"\']+)["\']', content, re.IGNORECASE)

        if not font_matches:
            return

        result['info']['fonts'] = list(set(font_matches))

        # Pre-installed on Windows + macOS out of the box (plus their direct
        # FONT_FALLBACK_WIN mappings). A stack whose last concrete family is in
        # this set survives the PPTX round-trip on any viewer machine.
        ppt_safe_tail = {
            'microsoft yahei', 'simhei', 'simsun', 'kaiti', 'fangsong',
            'pingfang sc', 'heiti sc', 'songti sc', 'stsong',
            'arial', 'arial black', 'calibri', 'segoe ui', 'verdana',
            'helvetica', 'helvetica neue', 'tahoma', 'trebuchet ms',
            'times new roman', 'times', 'georgia', 'cambria', 'palatino',
            'consolas', 'courier new', 'menlo', 'monaco',
            'impact',
        }

        for font_family in font_matches:
            font_family = html.unescape(font_family)
            brand_locked_viettel = 'fs magistral' in font_family.lower()
            # Drop the generic CSS fallback (sans-serif / serif / monospace)
            # and inspect the last concrete family.
            parts = [p.strip().strip('"').strip("'").lower()
                     for p in font_family.split(',')]
            parts = [p for p in parts
                     if p and p not in ('sans-serif', 'serif', 'monospace',
                                        'cursive', 'fantasy', 'system-ui')]
            if not parts:
                continue
            tail = parts[-1]
            if tail not in ppt_safe_tail:
                if brand_locked_viettel and tail == 'fs magistral':
                    continue
                result['warnings'].append(
                    f"Font stack does not end on a PPT-safe family "
                    f"(expected e.g. Microsoft YaHei / SimSun / Arial / "
                    f"Times New Roman / Consolas): {font_family}"
                )
                break

    def _check_dimensions(self, content: str, result: Dict):
        """Check width/height consistency with viewBox"""
        width_match = re.search(r'width="(\d+)"', content)
        height_match = re.search(r'height="(\d+)"', content)

        if width_match and height_match:
            width = width_match.group(1)
            height = height_match.group(1)
            result['info']['dimensions'] = f"{width}x{height}"

            # Check consistency with viewBox
            if 'viewbox' in result['info']:
                viewbox_parts = result['info']['viewbox'].split()
                if len(viewbox_parts) == 4:
                    vb_width, vb_height = viewbox_parts[2], viewbox_parts[3]
                    if width != vb_width or height != vb_height:
                        result['warnings'].append(
                            f"width/height ({width}x{height}) does not match viewBox "
                            f"({vb_width}x{vb_height})"
                        )

    def _check_full_canvas_white_rect_order(self, content: str, result: Dict):
        """Catch late full-slide white rectangles that erase backgrounds.

        Viettel layout and background reference SVGs are allowed to contain a
        white base rectangle for standalone preview. In generated pages,
        however, that base must be a single first visible primitive. A second
        or late full-canvas opaque white rect usually means the Executor pasted
        a template/background body after the decorative background layer, which
        leaves slide content visible but blanks the custom background.
        """
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            return

        canvas = self._canvas_size_from_svg(root)
        if not canvas:
            return
        canvas_w, canvas_h = canvas

        visible_index = 0
        white_rect_positions: List[int] = []

        def visit(elem: ET.Element):
            nonlocal visible_index
            tag = _local_name(elem.tag)
            if tag in NON_RENDER_TAGS:
                return

            if tag in VISIBLE_PRIMITIVE_TAGS:
                if tag != "g":
                    visible_index += 1
                    if self._is_opaque_full_canvas_white_rect(elem, canvas_w, canvas_h):
                        white_rect_positions.append(visible_index)

            for child in list(elem):
                visit(child)

        for child in list(root):
            visit(child)

        if not white_rect_positions:
            return
        if len(white_rect_positions) > 1:
            result['errors'].append(
                "Full-canvas white rectangle layering violation: found "
                f"{len(white_rect_positions)} opaque white page-size rects "
                f"({canvas_w:g}x{canvas_h:g}) "
                f"at visible positions {white_rect_positions}. Keep exactly one "
                "page base rect, and it must be the first visible shape before "
                "any decorative background/content."
            )
        elif white_rect_positions[0] != 1:
            result['errors'].append(
                "Full-canvas white rectangle layering violation: the opaque "
                f"page-size white rect is at visible position {white_rect_positions[0]}, "
                "not first. Move the page base rect before background layers, "
                "or omit the copied template/background white base rect."
            )

    def _canvas_size_from_svg(self, root: ET.Element) -> tuple[float, float] | None:
        viewbox = (root.get('viewBox') or '').strip()
        parts = [p for p in re.split(r'[\s,]+', viewbox) if p]
        if len(parts) == 4:
            try:
                return float(parts[2]), float(parts[3])
            except ValueError:
                pass

        width = (root.get('width') or '').removesuffix('px')
        height = (root.get('height') or '').removesuffix('px')
        try:
            return float(width), float(height)
        except ValueError:
            return None

    def _is_opaque_full_canvas_white_rect(
        self,
        elem: ET.Element,
        canvas_w: float,
        canvas_h: float,
    ) -> bool:
        if _local_name(elem.tag) != "rect":
            return False
        fill = (_get_svg_attr(elem, "fill") or "").strip().upper().replace(" ", "")
        if fill not in WHITE_FILLS:
            return False
        if self._opacity_value(elem, "opacity") < 0.999:
            return False
        if self._opacity_value(elem, "fill-opacity") < 0.999:
            return False

        x = _float_attr(elem, "x", 0.0)
        y = _float_attr(elem, "y", 0.0)
        w = _float_attr(elem, "width", 0.0)
        h = _float_attr(elem, "height", 0.0)
        return (
            abs(x) <= 0.01 and
            abs(y) <= 0.01 and
            abs(w - canvas_w) <= 0.01 and
            abs(h - canvas_h) <= 0.01
        )

    def _opacity_value(self, elem: ET.Element, name: str) -> float:
        raw = _get_svg_attr(elem, name, "1").strip()
        try:
            return float(raw)
        except ValueError:
            return 1.0

    def _check_text_elements(self, content: str, result: Dict):
        """Check text elements and wrapping methods"""
        # Count text and tspan elements
        text_count = content.count('<text')
        tspan_count = content.count('<tspan')

        result['info']['text_elements'] = text_count
        result['info']['tspan_elements'] = tspan_count

        # Check for overly long single-line text (may need wrapping)
        text_matches = re.findall(r'<text[^>]*>([^<]{100,})</text>', content)
        if text_matches:
            result['warnings'].append(
                f"Detected {len(text_matches)} potentially overly long single-line text(s) (use separate <text> lines or data-box/data-wrap)"
            )

    def _check_text_layout_risk(self, content: str, result: Dict):
        """Detect text that is likely to render outside its intended layout box.

        This is intentionally conservative and visual-output oriented. SVG text
        has no intrinsic width, and the native PPTX converter used to emit all
        text as wrap="none"; a page can pass XML checks while PowerPoint renders
        labels outside cards. We estimate text bounds, locate the nearest card /
        panel rectangle that contains the text anchor, and fail when the text
        exceeds that container by a meaningful amount.
        """
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            return

        containers: List[Dict] = []
        texts: List[Dict] = []
        shapes: List[Dict] = []

        def visit(elem: ET.Element, tx: float = 0.0, ty: float = 0.0):
            dx, dy = _parse_translate(elem.get('transform', ''))
            tx += dx
            ty += dy

            tag = _local_name(elem.tag)
            if tag == 'rect':
                x = _float_attr(elem, 'x') + tx
                y = _float_attr(elem, 'y') + ty
                w = _float_attr(elem, 'width')
                h = _float_attr(elem, 'height')
                fill = (_get_svg_attr(elem, 'fill') or '').upper()
                stroke = (_get_svg_attr(elem, 'stroke') or '').upper()
                rx = _float_attr(elem, 'rx', _float_attr(elem, 'ry', 0.0))
                rect = {
                    'x': x, 'y': y, 'w': w, 'h': h,
                    'x2': x + w, 'y2': y + h,
                    'fill': fill, 'stroke': stroke, 'rx': rx,
                    'allow_title_zone': elem.get('data-allow-title-zone') == 'true',
                }
                # Containers are real cards / panels, not bars or decorative
                # strips. Width threshold avoids mistaking chart bars for cards.
                if (
                    w >= 150 and h >= 35 and
                    not (w >= 1200 and h >= 650) and
                    (
                        stroke not in ('', 'NONE') or
                        fill in ('#F2F2F2', '#FFFFFF', '#12436D', '#EE0033') or
                        rx >= 6
                    )
                ):
                    containers.append(rect)
                if w > 0 and h > 0:
                    shapes.append(rect)

            elif tag in ('circle', 'ellipse'):
                cx = _float_attr(elem, 'cx') + tx
                cy = _float_attr(elem, 'cy') + ty
                rx = _float_attr(elem, 'r', _float_attr(elem, 'rx', 0.0))
                ry = _float_attr(elem, 'r', _float_attr(elem, 'ry', 0.0))
                shapes.append({
                    'x': cx - rx, 'y': cy - ry, 'w': rx * 2, 'h': ry * 2,
                    'x2': cx + rx, 'y2': cy + ry,
                    'fill': (_get_svg_attr(elem, 'fill') or '').upper(),
                    'stroke': (_get_svg_attr(elem, 'stroke') or '').upper(),
                    'rx': 0,
                })

            elif tag == 'text':
                if elem.get('data-allow-overflow') == 'true':
                    return
                text = ''.join(elem.itertext()).strip()
                if text:
                    x = _float_attr(elem, 'x') + tx
                    y = _float_attr(elem, 'y') + ty
                    fs = _float_attr(elem, 'font-size', 16)
                    fw = _get_svg_attr(elem, 'font-weight', '400')
                    anchor = _get_svg_attr(elem, 'text-anchor', 'start')
                    estimated_w = _estimate_svg_text_width(text, fs, fw) * 1.12
                    tspan_count = sum(
                        1 for child in elem.iter()
                        if child is not elem and _local_name(child.tag) == 'tspan'
                    )
                    line_count = max(1, tspan_count)
                    estimated_h = fs * 1.35 * line_count

                    if anchor == 'middle':
                        box_x = x - estimated_w / 2
                    elif anchor == 'end':
                        box_x = x - estimated_w
                    else:
                        box_x = x
                    box_y = y - fs * 0.85

                    data_box = elem.get('data-box')
                    if data_box:
                        parts = [p.strip() for p in re.split(r'[\s,]+', data_box) if p.strip()]
                        if len(parts) == 4:
                            try:
                                bx, by, bw, bh = [float(p) for p in parts]
                                box_x, box_y, estimated_w, estimated_h = bx + tx, by + ty, bw, bh
                            except ValueError:
                                pass

                    texts.append({
                        'text': text,
                        'x': x, 'y': y,
                        'x1': box_x, 'y1': box_y,
                        'x2': box_x + estimated_w,
                        'y2': box_y + estimated_h,
                        'font_size': fs,
                        'has_wrap_contract': bool(
                            data_box or elem.get('data-wrap') == 'true'
                        ),
                    })

            for child in list(elem):
                visit(child, tx, ty)

        visit(root)

        content_right = 1208
        content_bottom = 640
        overflow_count = 0
        unbounded_long_count = 0

        for text in texts:
            # Text outside the slide content safe area is usually accidental
            # unless it is a footer/header label.
            if 120 < text['y'] < content_bottom and text['x2'] > content_right + 8:
                overflow_count += 1

            container = self._find_text_container(text, containers)
            if container:
                pad = max(6.0, text['font_size'] * 0.35)
                if (
                    text['x1'] < container['x'] + pad - 10 or
                    text['x2'] > container['x2'] - pad + 10 or
                    text['y1'] < container['y'] + pad - 10 or
                    text['y2'] > container['y2'] - pad + 10
                ):
                    overflow_count += 1
            else:
                if len(text['text']) >= 80 and not text['has_wrap_contract'] and text['font_size'] >= 12:
                    unbounded_long_count += 1

        title_intrusions = self._count_title_zone_intrusions(shapes)

        if overflow_count:
            result['errors'].append(
                f"Detected {overflow_count} text layout overflow risk(s): text extends outside its card/panel or safe area. "
                f"Use separate <text> lines or data-box=\"x,y,w,h\" data-wrap=\"true\"."
            )
        if unbounded_long_count:
            result['warnings'].append(
                f"Detected {unbounded_long_count} long text line(s) without a wrap contract. "
                f"Use separate <text> lines or data-box/data-wrap so PPTX export cannot render past the intended block."
            )
        if title_intrusions:
            result['errors'].append(
                f"Detected {title_intrusions} content shape(s) intruding into the title/header zone. "
                f"Keep chart marks and content cards below the title divider or reduce chart scale."
            )

    def _check_visual_collision_risk(self, content: str, result: Dict):
        """Detect visual risks that are visible only after SVG paint ordering.

        The checker intentionally stays conservative: text/text collisions and
        later opaque shapes covering text are errors; low contrast is reported
        as a warning so existing decks can triage it without weakening hard
        Viettel brand gates.
        """
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            return

        texts, shapes = self._collect_visual_objects(root)
        text_overlap_count = self._count_text_overlaps(texts)
        cover_count = self._count_later_shape_text_covers(texts, shapes)
        low_contrast = self._find_low_contrast_texts(texts, shapes)

        if text_overlap_count:
            result['errors'].append(
                f"Detected {text_overlap_count} text overlap/collision risk(s): "
                "estimated text boxes intersect. Move labels apart, reduce copy, "
                "or add data-allow-overlap=\"true\" only for intentional overlaps."
            )
        if cover_count:
            result['errors'].append(
                f"Detected {cover_count} layer-cover risk(s): a later opaque shape/image "
                "appears to cover text. Move the shape behind the text or mark the "
                "intentional overlay with data-allow-cover-text=\"true\"."
            )
        if low_contrast:
            examples = ", ".join(
                f"{item['text']} ({item['ratio']:.2f}:1)" for item in low_contrast[:3]
            )
            suffix = "" if len(low_contrast) <= 3 else f", +{len(low_contrast) - 3} more"
            result['warnings'].append(
                f"Detected {len(low_contrast)} low-contrast text risk(s): {examples}{suffix}. "
                "Use a darker/lighter approved color or adjust the background."
            )

    def _collect_visual_objects(self, root: ET.Element) -> tuple[List[Dict], List[Dict]]:
        texts: List[Dict] = []
        shapes: List[Dict] = []
        order = 0
        paint_colors = self._extract_paint_colors(root)

        def visible(elem: ET.Element) -> bool:
            display = _get_svg_attr(elem, 'display', '').strip().lower()
            visibility = _get_svg_attr(elem, 'visibility', '').strip().lower()
            return display != 'none' and visibility != 'hidden'

        def visit(
            elem: ET.Element,
            tx: float = 0.0,
            ty: float = 0.0,
            inherited_fill: str = '#000000',
            inherited_font_size: float = 16.0,
            inherited_font_weight: str = '400',
            inherited_opacity: float = 1.0,
        ) -> None:
            nonlocal order

            tag = _local_name(elem.tag)
            if tag in NON_RENDER_TAGS or not visible(elem):
                return

            dx, dy = _parse_translate(elem.get('transform', ''))
            tx += dx
            ty += dy

            fill_raw = _get_svg_attr(elem, 'fill', inherited_fill)
            fill = fill_raw if fill_raw else inherited_fill
            font_size = _float_attr(elem, 'font-size', inherited_font_size)
            font_weight = _get_svg_attr(elem, 'font-weight', inherited_font_weight)
            opacity = inherited_opacity * self._opacity_value(elem, 'opacity')
            fill_opacity = opacity * self._opacity_value(elem, 'fill-opacity')

            if tag in VISIBLE_PRIMITIVE_TAGS:
                order += 1

            if tag == 'text':
                text = ''.join(elem.itertext()).strip()
                color = self._resolve_paint_color(fill, paint_colors) or '#000000'
                if text and fill_opacity > 0.01:
                    bounds = self._text_bounds_for_element(
                        elem,
                        text,
                        tx,
                        ty,
                        font_size,
                        font_weight,
                    )
                    if bounds:
                        bounds.update({
                            'order': order,
                            'text': text,
                            'fill': color,
                            'font_size': font_size,
                            'font_weight': font_weight,
                            'opacity': fill_opacity,
                            'allow_overlap': elem.get('data-allow-overlap') == 'true',
                            'allow_low_contrast': elem.get('data-allow-low-contrast') == 'true',
                            'allow_cover_text': elem.get('data-allow-cover-text') == 'true',
                        })
                        texts.append(bounds)
            else:
                shape = self._shape_bounds_for_element(elem, tag, tx, ty)
                if shape:
                    fill_color = self._resolve_paint_color(fill, paint_colors)
                    shape.update({
                        'order': order,
                        'tag': tag,
                        'fill': fill_color,
                        'opacity': fill_opacity,
                        'allow_cover_text': elem.get('data-allow-cover-text') == 'true',
                    })
                    shapes.append(shape)

            for child in list(elem):
                visit(child, tx, ty, fill, font_size, font_weight, opacity)

        visit(root)
        return texts, shapes

    def _extract_paint_colors(self, root: ET.Element) -> Dict[str, str]:
        """Resolve simple gradient ids to an average HEX color."""
        colors: Dict[str, str] = {}
        for elem in root.iter():
            tag = _local_name(elem.tag)
            if tag not in {'linearGradient', 'radialGradient'}:
                continue
            gradient_id = elem.get('id')
            if not gradient_id:
                continue
            stops = []
            for child in list(elem):
                if _local_name(child.tag) != 'stop':
                    continue
                color = _normalize_hex_color(_get_svg_attr(child, 'stop-color', ''))
                if color:
                    stops.append(color)
            if stops:
                colors[gradient_id] = self._average_hex(stops)
        return colors

    def _resolve_paint_color(self, value: str | None, paint_colors: Dict[str, str]) -> str | None:
        direct = _normalize_hex_color(value)
        if direct:
            return direct
        if not value:
            return None
        match = re.fullmatch(r'url\(#([^)]+)\)', value.strip())
        if not match:
            return None
        return paint_colors.get(match.group(1))

    @staticmethod
    def _average_hex(colors: List[str]) -> str:
        channels = []
        for color in colors:
            channels.append((
                int(color[1:3], 16),
                int(color[3:5], 16),
                int(color[5:7], 16),
            ))
        count = len(channels)
        r = round(sum(item[0] for item in channels) / count)
        g = round(sum(item[1] for item in channels) / count)
        b = round(sum(item[2] for item in channels) / count)
        return f"#{r:02X}{g:02X}{b:02X}"

    def _text_bounds_for_element(
        self,
        elem: ET.Element,
        text: str,
        tx: float,
        ty: float,
        font_size: float,
        font_weight: str,
    ) -> Dict | None:
        x = _float_attr(elem, 'x') + tx
        y = _float_attr(elem, 'y') + ty
        anchor = _get_svg_attr(elem, 'text-anchor', 'start')
        estimated_w = _estimate_svg_text_width(text, font_size, font_weight) * 1.12
        tspan_count = sum(
            1 for child in elem.iter()
            if child is not elem and _local_name(child.tag) == 'tspan'
        )
        estimated_h = font_size * 1.35 * max(1, tspan_count)

        if anchor == 'middle':
            box_x = x - estimated_w / 2
        elif anchor == 'end':
            box_x = x - estimated_w
        else:
            box_x = x
        box_y = y - font_size * 0.85

        data_box = elem.get('data-box')
        if data_box:
            parts = [p.strip() for p in re.split(r'[\s,]+', data_box) if p.strip()]
            if len(parts) == 4:
                try:
                    bx, by, bw, bh = [float(p) for p in parts]
                    box_x, box_y, estimated_w, estimated_h = bx + tx, by + ty, bw, bh
                except ValueError:
                    pass

        if estimated_w <= 0 or estimated_h <= 0:
            return None
        return {
            'x': x,
            'y': y,
            'x1': box_x,
            'y1': box_y,
            'x2': box_x + estimated_w,
            'y2': box_y + estimated_h,
        }

    def _shape_bounds_for_element(
        self,
        elem: ET.Element,
        tag: str,
        tx: float,
        ty: float,
    ) -> Dict | None:
        if tag == 'rect':
            x = _float_attr(elem, 'x') + tx
            y = _float_attr(elem, 'y') + ty
            w = _float_attr(elem, 'width')
            h = _float_attr(elem, 'height')
        elif tag == 'circle':
            cx = _float_attr(elem, 'cx') + tx
            cy = _float_attr(elem, 'cy') + ty
            r = _float_attr(elem, 'r')
            x, y, w, h = cx - r, cy - r, r * 2, r * 2
        elif tag == 'ellipse':
            cx = _float_attr(elem, 'cx') + tx
            cy = _float_attr(elem, 'cy') + ty
            rx = _float_attr(elem, 'rx')
            ry = _float_attr(elem, 'ry')
            x, y, w, h = cx - rx, cy - ry, rx * 2, ry * 2
        elif tag == 'image':
            x = _float_attr(elem, 'x') + tx
            y = _float_attr(elem, 'y') + ty
            w = _float_attr(elem, 'width')
            h = _float_attr(elem, 'height')
        elif tag in {'polygon', 'polyline'}:
            bounds = self._points_bounds(elem.get('points', ''), tx, ty)
            if bounds is None:
                return None
            x, y, w, h = bounds
        else:
            return None

        if w <= 0 or h <= 0:
            return None
        return {
            'x': x,
            'y': y,
            'w': w,
            'h': h,
            'x1': x,
            'y1': y,
            'x2': x + w,
            'y2': y + h,
        }

    def _points_bounds(self, raw_points: str, tx: float, ty: float) -> tuple[float, float, float, float] | None:
        nums = []
        for token in re.split(r'[\s,]+', raw_points.strip()):
            if not token:
                continue
            try:
                nums.append(float(token))
            except ValueError:
                return None
        if len(nums) < 4 or len(nums) % 2 != 0:
            return None
        xs = [nums[i] + tx for i in range(0, len(nums), 2)]
        ys = [nums[i] + ty for i in range(1, len(nums), 2)]
        x1, x2 = min(xs), max(xs)
        y1, y2 = min(ys), max(ys)
        return x1, y1, x2 - x1, y2 - y1

    def _count_text_overlaps(self, texts: List[Dict]) -> int:
        count = 0
        for i, first in enumerate(texts):
            if first.get('allow_overlap'):
                continue
            for second in texts[i + 1:]:
                if second.get('allow_overlap'):
                    continue
                if self._is_bottom_right_page_number(first) and self._is_bottom_right_page_number(second):
                    continue
                metrics = self._intersection_metrics(first, second)
                if not metrics:
                    continue
                min_w = max(1.0, min(first['x2'] - first['x1'], second['x2'] - second['x1']))
                min_h = max(1.0, min(first['y2'] - first['y1'], second['y2'] - second['y1']))
                if metrics['w'] >= min(24.0, min_w * 0.25) and metrics['h'] >= min(10.0, min_h * 0.35):
                    count += 1
        return count

    def _count_later_shape_text_covers(self, texts: List[Dict], shapes: List[Dict]) -> int:
        count = 0
        for text in texts:
            if text.get('allow_cover_text'):
                continue
            text_area = max(1.0, (text['x2'] - text['x1']) * (text['y2'] - text['y1']))
            for shape in shapes:
                if shape['order'] <= text['order'] or shape.get('allow_cover_text'):
                    continue
                if shape['tag'] != 'image' and not shape.get('fill'):
                    continue
                if shape.get('opacity', 1.0) < 0.75:
                    continue
                metrics = self._intersection_metrics(text, shape)
                if not metrics:
                    continue
                text_h = max(1.0, text['y2'] - text['y1'])
                if metrics['area'] / text_area >= 0.25 and metrics['h'] >= min(14.0, text_h * 0.45):
                    count += 1
                    break
        return count

    def _find_low_contrast_texts(self, texts: List[Dict], shapes: List[Dict]) -> List[Dict]:
        risks: List[Dict] = []
        for text in texts:
            if text.get('allow_low_contrast') or self._is_bottom_right_page_number(text):
                continue
            if text.get('font_size', 16.0) <= 12:
                continue
            fg = text.get('fill')
            if not fg:
                continue
            bg = self._background_fill_for_text(text, shapes) or '#FFFFFF'
            ratio = _contrast_ratio(fg, bg)
            if ratio < 3.0:
                risks.append({
                    'text': self._short_text(text.get('text', '')),
                    'ratio': ratio,
                })
        return risks

    def _background_fill_for_text(self, text: Dict, shapes: List[Dict]) -> str | None:
        cx = (text['x1'] + text['x2']) / 2
        cy = (text['y1'] + text['y2']) / 2
        candidates = []
        for shape in shapes:
            if shape['order'] >= text['order']:
                continue
            fill = shape.get('fill')
            if not fill or shape.get('opacity', 1.0) < 0.25:
                continue
            if shape['x1'] <= cx <= shape['x2'] and shape['y1'] <= cy <= shape['y2']:
                candidates.append(shape)
        if not candidates:
            return None
        candidates.sort(key=lambda item: item['order'], reverse=True)
        return candidates[0].get('fill')

    def _intersection_metrics(self, a: Dict, b: Dict) -> Dict | None:
        x1 = max(a['x1'], b['x1'])
        y1 = max(a['y1'], b['y1'])
        x2 = min(a['x2'], b['x2'])
        y2 = min(a['y2'], b['y2'])
        if x2 <= x1 or y2 <= y1:
            return None
        return {'w': x2 - x1, 'h': y2 - y1, 'area': (x2 - x1) * (y2 - y1)}

    @staticmethod
    def _short_text(text: str) -> str:
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) <= 36:
            return text
        return text[:33].rstrip() + "..."

    def _find_text_container(self, text: Dict, containers: List[Dict]) -> Dict | None:
        """Return the smallest container containing a text anchor point."""
        matches = []
        for rect in containers:
            if rect['x'] <= text['x'] <= rect['x2'] and rect['y'] <= text['y'] <= rect['y2']:
                area = rect['w'] * rect['h']
                matches.append((area, rect))
        if not matches:
            return None
        matches.sort(key=lambda item: item[0])
        return matches[0][1]

    def _count_title_zone_intrusions(self, shapes: List[Dict]) -> int:
        """Count non-background shapes that enter the reserved title area."""
        count = 0
        neutral_fills = {'', 'NONE', '#FFFFFF', '#F2F2F2', '#E6E6E6'}
        title_zone_bottom = 225.0
        for shape in shapes:
            if (
                shape['w'] >= 600 and shape['h'] <= 6 and
                180 <= shape['y'] <= 280 and
                shape.get('fill', '') in neutral_fills
            ):
                title_zone_bottom = max(title_zone_bottom, shape['y'])
        for shape in shapes:
            fill = shape.get('fill', '')
            if shape.get('allow_title_zone'):
                continue
            # Ignore rails, full-slide backgrounds, top accent bars, logo pills,
            # and subtle divider/background surfaces.
            if shape['x'] < 40 or shape['w'] >= 1100 or shape['h'] <= 12:
                continue
            if fill in neutral_fills:
                continue
            if shape['y'] < title_zone_bottom and shape['y2'] > 115 and shape['w'] >= 60 and shape['h'] >= 28:
                count += 1
        return count

    def _check_viettel_brand_layout(self, content: str, svg_path: Path, result: Dict):
        """Enforce Viettel brand invariants that generic SVG checks miss."""
        if self._get_brand_profile(svg_path, content) != VIETTEL_BRAND_PROFILE:
            return
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            return

        viewbox = (root.get('viewBox') or '').strip()
        if viewbox != VIETTEL_VIEWBOX:
            result['errors'].append(
                f"Viettel canvas violation: expected viewBox '{VIETTEL_VIEWBOX}', got '{viewbox or 'missing'}'"
            )

        width = (root.get('width') or '').removesuffix('px')
        height = (root.get('height') or '').removesuffix('px')
        if width != '1280' or height != '720':
            result['errors'].append(
                f"Viettel canvas violation: expected width/height 1280x720, got {width or 'missing'}x{height or 'missing'}"
            )

        has_logo = any(
            _local_name(elem.tag) == 'image' and
            'viettel-logo.png' in (
                elem.get('href') or
                elem.get('{http://www.w3.org/1999/xlink}href') or
                ''
            ).lower()
            for elem in root.iter()
        )
        if not has_logo:
            result['errors'].append(
                "Viettel brand violation: missing viettel-logo.png on the page"
            )

        logo_box = {'x1': 1060.0, 'y1': 20.0, 'x2': 1224.0, 'y2': 82.0}
        logo_text_overlaps = 0
        bottom_page_numbers = 0

        for text in self._iter_text_bounds(root):
            if self._boxes_intersect(text, logo_box):
                logo_text_overlaps += 1
            if self._is_bottom_right_page_number(text):
                bottom_page_numbers += 1

        if logo_text_overlaps:
            result['errors'].append(
                f"Viettel logo clearance violation: {logo_text_overlaps} header text box(es) overlap "
                "the reserved top-right logo slot (x=1060-1224, y=20-82). "
                "Wrap titles inside data-box=\"88,36,960,58\" data-wrap=\"true\" or shorten/manual-break the title."
            )
        if bottom_page_numbers > 1:
            result['errors'].append(
                f"Viettel page number duplication: detected {bottom_page_numbers} bottom-right page-number text elements. "
                "Keep exactly one shell/footer page number; do not add another in brand chrome or page content."
            )
        if 'cover' not in svg_path.stem.lower() and bottom_page_numbers == 0:
            result['errors'].append(
                "Viettel brand violation: missing bottom-right page number on a non-cover page"
            )

        self._check_viettel_fonts_and_colors(root, result)

    def _get_brand_profile(self, svg_path: Path, content: str) -> str | None:
        """Resolve explicit project brand profile, then fall back for templates."""
        lock = self._get_spec_lock(svg_path)
        if lock:
            profile = lock.get('brand', {}).get('profile', '').strip()
            if profile in {VIETTEL_BRAND_PROFILE, VIETTEL_CUSTOM_OVERRIDE_PROFILE}:
                return profile
        if self._looks_like_viettel_svg(content):
            return VIETTEL_BRAND_PROFILE
        return None

    def _check_viettel_fonts_and_colors(self, root: ET.Element, result: Dict) -> None:
        """Validate the locked Viettel font stack, palette, and blue scopes."""
        invalid_fonts = 0
        missing_fonts = 0
        invalid_weights: set[str] = set()
        invalid_colors: set[str] = set()
        blue_text = 0
        unscoped_blue = 0

        def visit(
            elem: ET.Element,
            inherited_font: str = '',
            inherited_weight: str = '',
            blue_scope: str = '',
        ) -> None:
            nonlocal invalid_fonts, missing_fonts, blue_text, unscoped_blue

            scope = (elem.get('data-viettel-blue-scope') or blue_scope).strip().lower()
            font = html.unescape(_get_svg_attr(elem, 'font-family', inherited_font)).strip()
            weight = _get_svg_attr(elem, 'font-weight', inherited_weight).strip().lower()
            tag = _local_name(elem.tag)
            is_text = tag in {'text', 'tspan'}
            if is_text:
                if not font:
                    missing_fonts += 1
                elif font != VIETTEL_FONT_STACK:
                    invalid_fonts += 1
                if weight not in VIETTEL_ALLOWED_FONT_WEIGHTS:
                    invalid_weights.add(weight)

            for attr in ('fill', 'stroke', 'stop-color'):
                value = _get_svg_attr(elem, attr).strip().upper()
                if not HEX_VALUE_RE.fullmatch(value):
                    continue
                if value not in VIETTEL_ALLOWED_COLORS:
                    invalid_colors.add(value)
                if value == VIETTEL_DEEP_BLUE:
                    if is_text:
                        blue_text += 1
                    elif scope not in VIETTEL_BLUE_SCOPES:
                        unscoped_blue += 1

            for child in list(elem):
                visit(child, font, weight, scope)

        visit(root)

        if missing_fonts or invalid_fonts:
            parts = []
            if missing_fonts:
                parts.append(f"{missing_fonts} text element(s) without an effective font-family")
            if invalid_fonts:
                parts.append(f"{invalid_fonts} text element(s) outside the exact locked stack")
            result['errors'].append(
                "Viettel typography violation: " + ", ".join(parts) +
                f"; required stack is {VIETTEL_FONT_STACK}"
            )
        if invalid_weights:
            result['errors'].append(
                "Viettel typography violation: forbidden font-weight value(s) " +
                ", ".join(sorted(invalid_weights)) +
                "; allowed weights are 400 Book/Regular, 500 Medium, and 700 Bold"
            )
        if invalid_colors:
            result['errors'].append(
                "Viettel palette violation: color(s) outside the approved palette: " +
                ", ".join(sorted(invalid_colors))
            )
        if blue_text:
            result['errors'].append(
                f"Viettel deep-blue violation: {blue_text} text element(s) use {VIETTEL_DEEP_BLUE}; "
                "deep blue is never a text color"
            )
        if unscoped_blue:
            result['errors'].append(
                f"Viettel deep-blue violation: {unscoped_blue} mark(s) use {VIETTEL_DEEP_BLUE} outside "
                'data-viettel-blue-scope="chart|diagram|icon"'
            )

    def _looks_like_viettel_svg(self, content: str) -> bool:
        lower = content.lower()
        return (
            'viettel-logo.png' in lower or
            'viettel-brand-chrome' in lower or
            'fs pf beausans pro' in lower or
            'fs magistral' in lower
        )

    def _iter_text_bounds(self, root: ET.Element) -> List[Dict]:
        texts: List[Dict] = []

        def visit(elem: ET.Element, tx: float = 0.0, ty: float = 0.0):
            dx, dy = _parse_translate(elem.get('transform', ''))
            tx += dx
            ty += dy

            if _local_name(elem.tag) == 'text':
                if elem.get('data-allow-overflow') == 'true':
                    return
                text = ''.join(elem.itertext()).strip()
                if text:
                    x = _float_attr(elem, 'x') + tx
                    y = _float_attr(elem, 'y') + ty
                    fs = _float_attr(elem, 'font-size', 16)
                    fw = _get_svg_attr(elem, 'font-weight', '400')
                    anchor = _get_svg_attr(elem, 'text-anchor', 'start')
                    estimated_w = _estimate_svg_text_width(text, fs, fw) * 1.12
                    tspan_count = sum(
                        1 for child in elem.iter()
                        if child is not elem and _local_name(child.tag) == 'tspan'
                    )
                    line_count = max(1, tspan_count)
                    estimated_h = fs * 1.35 * line_count

                    if anchor == 'middle':
                        box_x = x - estimated_w / 2
                    elif anchor == 'end':
                        box_x = x - estimated_w
                    else:
                        box_x = x
                    box_y = y - fs * 0.85

                    data_box = elem.get('data-box')
                    if data_box:
                        parts = [p.strip() for p in re.split(r'[\s,]+', data_box) if p.strip()]
                        if len(parts) == 4:
                            try:
                                bx, by, bw, bh = [float(p) for p in parts]
                                box_x, box_y, estimated_w, estimated_h = bx + tx, by + ty, bw, bh
                            except ValueError:
                                pass

                    texts.append({
                        'text': text,
                        'x': x,
                        'y': y,
                        'x1': box_x,
                        'y1': box_y,
                        'x2': box_x + estimated_w,
                        'y2': box_y + estimated_h,
                    })

            for child in list(elem):
                visit(child, tx, ty)

        visit(root)
        return texts

    def _boxes_intersect(self, a: Dict, b: Dict) -> bool:
        return (
            a['x1'] < b['x2'] and
            a['x2'] > b['x1'] and
            a['y1'] < b['y2'] and
            a['y2'] > b['y1']
        )

    def _is_bottom_right_page_number(self, text: Dict) -> bool:
        raw = text.get('text', '').strip()
        if not raw:
            return False
        token = raw.replace(' ', '')
        looks_like_page = (
            token == '{{PAGE_NUM}}' or
            bool(re.fullmatch(r'\d{1,3}(?:/\d{1,3})?', token))
        )
        if not looks_like_page:
            return False
        return text['x'] >= 1140 and text['y'] >= 640

    def _check_image_references(self, content: str, svg_path: Path, result: Dict):
        """Check image file existence and resolution vs display size."""
        # Find all <image ...> elements (capture the full tag)
        img_tag_pattern = re.compile(r'<image\b([^>]*)/?>', re.IGNORECASE)

        svg_dir = svg_path.parent
        checked = set()

        for tag_match in img_tag_pattern.finditer(content):
            attrs = tag_match.group(1)

            # Extract href (prefer href over xlink:href)
            href_match = (
                re.search(r'\bhref="(?!data:)([^"]+)"', attrs) or
                re.search(r'\bxlink:href="(?!data:)([^"]+)"', attrs)
            )
            if not href_match:
                continue

            href = href_match.group(1)
            if href in checked:
                continue
            checked.add(href)

            # Resolve path relative to SVG file directory
            img_path = (svg_dir / href).resolve()
            if self.template_mode and not img_path.exists():
                # Templates retain project-relative paths while their source
                # package keeps reusable assets beside the SVG files.
                template_asset = svg_dir / Path(href).name
                if template_asset.exists():
                    img_path = template_asset.resolve()

            if not img_path.exists():
                result['errors'].append(
                    f"Image file not found: {href} (resolved to {img_path})")
                continue

            # Check resolution vs display size
            w_match = re.search(r'\bwidth="([^"]+)"', attrs)
            h_match = re.search(r'\bheight="([^"]+)"', attrs)
            display_w_str = w_match.group(1) if w_match else None
            display_h_str = h_match.group(1) if h_match else None
            if not display_w_str or not display_h_str:
                continue

            try:
                display_w = float(display_w_str)
                display_h = float(display_h_str)
            except (ValueError, TypeError):
                continue

            try:
                from PIL import Image as PILImage
                with PILImage.open(img_path) as img:
                    actual_w, actual_h = img.size

                if actual_w < display_w or actual_h < display_h:
                    result['warnings'].append(
                        f"Image {href} is {actual_w}x{actual_h} but displayed at "
                        f"{int(display_w)}x{int(display_h)} — may appear blurry")
                elif actual_w > display_w * 4 and actual_h > display_h * 4:
                    result['warnings'].append(
                        f"Image {href} is {actual_w}x{actual_h} but displayed at "
                        f"{int(display_w)}x{int(display_h)} — consider downsizing "
                        f"to reduce file size")
            except ImportError:
                pass  # PIL not available, skip resolution check
            except Exception:
                pass  # Image unreadable, skip resolution check

    def _check_animation_group_ids(self, content: str, result: Dict):
        """Warn when visible top-level groups cannot be customized."""
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            return

        non_visual = {'defs', 'title', 'desc', 'metadata', 'style'}
        for index, child in enumerate(list(root), start=1):
            tag = child.tag.split('}', 1)[-1]
            if tag in non_visual:
                continue
            if tag == 'g' and not child.get('id'):
                result['warnings'].append(
                    f"Top-level visible <g> #{index} has no id; "
                    "object-level animation config cannot reference it"
                )

    def _get_spec_lock(self, svg_path: Path):
        """Locate and parse spec_lock.md near the SVG. Returns dict or None.

        Walks upward from the SVG directory. This covers common layouts
        (<project>/svg_output/) and staged chapter-parallel output under
        <project>/parallel_generation/runs/<run_id>/work/<group>/svg_output/.
        """
        if _parse_spec_lock is None:
            return None
        for parent in (svg_path.parent, *svg_path.parent.parents):
            candidate = parent / 'spec_lock.md'
            if candidate in self._lock_cache:
                return self._lock_cache[candidate]
            if candidate.exists():
                try:
                    data = _parse_spec_lock(candidate)
                except Exception:
                    data = None
                self._lock_cache[candidate] = data
                if data is not None:
                    self._lock_seen = True
                return data
        return None

    def _check_spec_lock_drift(self, content: str, svg_path: Path, result: Dict):
        """Detect values used in the SVG that fall outside spec_lock.md.

        Covers colors (fill / stroke / stop-color), font-family, and font-size.
        Emits per-file warnings summarising the drift counts; exact drifting
        values are accumulated in self._drift_summary for the end-of-run
        aggregation. When spec_lock.md is missing, silently skip (consistent
        with executor-base.md §2.1's 'missing lock → warn and proceed' policy).
        """
        lock = self._get_spec_lock(svg_path)
        if lock is None:
            return

        # Build allow-sets from the lock
        allowed_colors = set()
        for v in lock.get('colors', {}).values():
            if HEX_VALUE_RE.fullmatch(v):
                allowed_colors.add(v.upper())

        typo = lock.get('typography', {})
        # Font families: default `font_family` plus any per-role `*_family`
        # override (title_family / body_family / emphasis_family / code_family,
        # per spec_lock_reference.md). Any of these is a legitimate declared
        # value; an SVG that uses any one of them is not drifting.
        allowed_fonts = set()
        if typo:
            default_font = html.unescape(typo.get('font_family', '').strip())
            if default_font:
                allowed_fonts.add(default_font)
            for k, v in typo.items():
                if k == 'font_family' or not k.endswith('_family'):
                    continue
                v_clean = html.unescape(v.strip())
                # Skip placeholder text like "same as body (omit if identical)"
                if not v_clean or v_clean.lower().startswith('same as'):
                    continue
                allowed_fonts.add(v_clean)

        # Sizes: declared slots are anchors; body is the ramp baseline.
        allowed_sizes = set()
        body_px = None
        for k, v in typo.items():
            if k == 'font_family' or k.endswith('_family'):
                continue
            allowed_sizes.add(self._normalize_size(v))
            if k == 'body':
                try:
                    body_px = float(self._normalize_size(v))
                except (ValueError, TypeError):
                    body_px = None

        # Scan SVG for used values
        color_drifts = set()
        for attr in ('fill', 'stroke', 'stop-color'):
            pattern = re.compile(rf'\b{attr}\s*=\s*["\'](#[0-9A-Fa-f]{{3,8}})["\']')
            for m in pattern.finditer(content):
                val = m.group(1).upper()
                if val not in allowed_colors:
                    color_drifts.add(val)

        font_drifts = set()
        for m in re.finditer(r'font-family\s*=\s*["\']([^"\']+)["\']', content):
            val = html.unescape(m.group(1).strip())
            if allowed_fonts and val not in allowed_fonts:
                font_drifts.add(val)

        size_drifts = set()
        for m in re.finditer(r'font-size\s*=\s*["\']([^"\']+)["\']', content):
            val = self._normalize_size(m.group(1))
            if not allowed_sizes or val in allowed_sizes:
                continue
            # Intermediate values are allowed when they sit inside the ramp
            # envelope (ratio to body within [RAMP_MIN_RATIO, RAMP_MAX_RATIO]).
            if body_px and body_px > 0:
                try:
                    ratio = float(val) / body_px
                    if RAMP_MIN_RATIO <= ratio <= RAMP_MAX_RATIO:
                        continue
                except ValueError:
                    pass
            size_drifts.add(val)

        # Record in run-wide aggregation
        fname = svg_path.name
        for v in color_drifts:
            self._drift_summary['colors'][v].add(fname)
        for v in font_drifts:
            self._drift_summary['fonts'][v].add(fname)
        for v in size_drifts:
            self._drift_summary['sizes'][v].add(fname)

        # Per-file warning (one condensed line; details live in summary)
        parts = []
        if color_drifts:
            parts.append(f"{len(color_drifts)} color(s)")
        if font_drifts:
            parts.append(f"{len(font_drifts)} font-family value(s)")
        if size_drifts:
            parts.append(f"{len(size_drifts)} font-size value(s)")
        if parts:
            message = (
                f"spec_lock drift: {', '.join(parts)} not in spec_lock.md "
                "(see drift summary for details)"
            )
            if self._get_brand_profile(svg_path, content) == VIETTEL_BRAND_PROFILE:
                result['errors'].append(message)
            else:
                result['warnings'].append(message)

    def _find_image_sources_manifest(self, svg_path: Path) -> Path | None:
        """Locate image_sources.json for a project SVG.

        Quality checks run primarily on <project>/svg_output/*.svg, but this
        also supports SVGs checked from project root or svg_final.
        """
        bases = (svg_path.parent, svg_path.parent.parent, svg_path.parent.parent.parent)
        for base in bases:
            candidate = base / 'images' / 'image_sources.json'
            if candidate.exists():
                return candidate
        return None

    def _load_image_sources_manifest(self, svg_path: Path) -> Dict:
        manifest_path = self._find_image_sources_manifest(svg_path)
        if manifest_path is None:
            return {}
        if manifest_path in self._source_manifest_cache:
            return self._source_manifest_cache[manifest_path]
        try:
            payload = json.loads(manifest_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            payload = {}
        self._source_manifest_cache[manifest_path] = payload
        return payload

    def _check_sourced_image_attribution(self, content: str, svg_path: Path, result: Dict):
        """Require visible credit text for attribution-required web images.

        image_search.py records the legal tier in images/image_sources.json;
        Executor must render compact credit text into the SVG. This check
        prevents a quality-first CC BY / CC BY-SA image from silently reaching
        export without attribution.
        """
        manifest = self._load_image_sources_manifest(svg_path)
        items = manifest.get('items') or []
        if not items:
            return

        text_content = html.unescape(re.sub(r'<[^>]+>', ' ', content))
        text_content = re.sub(r'\s+', ' ', text_content)
        svg_stem = svg_path.stem

        for item in items:
            if not item.get('attribution_required') and item.get('license_tier') != 'attribution-required':
                continue

            filename = Path(str(item.get('filename') or '')).name
            slide = str(item.get('slide') or '').strip()
            referenced = bool(filename and filename in content)
            same_slide = bool(slide and slide == svg_stem)
            if not referenced and not same_slide:
                continue

            license_name = str(item.get('license_name') or '').upper()
            license_token = 'CC BY-SA' if 'BY-SA' in license_name else 'CC BY'
            has_credit = license_token in text_content.upper()
            if not has_credit:
                result['errors'].append(
                    f"Missing inline attribution for sourced image {filename or '(unknown)'} "
                    f"({license_token}). Add compact credit text per "
                    f"references/image-searcher.md §7."
                )

    @staticmethod
    def _normalize_size(value: str) -> str:
        """Normalize a font-size value for comparison: lowercase, strip spaces,
        strip trailing 'px'. Other units (em / rem / %) are kept as-is so that
        e.g. '1.5em' vs '24' stay distinct."""
        v = value.strip().lower()
        if v.endswith('px'):
            v = v[:-2].strip()
        return v

    def _categorize_issue(self, error_msg: str) -> str:
        """Categorize issue type"""
        if 'Invalid XML' in error_msg:
            return 'XML well-formedness'
        elif 'viewBox' in error_msg:
            return 'viewBox issues'
        elif 'foreignObject' in error_msg:
            return 'foreignObject'
        elif 'font' in error_msg.lower():
            return 'Font issues'
        elif 'text layout overflow' in error_msg.lower() or 'wrap contract' in error_msg.lower():
            return 'Text layout overflow'
        elif 'text overlap/collision' in error_msg.lower():
            return 'Text overlap'
        elif 'layer-cover risk' in error_msg.lower():
            return 'Layer covering text'
        elif 'title/header zone' in error_msg.lower():
            return 'Title zone intrusion'
        else:
            return 'Other'

    def check_directory(self, directory: str, expected_format: str = None) -> List[Dict]:
        """
        Check all SVG files in a directory

        Args:
            directory: Directory path
            expected_format: Expected canvas format

        Returns:
            List of check results
        """
        dir_path = Path(directory)

        if not dir_path.exists():
            print(f"[ERROR] Directory does not exist: {directory}")
            return []

        # Find all SVG files
        if dir_path.is_file():
            svg_files = [dir_path]
        else:
            if self.template_mode:
                # Template directories live at templates/layouts/<id>/.
                svg_files = sorted(dir_path.glob('*.svg'))
            else:
                svg_output = dir_path / \
                    'svg_output' if (
                        dir_path / 'svg_output').exists() else dir_path
                svg_files = sorted(svg_output.glob('*.svg'))

        if not svg_files:
            print(f"[WARN] No SVG files found")
            return []

        print(f"\n[SCAN] Checking {len(svg_files)} SVG file(s)...\n")

        for svg_file in svg_files:
            result = self.check_file(str(svg_file), expected_format)
            self._print_result(result)

        if self.template_mode and dir_path.is_dir():
            self._check_template_contract(dir_path, svg_files)
        elif dir_path.is_dir():
            self._check_animation_config_contract(dir_path)

        return self.results

    def _check_animation_config_contract(self, dir_path: Path) -> None:
        """Project-level animations.json reference checks."""
        if _load_animation_config is None or _validate_animation_config is None:
            return
        project_path = dir_path if (dir_path / 'svg_output').exists() else dir_path.parent
        try:
            config = _load_animation_config(project_path)
        except Exception as exc:
            self._animation_issues.append(('error', f"animations.json is invalid: {exc}"))
            return
        if not config:
            return
        for warning in _validate_animation_config(project_path, config):
            self._animation_issues.append(('warning', warning))

    def _check_template_contract(self, dir_path: Path,
                                 svg_files: List[Path]) -> None:
        """Template-mode-only checks: roster ↔ design_spec consistency and
        per-page placeholder hints.

        - **Roster mismatch (orphan / missing)** is reported as an *error*: a
          stale roster will produce a wrong ``layouts_index.json`` entry.
        - **Placeholder gaps** are reported as *warnings*. Templates may
          legitimately omit conventional placeholders or swap them out (e.g.
          ``{{CLOSING_MESSAGE}}`` instead of ``{{THANK_YOU}}``), and a content
          variant may use a bespoke slot vocabulary. Designers can declare
          their own per-stem expectations via ``placeholders:`` frontmatter
          in ``design_spec.md`` to suppress these warnings explicitly.

        Issues are aggregated and printed in :py:meth:`print_summary` so the
        per-file report stays focused on intrinsic SVG validity.
        """
        spec_path = dir_path / 'design_spec.md'
        spec_text = spec_path.read_text(encoding='utf-8') if spec_path.exists() else ""
        spec_pages = self._extract_spec_roster(spec_text) if spec_text else []
        custom_contract = self._extract_frontmatter_placeholders(spec_text) if spec_text else {}

        on_disk = {p.stem for p in svg_files}

        if spec_pages:
            spec_set = set(spec_pages)
            orphan = sorted(on_disk - spec_set)
            missing = sorted(spec_set - on_disk)
            for page in orphan:
                self._template_issues.append((
                    'error',
                    'roster_orphan',
                    f"{page}.svg exists on disk but is not listed in design_spec.md Page Roster",
                ))
            for page in missing:
                self._template_issues.append((
                    'error',
                    'roster_missing',
                    f"design_spec.md Page Roster lists {page} but {page}.svg is missing on disk",
                ))
        elif spec_path.exists():
            # design_spec.md is present but the roster parser found nothing —
            # surface as a warning. Legacy specs may lack an explicit roster.
            self._template_issues.append((
                'warning',
                'roster_unknown',
                f"could not extract page roster from {spec_path.name}; "
                "skipping orphan/missing checks",
            ))
        else:
            self._template_issues.append((
                'error',
                'spec_missing',
                f"{spec_path.name} not found — required for every library template",
            ))

        # Per-file placeholder coverage. Variants reuse the parent type's set
        # (e.g. 03a_content_two_col.svg ↔ 03_content rules) unless the spec
        # frontmatter overrides that page (custom_contract takes precedence).
        for svg_file in svg_files:
            expected = self._lookup_template_contract(
                svg_file.stem, overrides=custom_contract,
            )
            if expected is None:
                continue  # extension pages or stems with no convention
            try:
                content = svg_file.read_text(encoding='utf-8')
            except OSError:
                continue
            for placeholder in expected:
                if placeholder not in content:
                    self._template_issues.append((
                        'warning',
                        'placeholder_hint',
                        f"{svg_file.name}: missing conventional placeholder {placeholder} "
                        "(declare 'placeholders:' frontmatter in design_spec.md to silence)",
                    ))

    @staticmethod
    def _extract_frontmatter_placeholders(spec_text: str) -> Dict[str, Tuple[str, ...]]:
        """Read the optional ``placeholders:`` map from design_spec.md frontmatter.

        Shape:

        .. code-block:: yaml

            placeholders:
              01_cover: ["{{TITLE}}", "{{BRAND_LOGO}}"]
              03_content: []        # explicitly assert "no expectation"
              03a_content_two_col:  # variant-specific override
                - "{{LEFT_TITLE}}"
                - "{{RIGHT_TITLE}}"

        Each key is a stem (full filename without ``.svg``) or page-type prefix
        (``01_cover``). An empty list silences the default convention for that
        stem; a populated list replaces the default. Stems / prefixes not
        listed fall back to ``DEFAULT_PLACEHOLDER_CONVENTION``.

        We parse with PyYAML when available; otherwise we fall back to a
        minimal regex that handles the documented shape.
        """
        if not spec_text.startswith("---\n"):
            return {}
        end = spec_text.find("\n---\n", 4)
        if end == -1:
            return {}
        block = spec_text[4:end]

        try:
            import yaml  # type: ignore
        except ImportError:
            return _parse_placeholders_fallback(block)

        try:
            data = yaml.safe_load(block) or {}
        except yaml.YAMLError:
            return {}
        if not isinstance(data, dict):
            return {}
        raw = data.get("placeholders")
        if not isinstance(raw, dict):
            return {}

        out: Dict[str, Tuple[str, ...]] = {}
        for stem, value in raw.items():
            if not isinstance(stem, str):
                continue
            if isinstance(value, list):
                out[stem] = tuple(str(v) for v in value)
            elif value is None:
                out[stem] = ()
        return out

    @staticmethod
    def _extract_spec_roster(spec_text: str) -> List[str]:
        """Best-effort: extract the page roster from design_spec.md.

        Templates do not share a uniform section index for the roster — the
        personality-only skeleton puts it at §V "Page Roster"; legacy specs use
        §VI "Page Roster" or bury filenames under §VII "Page Types" as
        ``### N. Cover Page (01_cover.svg)``. We match by title (any roman
        index), then fall back to scanning the whole document for any
        backtick-wrapped ``<stem>.svg`` reference.

        Returns the deduplicated stem list in document order. Empty result
        means we can't determine the roster confidently — caller should treat
        that as "skip orphan/missing checks", not as "no pages declared".
        """
        # Pass 1: explicit roster section, any roman numeral.
        section = re.search(
            r"^##\s+[IVX]+\.\s+(?:Page Roster|Page Structure|Pages|Page Types)\b.*?(?=^##\s+|\Z)",
            spec_text,
            re.MULTILINE | re.DOTALL | re.IGNORECASE,
        )
        scope = section.group(0) if section else None

        # Pass 2: full document. We *only* trust this scan when the explicit
        # roster scan came up empty (no `<stem>.svg` references inside it) —
        # otherwise the explicit section's deliberate roster wins over loose
        # mentions elsewhere.
        if scope and re.search(r"[`\(][0-9A-Za-z_]+\.svg[`\)]", scope):
            text = scope
        else:
            text = spec_text

        stems: List[str] = []
        seen: set = set()
        # Accept backtick-quoted (`01_cover.svg`) and parenthesized
        # (01_cover.svg) forms — existing specs use either.
        svg_ref_re = re.compile(r"[`\(]([0-9A-Za-z_]+\.svg)[`\)]")
        for match in svg_ref_re.finditer(text):
            stem = match.group(1)[:-4]
            if stem in seen or not re.match(r"^\d", stem):
                continue
            seen.add(stem)
            stems.append(stem)

        # If the explicit §VI scan listed bare stems (without .svg), accept
        # those as fallback — but only when they were inside that section.
        if not stems and scope:
            for match in re.finditer(r"`([0-9]{2}[a-z]?_[A-Za-z0-9_]+)`", scope):
                stem = match.group(1)
                if stem in seen:
                    continue
                seen.add(stem)
                stems.append(stem)

        return stems

    @classmethod
    def _lookup_template_contract(
        cls, stem: str, *,
        overrides: Dict[str, Tuple[str, ...]] | None = None,
    ) -> Tuple[str, ...] | None:
        """Resolve a SVG stem to its expected placeholder set.

        Resolution order, first hit wins:
        1. ``overrides[stem]`` — frontmatter entry for the exact filename
        2. ``overrides[<page_type_prefix>]`` — frontmatter entry for the
           variant's parent type (e.g. ``03_content`` for
           ``03a_content_two_col``)
        3. ``DEFAULT_PLACEHOLDER_CONVENTION[<page_type_prefix>]``

        Returns ``None`` for stems with no matching convention or override —
        e.g. extension pages like ``05_section_break``. ``()`` (empty tuple)
        is a valid value meaning "no expected placeholders" — used to
        explicitly silence the default convention.
        """
        overrides = overrides or {}
        if stem in overrides:
            return overrides[stem]

        # Variant convention: <NN><letter>?_<rest>; strip the letter to find
        # the parent type prefix, e.g. "03a_content_two_col" -> "03_content".
        match = re.match(r"^(\d{2})([a-z])?_([a-z]+)", stem)
        if not match:
            return None
        num, _letter, kind = match.groups()
        key = f"{num}_{kind}"
        if key in overrides:
            return overrides[key]
        return cls.DEFAULT_PLACEHOLDER_CONVENTION.get(key)

    def _print_result(self, result: Dict):
        """Print check result for a single file"""
        if result['passed']:
            if result['warnings']:
                icon = "[WARN]"
                status = "Passed (with warnings)"
            else:
                icon = "[OK]"
                status = "Passed"
        else:
            icon = "[ERROR]"
            status = "Failed"

        print(f"{icon} {result['file']} - {status}")

        # Display basic info
        if result['info']:
            info_items = []
            if 'viewbox' in result['info']:
                info_items.append(f"viewBox: {result['info']['viewbox']}")
            if info_items:
                print(f"   {' | '.join(info_items)}")

        # Display errors
        if result['errors']:
            for error in result['errors']:
                print(f"   [ERROR] {error}")

        # Display warnings
        if result['warnings']:
            for warning in result['warnings'][:2]:  # Only show first 2 warnings
                print(f"   [WARN] {warning}")
            if len(result['warnings']) > 2:
                print(f"   ... and {len(result['warnings']) - 2} more warning(s)")

        print()

    def print_summary(self):
        """Print check summary"""
        print("=" * 80)
        print("[SUMMARY] Check Summary")
        print("=" * 80)

        print(f"\nTotal files: {self.summary['total']}")
        print(
            f"  [OK] Fully passed: {self.summary['passed']} ({self._percentage(self.summary['passed'])}%)")
        print(
            f"  [WARN] With warnings: {self.summary['warnings']} ({self._percentage(self.summary['warnings'])}%)")
        print(
            f"  [ERROR] With errors: {self.summary['errors']} ({self._percentage(self.summary['errors'])}%)")

        if self.issue_types:
            print(f"\nIssue categories:")
            for issue_type, count in sorted(self.issue_types.items(), key=lambda x: x[1], reverse=True):
                print(f"  {issue_type}: {count}")

        # spec_lock drift aggregation (only printed when a lock was found)
        self._print_drift_summary()

        # Template-mode aggregation (orphan/missing roster + placeholder hints)
        self._print_template_summary()

        # Animation config aggregation.
        self._print_animation_summary()

        # Fix suggestions
        if self.summary['errors'] > 0 or self.summary['warnings'] > 0:
            print(f"\n[TIP] Common fixes:")
            print(f"  1. XML well-formedness: write typography as raw Unicode (—, ©, →, NBSP); escape XML reserved chars as &amp; &lt; &gt; &quot; &apos; — never use HTML named entities like &nbsp; &mdash; &copy;")
            print(f"  2. viewBox issues: Ensure consistency with canvas format (see references/canvas-formats.md)")
            print(f"  3. foreignObject: Use separate <text> lines or data-box/data-wrap")
            print(f"  4. Font issues: end every font-family stack with a PPT-safe family (e.g. Microsoft YaHei / Arial / Consolas)")
            print(f"  5. Visual collisions: move overlapping text apart and keep opaque shapes/images behind text")

    def _print_animation_summary(self):
        """Print animations.json validation issues if present."""
        if not self._animation_issues:
            return

        errors = [item for item in self._animation_issues if item[0] == 'error']
        warnings = [item for item in self._animation_issues if item[0] == 'warning']
        self.summary['errors'] += len(errors)
        self.summary['warnings'] += len(warnings)
        for severity, _msg in self._animation_issues:
            self.issue_types[f'animation_config_{severity}'] += 1

        print("\n[ANIMATION] animations.json checks")
        for _severity, msg in errors:
            print(f"  [ERROR] {msg}")
        for _severity, msg in warnings:
            print(f"  [WARN] {msg}")

    def _print_template_summary(self):
        """Aggregate template-mode roster / placeholder issues at the bottom.

        Errors land under the ``errors`` summary count (so the exit signal
        from ``main`` agrees), warnings under ``warnings``. Both are listed
        per file so the user can act on them directly.
        """
        if not self._template_issues:
            return

        errors = [item for item in self._template_issues if item[0] == 'error']
        warnings = [item for item in self._template_issues if item[0] == 'warning']

        # Mirror into the global summary so downstream "0 errors" gates honor
        # template-mode issues.
        self.summary['errors'] += len(errors)
        self.summary['warnings'] += len(warnings)
        for severity, kind, _msg in self._template_issues:
            self.issue_types[f"template_{kind}"] += 1

        print("\n[TEMPLATE] Template mode checks")
        if errors:
            print(f"  Errors ({len(errors)}):")
            for _sev, kind, msg in errors:
                print(f"    [{kind}] {msg}")
        if warnings:
            print(f"  Warnings ({len(warnings)}):")
            for _sev, kind, msg in warnings:
                print(f"    [{kind}] {msg}")
        if not errors:
            print("  No structural roster issues. Placeholder hints above are advisory only;")
            print("  declare 'placeholders:' frontmatter in design_spec.md to silence them.")

    def _print_drift_summary(self):
        """Print spec_lock drift aggregation if any was observed.

        Values are sorted by file-count descending so frequent drift surfaces
        first. Frequent drift usually means spec_lock.md is missing entries
        the Strategist should have included; rare drift is more likely actual
        Executor drift and warrants SVG review.
        """
        if not self._lock_seen:
            return
        has_drift = any(self._drift_summary[cat] for cat in self._drift_summary)
        if not has_drift:
            print("\n[OK] spec_lock drift: none — all colors, fonts, and sizes are anchored to spec_lock.md")
            return

        print("\nspec_lock drift — values used outside spec_lock.md:")
        labels = [('colors', 'Colors'),
                  ('fonts', 'Font families'),
                  ('sizes', 'Font sizes')]
        for category, label in labels:
            items = self._drift_summary.get(category, {})
            if not items:
                continue
            entries = sorted(items.items(), key=lambda x: (-len(x[1]), x[0]))
            print(f"  {label}:")
            for val, files in entries:
                n = len(files)
                suffix = "file" if n == 1 else "files"
                print(f"    {val}  ({n} {suffix})")
        print(
            "Tip: frequent out-of-lock values usually mean spec_lock.md is missing\n"
            "     entries — extend the lock (scripts/update_spec.py or manual edit).\n"
            "     Rare ones are likely Executor drift — review the affected SVGs."
        )

    def _percentage(self, count: int) -> int:
        """Calculate percentage"""
        if self.summary['total'] == 0:
            return 0
        return int(count / self.summary['total'] * 100)

    def export_report(self, output_file: str = 'svg_quality_report.txt'):
        """Export check report"""
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("PPT Master SVG Quality Check Report\n")
            f.write("=" * 80 + "\n\n")

            for result in self.results:
                status = "[OK] Passed" if result['passed'] else "[ERROR] Failed"
                f.write(f"{status} - {result['file']}\n")
                f.write(f"Path: {result.get('path', 'N/A')}\n")

                if result['info']:
                    f.write(f"Info: {result['info']}\n")

                if result['errors']:
                    f.write(f"\nErrors:\n")
                    for error in result['errors']:
                        f.write(f"  - {error}\n")

                if result['warnings']:
                    f.write(f"\nWarnings:\n")
                    for warning in result['warnings']:
                        f.write(f"  - {warning}\n")

                f.write("\n" + "-" * 80 + "\n\n")

            # Write summary
            f.write("\n" + "=" * 80 + "\n")
            f.write("Check Summary\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Total files: {self.summary['total']}\n")
            f.write(f"Fully passed: {self.summary['passed']}\n")
            f.write(f"With warnings: {self.summary['warnings']}\n")
            f.write(f"With errors: {self.summary['errors']}\n")

        print(f"\n[REPORT] Check report exported: {output_file}")


def print_usage() -> None:
    """Print CLI usage information."""
    print("PPT Master - SVG Quality Check Tool\n")
    print("Usage:")
    print("  python3 scripts/svg_quality_checker.py <svg_file>")
    print("  python3 scripts/svg_quality_checker.py <directory>")
    print("  python3 scripts/svg_quality_checker.py <template_dir> --template-mode")
    print("  python3 scripts/svg_quality_checker.py --all examples")
    print("\nExamples:")
    print("  python3 scripts/svg_quality_checker.py examples/project/svg_output/slide_01.svg")
    print("  python3 scripts/svg_quality_checker.py examples/project/svg_output")
    print("  python3 scripts/svg_quality_checker.py examples/project")
    print("  python3 scripts/svg_quality_checker.py templates/layouts/anthropic --template-mode")
    print("\nOptions:")
    print("  --format <ppt169|ppt43|...>   Expected canvas format")
    print("  --template-mode               Validate a templates/layouts/<id> directory:")
    print("                                  glob *.svg directly, skip spec_lock checks,")
    print("                                  enforce roster ↔ design_spec.md Page Roster consistency,")
    print("                                  and emit advisory placeholder-convention warnings.")


def main() -> None:
    """Run the CLI entry point."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)

    if sys.argv[1] in {"-h", "--help", "help"}:
        print_usage()
        sys.exit(0)

    if sys.argv[1].startswith("--") and sys.argv[1] not in {"--all"}:
        print(f"[ERROR] Missing target before option: {sys.argv[1]}")
        print_usage()
        sys.exit(1)

    template_mode = '--template-mode' in sys.argv
    checker = SVGQualityChecker(template_mode=template_mode)

    # Parse arguments
    target = sys.argv[1]
    expected_format = None

    if '--format' in sys.argv:
        idx = sys.argv.index('--format')
        if idx + 1 < len(sys.argv):
            expected_format = sys.argv[idx + 1]

    # Execute check
    if target == '--all':
        # Check all example projects
        base_dir = sys.argv[2] if len(sys.argv) > 2 else 'examples'
        from project_utils import find_all_projects
        projects = find_all_projects(base_dir)

        for project in projects:
            print(f"\n{'=' * 80}")
            print(f"Checking project: {project.name}")
            print('=' * 80)
            checker.check_directory(str(project))
    else:
        checker.check_directory(target, expected_format)

    # Print summary
    checker.print_summary()

    # Export report (if specified)
    if '--export' in sys.argv:
        output_file = 'svg_quality_report.txt'
        if '--output' in sys.argv:
            idx = sys.argv.index('--output')
            if idx + 1 < len(sys.argv):
                output_file = sys.argv[idx + 1]
        checker.export_report(output_file)

    # Return exit code
    if checker.summary['errors'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
