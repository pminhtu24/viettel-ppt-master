#!/usr/bin/env python3
"""Real-font text measurement for the bundled FS Magistral faces.

Used by ``svg_quality_checker`` to check that wrapped text fits its declared
``data-box`` and to replace the character-class width heuristic when the SVG
uses FS Magistral. Everything degrades gracefully: when Pillow or the font
files are unavailable, ``measure_line`` returns ``None`` and ``wrap_runs``
callers are expected to skip the check.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

FONT_DIR = (
    Path(__file__).resolve().parent.parent
    / "templates" / "layouts" / "viettel_default" / "fonts"
)
_MEASURE_EM = 1000
_WORD_SPLIT = re.compile(r"([ \t\r\n]+)")  # NBSP (U+00A0) deliberately not a break


@dataclass(frozen=True)
class Run:
    text: str
    size: float
    face: str  # "Book" | "Medium" | "Bold"


@dataclass
class WrapResult:
    lines: int = 0
    height: float = 0.0
    widest_word: float = 0.0
    widest_word_text: str = ""
    last_line_words: int = 0
    last_line_text: str = ""
    last_line_width: float = 0.0
    last_line_height: float = 0.0
    line_texts: list[str] = field(default_factory=list)


def uses_magistral(font_family: str) -> bool:
    return "magistral" in (font_family or "").lower()


def face_for_weight(weight: object) -> str:
    value = str(weight or "400").strip().lower()
    if value in {"bold", "bolder", "600", "700", "800", "900"}:
        return "Bold"
    if value == "500":
        return "Medium"
    return "Book"


@lru_cache(maxsize=None)
def _font(face: str):
    try:
        from PIL import ImageFont
        return ImageFont.truetype(str(FONT_DIR / f"FS Magistral-{face}.ttf"), _MEASURE_EM)
    except (ImportError, OSError):
        return None


def is_available() -> bool:
    return all(_font(face) is not None for face in ("Book", "Medium", "Bold"))


def line_factor(face: str) -> float:
    """Single-spacing line pitch in em (ascent + descent of the font)."""
    font = _font(face)
    if font is None:
        return 1.35
    ascent, descent = font.getmetrics()
    return (ascent + descent) / _MEASURE_EM


def text_width(text: str, size: float, face: str) -> float:
    font = _font(face)
    if font is None or not text:
        return 0.0
    return font.getlength(text) / _MEASURE_EM * size


def measure_line(text: str, size: float, weight: object, font_family: str) -> float | None:
    """Width in px of ``text`` on one line, or None when it cannot be measured."""
    if not uses_magistral(font_family) or not is_available():
        return None
    return text_width(" ".join(text.split()), size, face_for_weight(weight))


def _split_words(runs: list[Run]) -> list[dict]:
    """Group run text into words; a word may span run boundaries."""
    words: list[dict] = []
    current: list[Run] | None = None
    current_space: Run | None = None
    pending_space: Run | None = None
    for run in runs:
        for part in _WORD_SPLIT.split(run.text):
            if not part:
                continue
            if part.isspace():
                if current is not None:
                    words.append({"pieces": current, "space_before": current_space})
                    current = None
                pending_space = Run(" ", run.size, run.face)
                continue
            if current is None:
                current = []
                current_space = pending_space if words else None
                pending_space = None
            current.append(Run(part, run.size, run.face))
    if current is not None:
        words.append({"pieces": current, "space_before": current_space})
    return words


def wrap_runs(runs: list[Run], box_width: float) -> WrapResult:
    """Greedy word wrap of one paragraph into ``box_width`` px."""
    result = WrapResult()
    words = _split_words([r for r in runs if r.text])
    if not words:
        return result

    line_words: list[str] = []
    line_width = 0.0
    line_height = 0.0

    def close_line() -> None:
        result.lines += 1
        result.height += line_height
        result.last_line_height = line_height
        result.line_texts.append(" ".join(line_words))

    for word in words:
        pieces = word["pieces"]
        text = "".join(p.text for p in pieces)
        width = sum(text_width(p.text, p.size, p.face) for p in pieces)
        height = max(p.size * line_factor(p.face) for p in pieces)
        if width > result.widest_word:
            result.widest_word, result.widest_word_text = width, text
        space = word["space_before"]
        space_w = text_width(" ", space.size, space.face) if space else 0.0

        if not line_words:
            line_words, line_width, line_height = [text], width, height
        elif line_width + space_w + width <= box_width + 0.5:
            line_words.append(text)
            line_width += space_w + width
            line_height = max(line_height, height)
        else:
            close_line()
            line_words, line_width, line_height = [text], width, height
        if width > box_width + 0.5:
            extra = math.ceil(width / box_width) - 1
            line_height += extra * height

    # An NBSP-joined group (e.g. 'KV3:\u00a08/15') is an intentional unit, not one lonely word.
    result.last_line_words = sum(1 + w.count("\u00a0") for w in line_words)
    result.last_line_text = " ".join(line_words)
    result.last_line_width = line_width
    close_line()
    return result
