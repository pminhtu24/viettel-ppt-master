#!/usr/bin/env python3
"""Regression checks for measured text-vs-data-box fit in svg_quality_checker."""

from __future__ import annotations

from svg_quality_checker import SVGQualityChecker
import text_metrics

FAMILY = 'font-family="FS Magistral"'
LONG = (
    "Tận dụng vật tư sẵn có tồn từ triển khai 5G 2026; thu hồi rectifier "
    "tái sử dụng dự phòng, ƯCTT"
)


def svg(body: str) -> str:
    return (
        '<svg width="1280" height="720" viewBox="0 0 1280 720" '
        'xmlns="http://www.w3.org/2000/svg">'
        f'{body}</svg>'
    )


def run(body: str) -> dict:
    result = {'errors': [], 'warnings': []}
    SVGQualityChecker()._check_text_layout_risk(svg(body), result)
    return result


def tags(result: dict, key: str) -> list[str]:
    return [m for m in result[key] if m.startswith('[text-') or ' [text-' in m[:20]]


def has(result: dict, key: str, tag: str) -> bool:
    return any(tag in message for message in result[key])


def box_text(box: str, text: str = LONG, size: int = 16, weight: str = "400",
             extra: str = "", family: str = FAMILY) -> str:
    return (
        f'<text x="120" y="360" data-box="{box}" data-wrap="true" {family} '
        f'font-size="{size}" font-weight="{weight}" {extra}>{text}</text>'
    )


def test_fonts_available() -> None:
    assert text_metrics.is_available()
    assert (text_metrics.line_factor('Book'), text_metrics.line_factor('Bold')) == (1.15, 1.4)


def test_box_too_small_is_error() -> None:
    result = run(box_text("120,344,220,48"))
    assert has(result, 'errors', '[text-box-overflow]'), result
    message = next(m for m in result['errors'] if '[text-box-overflow]' in m)
    assert 'needs 4 line(s) = 73.6px > 48px' in message, message
    assert 'raise the data-box height to >= 74px' in message, message


def test_box_with_room_is_clean() -> None:
    result = run(box_text("120,344,220,90"))
    assert not has(result, 'errors', '[text-box'), result
    assert not has(result, 'warnings', '[text-box'), result


def test_tight_box_warns() -> None:
    result = run(box_text("120,344,220,76"))
    assert not has(result, 'errors', '[text-box'), result
    assert has(result, 'warnings', '[text-box-tight]'), result


def test_small_overrun_warns_not_errors() -> None:
    # 4 lines need 73.6px; 3px short is well under half a line.
    result = run(box_text("120,344,220,70.6"))
    assert not has(result, 'errors', '[text-box'), result
    assert has(result, 'warnings', 'over by 3.0px'), result


def test_orphan_last_line_warns() -> None:
    result = run(box_text("120,344,220,120"))
    assert has(result, 'warnings', '[text-orphan-line]'), result
    assert "'ƯCTT'" in next(m for m in result['warnings'] if '[text-orphan-line]' in m)


def test_word_wider_than_box_is_error() -> None:
    result = run(box_text("120,344,60,200", text="Siêu_dài_không_có_khoảng_trắng", size=20))
    assert has(result, 'errors', '[text-word-too-wide]'), result


def test_nbsp_prevents_orphan() -> None:
    plain = run(box_text("120,344,220,120"))
    joined = run(box_text("120,344,220,120", text=LONG.replace("dự phòng, ƯCTT", "dự phòng,\u00a0ƯCTT")))
    assert has(plain, 'warnings', '[text-orphan-line]'), plain
    assert not has(joined, 'warnings', '[text-orphan-line]'), joined


def test_bold_uses_larger_line_pitch() -> None:
    # One 32px Bold line needs 44.8px (Book would need only 36.8px).
    assert not has(run(box_text("120,344,900,58", "Tiêu đề ngắn", 32, "700")), 'errors', '[text-box')
    two_lines = "Tiêu đề trang rất dài " * 6
    result = run(box_text("120,344,400,58", two_lines, 32, "700"))
    assert has(result, 'errors', '[text-box-overflow]'), result


def test_tspan_runs_flow_as_one_paragraph() -> None:
    body = (
        f'<text x="120" y="360" data-box="120,344,200,40" {FAMILY} font-size="16">'
        '<tspan font-weight="700">Nghiệm thu </tspan><tspan>sản phẩm A1 tại NAN 26/8 '
        'tài nguyên xong trước 2 ngày</tspan></text>'
    )
    assert has(run(body), 'errors', '[text-box-overflow]')


def test_group_font_family_is_inherited() -> None:
    body = (
        f'<g {FAMILY}><text x="120" y="360" data-box="120,344,220,48" '
        f'font-size="16">{LONG}</text></g>'
    )
    assert has(run(body), 'errors', '[text-box-overflow]')


def test_other_font_families_are_not_measured() -> None:
    result = run(box_text("120,344,220,48", family='font-family="Arial"'))
    assert not has(result, 'errors', '[text-box'), result


def test_allow_overflow_opts_out() -> None:
    result = run(box_text("120,344,220,48", extra='data-allow-overflow="true"'))
    assert not has(result, 'errors', '[text-box'), result


def main() -> None:
    tests = [(name, fn) for name, fn in sorted(globals().items())
             if name.startswith('test_') and callable(fn)]
    for name, fn in tests:
        fn()
    print(f'OK: {len(tests)} text-box fit checks')


if __name__ == '__main__':
    main()
