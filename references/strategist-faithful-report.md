# Role Mode: Faithful Report Structure Mapper

Use this mode for already-structured weekly/monthly/meeting/operations reports
where every meaningful source block must reach the deck. This is a conditional
branch inside `viettel-ppt-master`, not a separate skill.

## Contract

### FAITHFUL REPORT — CLOSED SOURCE MODE

The assigned source blocks are a closed content set. Use only content explicitly
present in those blocks. Never add an insight, cause, risk, direction,
recommendation, conclusion, deadline, owner, status, KPI, reporting period,
forecast, remainder, ratio, or variance. Never combine numbers from different
sentences or time points, use background knowledge, or borrow from another
page's blocks. In particular, preserve contrasts such as `đạt/vượt`,
`đã/đang/chưa`, and `dự kiến/hoàn thành` exactly.

Allowed transformations are mechanical only: line breaks, bullets, moving words
within the same fact into a heading, repeating table headers, and choosing a chart,
timeline, KPI card, diagram, or table that retains the complete source data. If
content does not fit, add a slide. Never summarize, omit, or shrink below the
text-fit floor.

- Treat source order and headings as authoritative. Do not create a new
  narrative, SCQA, pyramid, insight, cause, recommendation, conclusion, or
  priority ranking.
- Coverage is 100% of blocks marked `required: true` in
  `source_inventory.json`. There is no hard slide cap; readability determines
  page count.
- Mechanical editing only: split sentences/bullets, normalize whitespace, or
  move tokens within one fact into a heading. Do not deduplicate across facts;
  every fact must retain its complete token multiset. Preserve terminology,
  negation, qualifiers, status, owner, deadline, units, and every numeric value.
- Do not add executive-summary, key-takeaway, chapter, conclusion, agenda, or
  ending pages unless the source contains the corresponding material. Cover and
  TOC content may use only source metadata/headings.

## Inventory

`scripts/faithful_report.py prepare <project_path>` creates the canonical
inventory. Every heading, paragraph, list item, table row, and image is required
by default and has an id such as `SRC01-B0001`.

Only these exclusion reasons are valid:

- `exact_duplicate`
- `decorative_asset`
- `header_footer_artifact`

An exclusion must be visually/source-structurally verified and written into the
block's `required: false` and `exclusion_reason` fields. Never exclude a block to
meet a page target.

## Eight Confirmations override

Keep the existing eight-item checkpoint, with these mode-specific statements:

- Page count: readable estimate, no hard cap, 100% meaningful-block coverage.
- Audience/content mode: `faithful_report`; source structure is authoritative;
  synthesis is disabled.
- Image approach: source assets plus native charts/icons by default; no web
  images unless the user explicitly requests them.
- Visualization: prefer charts/infographics when they retain every series,
  label, unit, time horizon, qualifier, and value. Otherwise add a detail
  table/callout or split the material across slides.

If the user imposes a page cap below the readable estimate, stop and ask them to
choose completeness or the cap. Do not silently compress or omit content.

## Mapping output

Preserve source sequence while assigning blocks to slides. Do not merge
unrelated workstreams for visual convenience. Repeat table headers when a table
spans slides and keep month/quarter/year values together when they describe one
KPI.

Every page in `design_spec.md §IX` MUST include:

```markdown
- **Source Blocks**: SRC01-B0038-SRC01-B0042
```

Mirror the same mapping in `spec_lock.md ## page_sources`. Add
`## content_mode` exactly as specified in `templates/spec_lock_reference.md`.

Do not create a claim or chart manifest. `page_sources` is the complete handoff:
Executor reads each mapped block and its atomic facts directly from
`source_inventory.json`. Derived formulas and calculated labels are forbidden.
Do not put QA labels such as source coverage or validation status on a slide.

Executor records provenance directly in SVG. Every source-backed text leaf
resolves to exactly one fact through inherited or local metadata:

```xml
<g data-source-ids="SRC01-B0042" data-fact-ids="SRC01-B0042-F01">
  <text>Cosite đạt 43% KH Q3</text>
</g>
```

One fact may span multiple SVG text elements for mechanical line breaking.
Source images use `data-content-kind="source_asset"` and their source block id.
Chart labels, values, tables, and callouts use the same direct fact provenance.
A chart that cannot retain every source token uses an additional table/callout
or another slide.

Run `python3 scripts/faithful_report.py validate-spec <project_path>` and fix all
errors before handing off to Executor. Duplicate mappings are allowed when a
source fact legitimately appears in both overview and detail pages; they remain
visible as warnings.
