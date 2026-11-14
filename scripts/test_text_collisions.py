#!/usr/bin/env python3
"""Labels that collide, run off the left edge, or hide under a later shape (run 2026-11-13 P05/P10/P12)."""

from svg_quality_checker import SVGQualityChecker


def check(body: str) -> dict:
    result = {'errors': [], 'warnings': []}
    svg = f'<svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg" font-family="FS Magistral">{body}</svg>'
    SVGQualityChecker()._check_text_layout_risk(svg, result)
    return result


def errors(body: str) -> list[str]:
    return check(body)['errors']


def main() -> None:
    header = errors(  # P12: a left-anchored header ran into the previous column's header
        '<rect x="64" y="150" width="1152" height="36" fill="#44494D"/>'
        '<text x="900" y="173" font-size="14" font-weight="700" fill="#FFFFFF" text-anchor="end">% KH năm</text>'
        '<text x="880" y="173" font-size="14" font-weight="700" fill="#FFFFFF">Đánh giá</text>'
    )
    assert any('[text-collision]' in e and 'Đánh giá' in e for e in header), header

    clipped = errors(  # P10: an end-anchored row label longer than its gutter
        '<text x="190" y="346" font-size="18" font-weight="700" text-anchor="end">trong đó: người dùng 5G mới</text>'
    )
    assert any('safe-area overflow(left' in e for e in clipped), clipped

    covered = errors(  # P05: the second line of a row label sat inside the bar drawn after it
        '<text x="330" y="444" font-size="18">nội dung, ứng dụng</text>'
        '<rect x="330" y="432" width="744" height="18" rx="9" fill="#E6E6E6"/>'
    )
    assert any('[text-covered]' in e for e in covered), covered

    fine = errors(  # a backdrop drawn first, stacked lines, a faint watermark, a rotated axis title
        '<rect x="330" y="432" width="744" height="18" rx="9" fill="#E6E6E6"/>'
        '<text x="330" y="444" font-size="18">nội dung, ứng dụng</text>'
        '<text x="330" y="464" font-size="18">dòng thứ hai</text>'
        '<text x="330" y="444" font-size="48" fill="#F46A25" fill-opacity="0.06">WATERMARK</text>'
        '<text x="30" y="380" font-size="16" text-anchor="middle" transform="rotate(-90 30 380)">Doanh thu (tỷ đồng)</text>'
    )
    assert not any('[text-c' in e or 'overflow(left' in e for e in fine), fine
    # run 2026-11-14 P05: rows packed 58px apart — next label inside the bar above, value over the next row
    packed = errors(
        '<rect x="88" y="230" width="610" height="18" rx="9" fill="#EE0033"/>'
        '<text x="708" y="245" font-size="22" font-weight="700">55.743</text>'
        '<text x="88" y="258" font-size="18" font-weight="700">Kinh doanh quốc tế (quy đổi)</text>'
        '<text x="752" y="258" text-anchor="end" font-size="16">72.3% KH năm</text>'
    )
    assert any('[text-on-edge]' in e for e in packed), packed
    assert any('[text-collision]' in e and '55.743' in e for e in packed), packed

    # P14: mixed units on one absolute axis scatter the plan marks
    ticks = check('<g data-chart="v1">' + ''.join(
        f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + 34}" stroke="#6B7280" stroke-dasharray="5 3"/>'
        for x, y in ((1080, 146), (520, 213), (607, 280))) + '</g>')['warnings']
    assert any('[plan-line-misaligned]' in w for w in ticks), ticks

    # P02: the last rows of a table lost their indent
    rows = check(''.join(f'<text x="{112 if i < 9 else 64}" y="{211 + 38 * i}" font-size="18">Chỉ tiêu {i}</text>'
                         for i in range(12)))['warnings']
    assert any('[column-misaligned]' in w and 'x=64' in w for w in rows), rows
    print("OK: text collisions")


if __name__ == "__main__":
    main()
