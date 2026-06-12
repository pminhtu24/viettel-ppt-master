# Execution Lock

> **⚠️ Skeleton for Strategist — do NOT copy verbatim into a project.** When producing `<project_path>/spec_lock.md`, emit only `##` sections with filled-in `-` data lines. Do NOT carry over any `>` blockquote guidance, HARD-rule notes, or override examples — those are author-time guidance, not runtime data. Every output line must be parseable data.
>
> Machine-readable execution contract. Executor MUST `read_file` this before every SVG page. Values not listed here must NOT appear in SVGs. For design narrative (rationale, audience, style), see `design_spec.md`.
>
> After SVG generation begins, this is the canonical source for color / font / icon / image values. Modifications should go through `scripts/update_spec.py` to keep this file and generated SVGs in sync.

## canvas

- viewBox: 0 0 1280 720
- format: PPT 16:9

> This skill is locked to PPT 16:9: `0 0 1280 720`. Do not emit another canvas, including for `custom_override`.

## brand

- profile: viettel_default
- deep_blue_scope: chart_diagram_icon_only

> Every normal run MUST emit exactly the two lines above. `viettel_default` means the Viettel logo, brand chrome, approved colors, and locked typography remain mandatory even on pages with adaptive composition and no `page_layouts` entry.
>
> Emit `- profile: custom_override` only when the user explicitly says not to use Viettel, names another brand, or supplies an explicit non-Viettel template path. A color, font, mood, or visual-style request alone does not qualify. For `custom_override`, omit `deep_blue_scope` and record the explicit override reason in `design_spec.md`.

## colors

- bg: #FFFFFF
- surface: #F2F2F2
- primary: #EE0033
- chart_deep_blue: #12436D
- text: #000000
- text_secondary: #44494D
- text_tertiary: #999999
- border: #E6E6E6
- success: #28A197
- warning: #F46A25
- chart_neutral: #6B7280
- image_rendering: vector-illustration
- image_palette: cool-corporate

> For `viettel_default`, keep only the approved rows actually used and do not add colors outside this palette. For explicit `custom_override`, replace the section with the override palette.
>
> **Viettel default color lock**: normal runs use Viettel red `#EE0033`, white/approved-gray surfaces, and dark-neutral text. Deep blue `#12436D` may appear only in chart, diagram/infographic, or icon marks. Every deep-blue SVG mark MUST be inside `<g data-viettel-blue-scope="chart|diagram|icon">`; it is forbidden for text, backgrounds, cards, rails, footers, dividers, and decoration.
>
> **`image_rendering` and `image_palette`** — required only when `images` section below contains `ai`-sourced files. Values MUST be valid names from `references/image-renderings/_index.md` and `references/image-palettes/_index.md`. Image_Generator reads these and applies them deck-wide. Omit both rows when the deck has no AI-generated images.

## typography

- font_family: "FS Magistral"
- body: 22
- title: 32
- subtitle: 24
- annotation: 14

> `font_family` is the only family declaration for `viettel_default`; every role inherits it. Do not emit `title_family`, `body_family`, `emphasis_family`, or `code_family` for normal Viettel runs.
>
> **Viettel default for this skill**: keep the single locked family `"FS Magistral"`. Typography is not a user choice in normal runs. Do not introduce FS PF BeauSans Pro, Sarabun, Microsoft YaHei, Arial, Georgia, Consolas, or another design font. Runtime missing-font handling belongs to `scripts/check_fonts.py` and must be reported as `brand fidelity degraded`.
>
> **Weight lock**: FS Magistral Bold (`700`) is mandatory for titles, headers, card/KPI labels, hero/KPI numbers, callouts, and highlighted text. Book/Regular (`400`) is mandatory for body, descriptions, captions, sources, footers, and ordinary chart labels. Medium (`500`) is reserved for secondary subtitles/labels. Do not use `600`, `800`, or `900`.
>
> Sizes (`body` / `title` / etc.) are in px, matching SVG units. `body` is the **required baseline anchor** — all other sizes derive as ratios of it (ramp table: `design_spec_reference.md §IV`).
>
> **Size slots are anchors, not a closed menu.** Common slots (`title` / `subtitle` / `annotation`) cover frequent cases. Add role-specific slots (e.g. `cover_title: 72`, `hero_number: 48`, `chart_annotation: 13`) when needed — common for cover-heavy decks, consulting-style hero numbers, dense pages. Executor may use intermediate sizes as long as the ratio to `body` sits in the role's ramp band.
>
> **⚠️ PPT-safe stack discipline (HARD rule).** PPTX stores one `typeface` per run with no runtime fallback. For explicit non-Viettel overrides, every stack MUST end with a cross-platform pre-installed font: `"Microsoft YaHei", sans-serif` / `SimSun, serif` / `Arial, sans-serif` / `"Times New Roman", serif` / `Consolas, "Courier New", monospace`. The locked Viettel stack is this skill's bundled-brand exception and is validated by font preflight instead.
>
> **Stack length discipline.** Keep the default Viettel family declaration exactly `"FS Magistral"`. For explicit non-Viettel overrides, 3-4 fonts per stack is the sweet spot. Converter only writes the **first** Latin and **first** CJK font into PPTX — everything after is silently dropped. macOS-only families (`Songti SC`, `Menlo`, `Monaco`, `Helvetica`) are auto-mapped to Windows equivalents via `FONT_FALLBACK_WIN` (see `scripts/svg_to_pptx/drawingml_utils.py`); stacking both is redundant.
>
> **Bundled-font exception**: a template may intentionally lock `font_family` to non-preinstalled brand fonts when it also ships a local `fonts/` bundle and the workflow runs `scripts/check_fonts.py` before SVG generation. In that case, keep the exact brand stack in `spec_lock.md`; if the host falls through to a later family, the run must report `brand fidelity degraded` instead of silently pretending the brand font is available.

