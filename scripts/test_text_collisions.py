#!/usr/bin/env python3
"""Labels that collide, run off the left edge, or hide under a later shape (run 2026-11-13 P05/P10/P12)."""

from svg_quality_checker import SVGQualityChecker


def errors(body: str) -> list[str]:
    result = {'errors': [], 'warnings': []}
    svg = f'<svg viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg" font-family="FS Magistral">{body}</svg>'
    SVGQualityChecker()._check_text_layout_risk(svg, result)
    return result['errors']


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
    print("OK: text collisions")


if __name__ == "__main__":
    main()
