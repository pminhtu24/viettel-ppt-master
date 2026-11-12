# Page brief rules (sub-agent and main agent)

These are the rules the checks cannot catch, plus the content bindings that `page_plan.py check <project> --pages <PID>` verifies. Everything that command reports (brand colors/fonts/weights, deep-blue scope, logo clearance, page number, backgrounds, rails, forbidden elements, spec_lock drift, text overflow, title zone, bindings) you fix on your own SVG until it reports nothing. Never open the skill's scripts to learn these rules — this file and the check output are complete; each finding names the element and what to change.

1. **Content grounding** — show only facts, derived values and conclusions present in this page's content lock. Never add numbers, comparisons, trends, rankings or causal claims to fill a layout. Keep every meaning-bearing qualifier visible ("dự kiến", "khoảng", "kế hoạch", "lũy kế", period and scope); a number's period/scope label (KH tháng, Q3, lũy kế năm, tuần) is the one in its lock entry and stays next to it — never relabel, drop or invent it. `page_plan.py check` also traces your wording: a period label must be the one your bound source attaches to that number (same clause); keep "nguy cơ", "dự kiến", "chưa" with their status word and never add a status (chậm, vượt, đạt…) your bound source does not say; a place/project/unit named in a card heading must be the section of every number in that card; keep the noun after a ratio (`9/9 nhiệm vụ`, not `9/9`); a count in a title must equal the items listed. Every `required` ID must be visibly represented. Never show internal identifiers (source block IDs such as `S…-B0006`, lock IDs, file names). Bind while you draw, not afterwards: root `<svg data-content-contract="1">`; every visible `<text>` (or its parent `<g>`) carries `data-claims="<IDs from this page's lock>"` naming exactly the facts/derived/conclusions it shows — a number may appear only in a text bound to an ID whose `text`/`raw`/`value` contains it; neutral headings, labels and the "Nguồn: …" footer bind to an editorial conclusion ID. Copy locked tokens verbatim (`2027-2029`, not `2027 -2029`). Exempt only `data-chrome="page-number"` (digits) and `data-chrome="logo"`. (content-grounding §2, §3, §5)
2. **Chart geometry from the lock** — compute bar/point/arc geometry from the lock's values, never from the visible labels. (content-grounding §4, workflows/verify-charts.md)
3. **Chart markers** — each visualization in the lock whose template is not `none` is one `<g data-chart="<its id, e.g. v1>">` containing its marks and labels; chart pages also carry the `<!-- chart-plot-area: ... -->` comment. Deep blue `#12436D` only inside a group with `data-viettel-blue-scope="chart|diagram|icon|background"`. (content-grounding §3, executor-base §3.1)
4. **Rhythm** — `breathing` pages must not use multi-card grid layouts; `anchor` pages follow their template as-is. (executor-base §2.1, spec_lock_reference page_rhythm)
5. **Animation-ready groups** — 3–8 top-level content `<g id="...">` groups per slide; chrome groups use ids containing `header`, `footer`, `bg`, `background` or `decor`. (shared-standards Element Grouping)
6. **Text fit** — every text run in a card, table cell, chart lane or callout uses manual line breaks or `data-box="x,y,w,h" data-wrap="true"`; keep card padding (18px body, 14px dense chart labels, 24px KPI). Split or trim lower-priority text rather than shrinking below the locked sizes. (executor-base §2.2)
7. **Match the anchor** — reuse the anchor SVG's title/subtitle/divider/footer positions and its card, table and status styling; copy its `viettel-brand-chrome` group as is. Never draw a second logo or page number. (executor-base §3)
8. **Hand-written, one page at a time** — write each SVG directly; never generate SVG with a script. (SKILL.md rule 9)

## Binding pattern

Lock IDs below are examples (`c1` title conclusion, `c_src` editorial source line, `f1`–`f4` facts, `v1` visualization); use your page's own IDs.

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 720" width="1280" height="720" data-content-contract="1">
  <rect x="0" y="0" width="1280" height="720" fill="#FFFFFF"/>
  <g id="header">
    <rect x="60" y="46" width="4" height="64" rx="2" fill="#EE0033"/>
    <text x="78" y="84" font-family="FS Magistral" font-size="30" font-weight="700" fill="#000000" data-claims="c1">Tiêu đề = text of conclusion c1</text>
  </g>
  <g id="chartArea" data-chart="v1" data-viettel-blue-scope="chart">
    <!-- chart-plot-area: 392,196,782,640 -->
    <g id="row-1" data-claims="f1 f2">                  <!-- children inherit f1 f2 -->
      <text x="120" y="238" font-family="FS Magistral" font-size="16" font-weight="700" fill="#000000">PS vị trí 4G mới</text>
      <text x="368" y="239" text-anchor="end" font-family="FS Magistral" font-size="20" font-weight="700" fill="#12436D" data-claims="f1">35%</text>
      <rect x="392" y="225" width="136.5" height="16" rx="8" fill="#12436D"/>  <!-- width from f1.value, not the label -->
      <text x="806" y="238" font-family="FS Magistral" font-size="16" fill="#44494D" data-claims="f1 f2">127/361 vị trí · KH tháng</text>
    </g>
  </g>
  <g id="footer" data-claims="c_src">
    <text x="75" y="697" font-family="FS Magistral" font-size="13" fill="#999999">Nguồn: …</text>
  </g>
  <!-- then the anchor's <g id="viettel-brand-chrome"> copied unchanged (logo + data-chrome="page-number") -->
</svg>
```