## text_fit

- card_padding: 20
- chart_label_max_chars: 24
- card_body_max_lines: 3
- kpi_caption_max_lines: 2
- footer_max_chars: 90
- require_wrap_contract: true
- title_zone_bottom: 255

> Strategist: fill only the constraints the deck needs. These values guide Executor text budgeting and make `svg_quality_checker.py` overflow checks actionable. New projects should keep `require_wrap_contract: true`; omit this section only for legacy decks.

## icons

- library: chunk-filled
- brand_library: simple-icons
- inventory: target, bolt, shield, users, chart-bar, lightbulb

> `library` MUST be exactly one of `chunk-filled` / `tabler-filled` / `tabler-outline` / `phosphor-duotone` — mixing is forbidden. `brand_library: simple-icons` is optional; include only when the deck uses real company / product brand marks, otherwise omit. `inventory` lists approved icon names (no library prefix); Executor may only use icons from this list.
>
> **`stroke_width` (stroke-style libraries only)** — required when `library` is stroke-based (currently `tabler-outline`); allowed values `1.5` / `2` / `3`. Executor MUST apply this value to every `<use data-icon="...">` placeholder via `stroke-width`, deck-wide. Omit for non-stroke libraries (`chunk-filled` / `tabler-filled` / `phosphor-duotone`) — ignored there. For heavier weight switch library; do not exceed `3` (at 24×24 strokes merge and the icon stops reading as line art).
>
> Example for stroke-style libraries:
>
> ```
> - library: tabler-outline
> - stroke_width: 2
> - inventory: home, chart-bar, users, bulb
> ```

## images

- cover_bg: images/cover_bg.jpg
- q3_revenue_chart: images/q3_revenue.png | no-crop

> One entry per image file used. Append ` | no-crop` only for images that must not lose pixels (data screenshots, charts, certificates) — Executor will size the container to native ratio and use `preserveAspectRatio="xMidYMid meet"`. Untagged entries default to croppable (`slice`). Remove the section entirely if no images.

## page_rhythm

- P01: anchor
- P02: dense
- P03: breathing
- P04: dense
- P05: dense
- P06: breathing
- P07: anchor

> One entry per page. Key: `P<NN>` (zero-padded, matching `§IX Content Outline` in `design_spec.md`). Value: one of the three rhythm tags. Executor reads per page and applies the tag's layout discipline — breaks the "every page looks the same" pattern.
>
> **Vocabulary** (exactly these three values):
>
> - `anchor` — Structural pages (cover / chapter opener / TOC / ending). Follow the template as-is.
> - `dense` — Information-heavy pages (data, KPIs, comparisons, multi-point lists). Card grids, multi-column layouts, tables, charts all permitted.
> - `breathing` — Low-density pages (single concept, hero quote, big image + caption, section transition). Avoid **multi-card grid layouts** (multiple parallel rounded containers as the primary structure); organize via naked text, dividers, whitespace, or full-bleed imagery. Single rounded elements (hero image corners, callouts, tags, one emphasis block) are fine. Proportions follow information weight — not a preset ratio menu.
>
> **Rhythm follows narrative**: `breathing` pages appear where narrative genuinely pauses — section transitions, a single argument worth standalone emphasis, a deliberate stop after a dense sequence. A data briefing or consulting analysis may legitimately be nearly all `dense` — **do not invent filler pages** to pad rhythm. Validation: every `breathing` page must answer "what independent thing is this page saying?".
>
> **Missing or empty section** → Executor falls back to `dense` for every page (legacy pre-rhythm behavior). Remove the section only for legacy decks; new decks MUST fill it.

