#!/usr/bin/env python3
"""Focused regression checks for actionable SVG quality diagnostics."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

from svg_quality_checker import SVGQualityChecker
from svg_to_pptx.drawingml_converter import prepare_svg_for_native_conversion


def svg(body: str) -> str:
    return (
        '<svg width="1280" height="720" viewBox="0 0 1280 720" '
        'xmlns="http://www.w3.org/2000/svg">'
        f'{body}</svg>'
    )


def layout_errors(body: str) -> list[str]:
    result = {'errors': [], 'warnings': []}
    SVGQualityChecker()._check_text_layout_risk(svg(body), result)
    return result['errors']


def main() -> None:
    three_overflows = ''.join(
        f'<g transform="translate({offset} 0)">'
        '<rect x="80" y="300" width="220" height="90" rx="8" fill="#F2F2F2"/>'
        f'<text id="overflow-{index}" x="95" y="350" font-size="28">'
        'This sentence is intentionally much wider than its card'
        '</text></g>'
        for index, offset in enumerate((0, 360, 720), start=1)
    )
    errors = layout_errors(three_overflows)
    overflow_errors = [error for error in errors if '[text-overflow]' in error]
    assert len(overflow_errors) == 3, overflow_errors
    assert all(f'locator=#overflow-{index}' in '\n'.join(errors) for index in range(1, 4))

    first = layout_errors(
        '<rect x="80" y="300" width="220" height="90" rx="8" fill="#F2F2F2"/>'
        '<text id="stable" x="95" y="350" font-size="28">'
        'This sentence is intentionally much wider than its card</text>'
    )
    second = layout_errors(
        '<rect x="80" y="300" width="220" height="90" rx="8" fill="#F2F2F2"/>'
        '<text id="stable" x="105" y="350" font-size="28">'
        'This sentence is intentionally much wider than its card</text>'
    )
    assert sum('[text-overflow]' in error for error in first) == 1
    assert sum('[text-overflow]' in error for error in second) == 1
    assert 'locator=#stable' in first[0] and 'locator=#stable' in second[0]

    allowed = layout_errors(
        '<rect x="80" y="300" width="220" height="90" rx="8" fill="#F2F2F2"/>'
        '<text id="allowed" data-allow-overflow="true" x="95" y="350" font-size="28">'
        'This sentence is intentionally much wider than its card</text>'
    )
    assert not any('[text-overflow]' in error for error in allowed), allowed

    intruder = layout_errors(
        '<rect id="intruder" x="100" y="130" width="220" height="60" fill="#EE0033"/>'
    )
    assert any('[title-zone] locator=#intruder' in error for error in intruder), intruder
    allowed_title = layout_errors(
        '<g data-allow-title-zone="true">'
        '<rect id="allowed-title" x="100" y="130" width="220" height="60" fill="#EE0033"/>'
        '</g>'
    )
    assert not any('[title-zone]' in error for error in allowed_title), allowed_title

    valid_icon = ET.fromstring(svg(
        '<use data-icon="tabler-filled/layout-cards" '
        'x="100" y="100" width="48" height="48" fill="#000000"/>'
    ))
    expanded, issues = prepare_svg_for_native_conversion(valid_icon)
    assert expanded == 1 and not issues, issues

    missing_icon = ET.fromstring(svg(
        '<use id="missing-icon" data-icon="tabler-outline/definitely-missing-icon" '
        'x="100" y="100" width="48" height="48" fill="#000000"/>'
    ))
    _, issues = prepare_svg_for_native_conversion(missing_icon)
    assert any(
        '[native-icon]' in issue and 'definitely-missing-icon' in issue
        and 'locator=#missing-icon' in issue
        for issue in issues
    ), issues
    checker_native = {'errors': [], 'warnings': []}
    SVGQualityChecker()._check_native_export_compatibility(
        svg(
            '<use id="missing-icon" data-icon="tabler-outline/definitely-missing-icon" '
            'x="100" y="100" width="48" height="48" fill="#000000"/>'
        ),
        checker_native,
    )
    assert checker_native['errors'] == issues

    plain_use = ET.fromstring(svg('<use href="#shape" x="10" y="10"/>'))
    _, issues = prepare_svg_for_native_conversion(plain_use)
    assert any('[native-use]' in issue for issue in issues), issues

    brand_result = {'errors': [], 'warnings': []}
    brand_root = ET.fromstring(svg(
        '<g font-family="Arial">'
        '<text id="bad-brand" x="100" y="100" font-size="20" '
        'font-weight="900" fill="#ABCDEF">Bad brand</text>'
        '</g>'
    ))
    SVGQualityChecker()._check_viettel_fonts_and_colors(brand_root, brand_result)
    brand_errors = '\n'.join(brand_result['errors'])
    assert '[brand-font]' in brand_errors and 'locator' in brand_errors
    assert '[brand-font-weight]' in brand_errors and '#bad-brand' in brand_errors
    assert '[brand-color]' in brand_errors and '#ABCDEF' in brand_errors

    spec_checker = SVGQualityChecker()
    spec_checker._get_spec_lock = lambda _path: {
        'brand': {'profile': 'viettel_default'},
        'colors': {'background': '#FFFFFF'},
        'typography': {'font_family': 'Arial', 'body': '20'},
    }
    spec_result = {'errors': [], 'warnings': []}
    spec_checker._check_spec_lock_drift(
        svg(
            '<rect id="drift-color" x="10" y="10" width="20" height="20" fill="#ABCDEF"/>'
            '<text id="drift-size" x="10" y="100" font-family="Arial" font-size="120">120</text>'
        ),
        Path('sample.svg'),
        spec_result,
    )
    spec_errors = '\n'.join(spec_result['errors'])
    assert '[spec-lock-drift]' in spec_errors
    assert '#drift-color' in spec_errors and '#drift-size' in spec_errors

    print("OK: actionable SVG quality diagnostics")


if __name__ == "__main__":
    main()