## page_backgrounds

- P01: bg_red_corner_sweep
- P03: bg_red_folded_stage
- P06: bg_wave_ribbon_soft
- P07: bg_red_corner_depth

> Optional section-only entries for `brand.profile: viettel_default`. Key: `P<NN>` matching §IX. Value: a background id from `templates/backgrounds/backgrounds_index.json`, without `.svg`.
>
> **Default Viettel policy**: only cover, chapter, section-divider, ending, and low-content breathing pages get a background layer. Dense content, chart, KPI, and table pages MUST omit `page_backgrounds` and use the standard clean Viettel shell.
>
> **Softening rule**: background details should be visually softened with pale fills, low opacity, wide shapes, and gradient-like fades. Do not use SVG `<filter>` / blur effects; they are not PPTX-safe. Keep sharp detail away from the main content/chart area.
>
> **Selection source**: read `templates/backgrounds/backgrounds_index.json`. Match by section/page role, `page_rhythm`, content topic, and `safe_text_zone`. Avoid repeating the same background on adjacent section pages when another suitable option exists.
>
> **Missing entry** → Executor applies no decorative background. This is expected for content-heavy pages.

## page_layouts

- P01: 01_cover
- P03: 02a_chapter
- P04: 03a_content_abstract

> One entry per page **that uses a template SVG**. Key: `P<NN>` matching §IX. Value: the template's SVG basename without extension (e.g., `01_cover`, `03a_content_image_text`) — Executor resolves it to `templates/<chosen_template>/<value>.svg`. Modern templates ship many content-page variants (`03a_content_abstract`, `03b_content_image_text`, `03c_content_three_items` …); the page-type → single-file mapping in `executor-base.md §1` no longer covers them, so this section is the per-page truth.
>
> **No entry for a page** → no layout SVG inheritance. Under `viettel_default`, this means adaptive Viettel composition: content geometry is flexible, while Viettel logo, chrome, colors, typography, and deep-blue scope remain mandatory. Under `custom_override`, it means ordinary free design.
>
> **Hard rule**: Use both `page_layouts` and `page_charts` for the same page only when the layout template is a compatible shell for the chart. Do not assign a conflicting layout just to fill every page: a waterfall chart should not inherit a timeline layout, and KPI cards should not inherit a circle-diagram layout unless that is the intended visual structure. When no compatible layout exists, omit the page from `page_layouts`.
>
> **Whole section omitted** → no pages inherit layout SVGs. Under `viettel_default`, the entire deck still uses adaptive Viettel composition and receives Viettel brand chrome. Under `custom_override`, this is ordinary free design.
>
> **Strategist source**: copy the per-page SVG choices from `design_spec.md §VI Page Roster` (or §IX outline if Roster is absent). Names must match files in `templates/<chosen_template>/` exactly — typos cause silent fallback to adaptive composition.

## page_charts

- P05: bar_chart
- P09: timeline
- P12: quadrant_bubble_scatter

> One entry per page **that adapts a `templates/charts/` chart template**. Key: `P<NN>` matching §IX. Value: chart template basename without `.svg` (must match a key in `templates/charts/charts_index.json`).
>
> **No entry for a page** → no chart on that page (or a chart that did not match any catalog template — Strategist's `no-template-match` fallback). Both cases mean Executor designs the visualization from scratch per `design_spec.md §VII`.
>
> **Whole section omitted** → no data-visualization or structural-pattern pages in this deck. Omit only when `design_spec.md §VII` explicitly says the catalog was read and no page matched, or when all candidate pages are marked `no-template-match`.
>
> **Strategist source**: copy from `design_spec.md §VII Visualization Reference List` — only the rows whose `reference template path` points to a `templates/charts/` file. Pages marked `no-template-match` in §VII MUST NOT appear here.
>
> **Audit rule**: every §VII row with a `templates/charts/<name>.svg` path MUST have an exact `P<NN>: <name>` row here. A deck with numeric charts/KPIs/ranked lists but no `page_charts` section is invalid unless §VII documents `no-template-match` for each such page.

## forbidden

- Mixing icon libraries
- rgba()
- `<style>`, `class`, `<foreignObject>`, `textPath`, `@font-face`, `<animate*>`, `<script>`, `<iframe>`, `<symbol>`+`<use>`
- `<g opacity>` (set opacity on each child element individually)
- HTML named entities in text (`&nbsp;`, `&mdash;`, `&copy;`, `&ndash;`, `&reg;`, `&hellip;`, `&bull;` …) — write as raw Unicode (`—`, `©`, `→`, NBSP, etc.); XML reserved chars `& < > " '` must be escaped as `&amp; &lt; &gt; &quot; &apos;`. See shared-standards.md §1.0
