# {project_name} - Design Spec

> Human-readable design narrative — rationale, audience, style, color choices, content outline. Read once by downstream roles for context.
>
> Machine-readable execution contract: `spec_lock.md` (color / typography / icon / image short form). Executor re-reads `spec_lock.md` before every SVG page to resist context-compression drift. Keep both in sync; on divergence, `spec_lock.md` wins.
>
> **Viettel default brand contract**: every normal run uses PPT 16:9 and `brand.profile: viettel_default`. Keep the Viettel logo/chrome, locked font stack, Viettel red, white/approved-gray surfaces, and dark-neutral text on every page. Deep blue `#12436D` is chart/diagram/icon-only and every such mark must be inside `<g data-viettel-blue-scope="chart|diagram|icon">`. Use `brand.profile: custom_override` only for an explicit hard non-Viettel request; color/font/style requests alone do not unlock the brand.

## I. Project Information

| Item | Value |
| ---- | ----- |
| **Project Name** | {project_name} |
| **Canvas Format** | {canvas_info['name']} ({canvas_info['dimensions']}) |
| **Page Count** | [Filled by Strategist] |
| **Design Style** | {design_style} |
| **Target Audience** | [Filled by Strategist] |
| **Use Case** | [Filled by Strategist] |
| **Created Date** | {date_str} |

---

## II. Canvas Specification

| Property | Value |
| -------- | ----- |
| **Format** | {canvas_info['name']} |
| **Dimensions** | {canvas_info['dimensions']} |
| **viewBox** | `{canvas_info['viewbox']}` |
| **Margins** | [Recommended by Strategist, e.g., left/right 60px, top/bottom 50px] |
| **Content Area** | [Calculated from canvas] |

---

## III. Visual Theme

### Theme Style

- **Style**: {design_style}
- **Theme**: Light reporting theme (locked for `viettel_default`; change only for explicit `custom_override`)
- **Tone**: [Filled by Strategist, e.g., tech, professional, modern, innovative]

### Color Scheme

> For `viettel_default`, use the palette below and delete unused rows rather than inventing replacements. Map compatible user color requests to the nearest approved data/illustration role; they do not add colors or replace Viettel red, white/gray surfaces, or dark-neutral text. Replace this palette only for explicit `custom_override`.

| Role | HEX | Purpose |
| ---- | --- | ------- |
| **Background** | `#FFFFFF` | Page background |
| **Secondary bg** | `#F2F2F2` | Card and section surfaces |
| **Primary** | `#EE0033` | Viettel brand accents and primary data |
| **Deep blue** | `#12436D` | Chart, diagram/infographic, and icon marks only |
| **Body text** | `#000000` | Main titles and body text |
| **Secondary text** | `#44494D` | Captions and annotations |
| **Tertiary text** | `#999999` | Supplementary info and footers |
| **Border/divider** | `#E6E6E6` | Card borders and divider lines |
| **Success** | `#28A197` | Positive indicators and data series |
| **Warning** | `#F46A25` | Warning indicators and data series |
| **Neutral data** | `#6B7280` | Neutral chart series |

> `#12436D` is never a text, background, card, rail, footer, divider, or decorative color. Put each deep-blue mark inside `<g data-viettel-blue-scope="chart|diagram|icon">`.

### AI Image Strategy (fill only when §VIII has `ai` rows)

- **Image Rendering**: [one of the 16 names in `references/image-renderings/_index.md`, e.g. `vector-illustration`]
- **Image Palette**: [one of the 10 names in `references/image-palettes/_index.md`, e.g. `cool-corporate`]

> Strategist: lock these once per deck in h.5; every AI image inherits them. Cross-check the rendering × palette compatibility matrix in `image-palettes/_index.md` — avoid `✗` combinations. Leave the section out entirely if §VIII has no `ai` rows.

### Gradient Scheme (explicit `custom_override` only, using SVG syntax)

> Omit this section for `viettel_default`; normal Viettel pages use flat white/gray reporting surfaces and flat brand/data colors.

```xml
<!-- Title gradient -->
<linearGradient id="titleGradient" x1="0%" y1="0%" x2="100%" y2="100%">
  <stop offset="0%" stop-color="#[primary]"/>
  <stop offset="100%" stop-color="#[secondary accent]"/>
</linearGradient>

<!-- Background decorative gradient (note: rgba forbidden, use stop-opacity) -->
<radialGradient id="bgDecor" cx="80%" cy="20%" r="50%">
  <stop offset="0%" stop-color="#[primary]" stop-opacity="0.15"/>
  <stop offset="100%" stop-color="#[primary]" stop-opacity="0"/>
</radialGradient>
```

---

## IV. Typography System

### Font Plan

> **Viettel default for this skill.** All normal Viettel roles MUST use the single locked family `"FS Magistral"`. This is informational, not a user-selectable typography option. Do not propose or record alternative font combinations. Create hierarchy through size, the locked weights, spacing, and color.
>
> **Viettel weight lock.** Title / Header / Emphasis use FS Magistral Bold (`700`): cover/chapter/page titles, section/card headers, KPI/hero numbers, callouts, and highlighted text. Body / Caption use Book/Regular (`400`). Secondary subtitles/labels may use Medium (`500`). Do not use `600`, `800`, or `900`.
>
> **⚠️ PPT-safe stack discipline (HARD rule).** PPTX stores a single `typeface` per run — no runtime fallback. For explicit non-Viettel overrides, every stack MUST end with a cross-platform pre-installed font: `"Microsoft YaHei", sans-serif` / `SimSun, serif` / `Arial, sans-serif` / `"Times New Roman", serif` / `Consolas, "Courier New", monospace`. The locked Viettel stack is this skill's bundled-brand exception and is validated by `scripts/check_fonts.py`.

**Typography direction**: Viettel brand sans — locked family: FS Magistral; locked weights: `400` / `500` / `700`

| Role | Family | Weight | Usage |
| ---- | ------ | ------ | ----- |
| **Title / Header** | `"FS Magistral"` | Bold (`700`) | Cover/chapter/page titles, section/card headers |
| **Emphasis** | `"FS Magistral"` | Bold (`700`) | KPI/hero numbers, callouts, highlighted text |
| **Body** | `"FS Magistral"` | Book/Regular (`400`) | Body copy, descriptions, ordinary chart labels |
| **Secondary** | `"FS Magistral"` | Medium (`500`) | Secondary subtitles/labels only |
| **Caption** | `"FS Magistral"` | Book/Regular (`400`) | Sources, footers, page numbers |

**SVG / spec lock family value**: `"FS Magistral"` for every role. In normal Viettel `spec_lock.md`, emit only `font_family`; do not emit redundant per-role family overrides.

> **Stack ordering for explicit non-Viettel overrides only**: CSS `font-family` falls back font-by-font (not char-by-char). The normal Viettel flow has one family and no ordering choice. For custom overrides:
> - `Georgia, "Microsoft YaHei", serif` → Latin in Georgia (elegant serif), CJK falls through to Microsoft YaHei. **Use when Latin typography is the primary design statement** (academic / editorial / Latin-heavy covers).
> - `"Microsoft YaHei", Georgia, serif` → Everything in Microsoft YaHei (Latin uses YaHei's Latin glyphs — a different design tone). **Use when the deck is CJK-primary and Latin is incidental**.
>
> The converter (`drawingml_utils.py parse_font_family`) maps these to PPTX `<a:latin>` / `<a:ea>` regardless of order — but browser preview and SVG native rendering reflect stack order. Pick the order matching your design intent.

> **Bundled brand fonts**: when a template ships a local `fonts/` bundle, keep the intended brand stack in `design_spec.md` / `spec_lock.md` exactly as designed, even if the host may not have those fonts yet. The runtime workflow must then run `scripts/check_fonts.py` after `spec_lock.md` generation. If the leading family is absent on the host, execution continues with fallback rendering but MUST report `brand fidelity degraded`; installation from the local bundle is opt-in and requires explicit user approval.

### Font Size Hierarchy

> **Ramp discipline, not a fixed menu.** `body` is the single anchor; every other size is a ratio of it. Each row below gives the role's allowed ratio band — Executor may pick any px value inside the band (e.g., 40px hero number, 13px chart annotation, 72px cover headline) without pre-declaring intermediates in `spec_lock.md`.
> **Unit**: px uniformly (SVG native) to avoid pt/px conversion errors.
> **Baseline selection**: drive by **content density**, not design style.

**Baseline**: Body font size = [fill in]px (any reasonable integer — `18` and `24` are most common; `16` for chart-heavy, `20`/`22` for medium density, `28-32` for poster / cover decks are all valid. Drive by content density.)

| Purpose | Ratio to body | Example @ body=24 (relaxed) | Example @ body=18 (dense) | Weight |
| ------- | ------------- | --------------------------- | ------------------------- | ------ |
| Cover title (hero headline) | 2.5-5x | 60-120px | 45-90px | Bold (`700`) |
| Chapter / section opener | 2-2.5x | 48-60px | 36-45px | Bold (`700`) |
| Page title | 1.5-2x | 36-48px | 27-36px | Bold (`700`) |
| Hero number (consulting KPIs) | 1.5-2x | 36-48px | 27-36px | Bold (`700`) |
| Section/card header | 1-1.3x | 24-31px | 18-23px | Bold (`700`) |
| Subtitle | 1.2-1.5x | 29-36px | 22-27px | Medium (`500`) |
| **Body content** | **1x** | **24px** | **18px** | Book/Regular (`400`) |
| Annotation / caption | 0.7-0.85x | 17-20px | 13-15px | Book/Regular (`400`) |
| Page number / footnote | 0.5-0.65x | 12-16px | 9-12px | Book/Regular (`400`) |

> The two px columns are illustrations for common baselines. For any other `body` value, multiply by each row's ratio — the checker (`svg_quality_checker._check_spec_lock_drift`) reads the live `body` from `spec_lock.md` and applies the bands, so no code change is needed for a different baseline.

> Sizes outside **every** band remain forbidden — surface the need and extend `spec_lock.md typography` (e.g., `cover_title: 96`) rather than invent a one-off value.

---

## V. Layout Principles

### Page Structure

- **Header area**: [Height and content description]
- **Content area**: [Height and content description]
- **Footer area**: [Height and content description]

### Layout Pattern Library (combine or break as content demands)

> **Principle — proportion follows information weight, not preset ratios.** The table below is a pattern library, not a menu. Combine two patterns on one page, break the grid entirely for a `breathing` page, or propose a pattern not listed when content calls for it. Defaulting every page to a symmetric grid produces the "AI-generated" look — vary intentionally.

| Pattern | Suitable Scenarios |
| ------- | ----------------- |
| **Single column centered** | Covers, conclusions, key points |
| **Symmetric split (5:5)** | Comparisons where two sides carry equal weight |
| **Asymmetric split (3:7 / 2:8)** | One side dominates — data chart vs. brief takeaway, image vs. caption |
| **Top-bottom split** | Processes, timelines, ultra-wide image + text |
| **Three/four column cards** | Feature lists, parallel points, team intros |
| **Matrix grid (2×2)** | Two-axis classifications, strategic quadrants |
| **Z-pattern / waterfall** | Storytelling, case studies — content blocks alternate left/right guiding the eye |
| **Center-radiating** | Core concept + surrounding nodes, ecosystem / stakeholder maps |
| **Full-bleed + floating text** | `breathing` / feature pages — image fills canvas, text floats with opacity overlay |
| **Figure-text overlap** | Hero moments — headline / big number sits over or against an image edge instead of beside it |
| **Negative-space-driven** | A single element in 40-60% whitespace — lets one idea land with weight |

### Spacing Specification

> Spacing defaults depend on **container type**. Cards are one option, not the universal default. Tables below split by container type; a page may consult only one set (e.g., a `breathing` page with no cards uses only universal + non-card entries).

**Universal** (any container type):

| Element | Recommended Range | Current Project |
| ------- | ---------------- | --------------- |
| Safe margin from canvas edge | 40-60px | [fill in] |
| Content block gap | 24-40px | [fill in] |
| Icon-text gap | 8-16px | [fill in] |

**Card-based layouts** (consult only when the page uses cards — typically `dense` pages with parallel containers):

| Element | Recommended Range | Current Project |
| ------- | ---------------- | --------------- |
| Card gap | 20-32px | [fill in] |
| Card padding | 20-32px | [fill in] |
| Card border radius | 8-16px | [fill in] |
| Single-row card height | 530-600px | [fill in] |
| Double-row card height | 265-295px each | [fill in] |
| Three-column card width | 360-380px each | [fill in] |

**Non-card containers** (naked text blocks / full-bleed imagery / divider-separated content — typical for `breathing` pages or minimalist designs):

- Vertical rhythm carried by **whitespace**, not gutters — block gaps run wider than card gaps since there's no container edge to separate content.
- **Line-height**: 1.4-1.6× body font size.
- **Full-bleed text placement**: inset text away from the image's focal points; legibility over photographic backgrounds typically needs a gradient or opacity overlay.
- **Content width** is driven by reading comfort and image composition, not a card grid slot — don't back-compute "column width" when there's no column.

### Text Fit Budget

> Strategist MUST define text fit constraints for the deck. Executor uses these as the budget before writing SVG; `svg_quality_checker.py` enforces overflow risks.

| Slot | Max lines | Max chars per line | Min font | Required handling |
| ---- | --------- | ------------------ | -------- | ----------------- |
| KPI value | [1] | [e.g., 8-12] | [fill] | Number and unit must both fit the card; move unit below when needed |
| KPI caption | [1-2] | [fill] | [fill] | Use separate `<text>` lines or `data-box` |
| Card body | [2-4] | [fill] | [fill] | Use `data-box="x,y,w,h" data-wrap="true"` or manual lines |
| Chart label | [1-2] | [fill] | [fill] | Shorten label before shrinking below annotation size |
| Footer/source | [1] | [fill] | [fill] | Must not collide with page badge or content above |

**Overflow policy**:

- Text inside cards, tables, chart panels, callouts, and KPI blocks requires a wrap contract: separate `<text>` lines or `data-box + data-wrap`.
- If content exceeds the budget, split the slide or shorten lower-priority text. Do not add more cards or shrink body text below the stated minimum.
- Large chart/data marks must stay outside the title/header zone. If a chart needs vertical space, reduce title density or split the page.

---

## VI. Icon Usage Specification

### Source

- **Built-in icon library**: `templates/icons/` (11,600+ icons across five libraries; see `templates/icons/README.md`)
- **Usage method**: SVG placeholder `<use data-icon="library/icon-name" .../>`; Design Spec should list approved `library/icon-name` entries for Executor.

### Recommended Icon List (fill as needed)

| Purpose | Icon Path | Page |
| ------- | --------- | ---- |
| [example] | `chunk-filled/circle-checkmark` | Slide XX |

---

## VII. Visualization Reference List

> Strategist MUST read `templates/charts/charts_index.json` and list every page that maps to a chart-library template (data charts OR structural patterns — team rosters, agendas, frameworks, etc.). Single combined table — `summary-quote` column is the anti-fabrication audit, `path` + `usage` columns serve Executor lookup.
>
> For data-heavy reports, executive dashboards, KPI summaries, ranked lists, tables, timelines, process flows, or recommendation lists, this section is expected to be non-empty unless every candidate page is explicitly marked `no-template-match` with a reason.

Catalog read: 71 templates

| Page | Template | Path | Summary-quote (verbatim from `charts_index.json`) | Usage |
| ---- | -------- | ---- | ------------------------------------------------- | ----- |
| P05 | grouped_bar_chart | `templates/charts/grouped_bar_chart.svg` | "Pick for 2-4 series side-by-side across the same categories (e.g. YoY/QoQ). Skip if showing composition within each category (use stacked_bar_chart)." | YoY revenue comparison by product line |

**Runners-up considered** (3 entries minimum, drawn from real second-best matches in this deck):

- `<key_A>` | rejected for P05: `<reason citing this deck's specifics>`
- `<key_B>` | rejected for P##: `<reason>`
- `<key_C>` | rejected for P##: `<reason>`

> **Audit rule**: `Summary-quote` must be copy-pasted verbatim — paraphrasing breaks the audit. Every template name listed must `grep` cleanly inside `charts_index.json` (so misspellings/inventions fail). If fewer than 3 viz pages exist, list what exists and note "fewer than 3 viz pages"; runners-up still required for each page that does exist.
>
> **Spec lock handoff rule**: every row whose `Path` starts with `templates/charts/` MUST be copied into `spec_lock.md ## page_charts` using the same page key and chart basename. If a page is marked `no-template-match`, it MUST NOT appear in `page_charts`.

---

### Viettel Section Background Assignment (viettel_default)

> For `brand.profile: viettel_default`, Strategist MUST read `templates/backgrounds/backgrounds_index.json` and assign background ids only to cover, chapter, section-divider, ending, and low-content breathing pages. Dense content, chart, KPI, and table pages MUST omit `page_backgrounds` so the standard clean shell stays behind content.
>
> Softness rule: choose backgrounds that are already visually softened by pale fills, low opacity, wide geometry, and calm safe zones. Do not request SVG filters or blur effects.

| Page | Background ID | Category | Intensity | Reason |
| ---- | ------------- | -------- | --------- | ------ |
| P01 | `bg_red_corner_sweep` | cover | high | Cover needs stronger brand presence; title sits in the calm left zone |
| P03 | `bg_red_folded_stage` | brand | high | Section divider can carry a stronger visual field because content is sparse |

> **Spec lock handoff rule**: every row MUST be copied into `spec_lock.md ## page_backgrounds` with the same page key and background id. Content-heavy pages MUST NOT appear in `page_backgrounds`.

---

## VIII. Image Resource List (if needed)

| Filename | Dimensions | Ratio | Purpose | Type | Layout pattern | Acquire Via | Status | Reference | text_policy | page_role |
| -------- | --------- | ----- | ------- | ---- | -------------- | ----------- | ------ | --------- | ----------- | --------- |
| cover_bg.png | {canvas_info['dimensions']} | [ratio] | Cover background | Background | #1 full-bleed background with floating title + #29 two-stop scrim | ai | Pending | [subject + intent + composition, no style/HEX] | | |

> **Layout pattern column is MANDATORY** — value is one or more `#<id> <name>` joined by ` + ` drawn verbatim from [`references/image-layout-patterns.md`](../references/image-layout-patterns.md) (Primary + optional Modifiers). Empty cells, paraphrased names, or invented ids invalidate the row. See `strategist.md §h` GATE for the three-layer requirement (read → produce → image-as-canvas coverage).

**Status**:

- **Pending** — needs AI generation or web sourcing
- **Existing** — user-supplied, place in `images/`
- **Placeholder** — not yet processed, use dashed border in SVG

**Type** (narrative shorthand — kept for backward compatibility; Image_Generator infers its 9-way internal-composition type from `Purpose`):

- **Background** — full-page (covers / chapters); reserve text area
- **Photography** — real scenes, people, products, architecture
- **Illustration** — flat / vector / cartoon / concept diagrams
- **Diagram** — flowcharts, architecture diagrams, concept maps
- **Decorative** — partial decorations, textures, borders, dividers

**text_policy** (`ai` rows only; leave blank for default):

- *blank / `none`* — image carries no text; SVG overlays labels
- `embedded` — image contains in-artwork text: decorative lettering, a designed title, or hand-lettered keywords. Body copy / data points / long quotes never go inside the image regardless. English text renders most reliably; CJK characters fail in most models

**page_role** (`ai` rows only; leave blank for default):

- *blank / `local`* — image is a region block on an SVG page
- `hero_page` — image is the page's main voice; SVG overlay is minimal or empty. Use on covers, chapter dividers, mood transitions, single-number data heroes, closing quotes. Same rendering and palette as the rest of the deck regardless

**Reference grammar** (`ai` rows): write **subject + intent + composition** only. Do NOT repeat style words ("flat design", "modern") or HEX values — both are already locked deck-wide by `design_spec §III AI Image Strategy` (rendering + palette) and `§III Color Scheme` (HEX triplet). Image_Generator's prompt assembler injects them.

---

## IX. Content Outline

### Part 1: [Chapter Name]

#### Slide 01 - Cover

- **Layout**: Full-screen background image + centered title
- **Title**: [Main title]
- **Subtitle**: [Subtitle]
- **Info**: [Author / Date / Organization]

#### Slide 02 - [Page Name]

- **Layout**: [Choose a pattern from §V, combine two, or break the grid as the content demands]
- **Title**: [Page title]
- **Visualization**: [visualization_type] (see VII. Visualization Reference List)
- **Content**:
  - [Point 1]
  - [Point 2]
  - [Point 3]

> **Visualization field**: add only when the page has data visualization or structured infographic elements. Type must be listed in §VII.

---

[Strategist continues adding more pages based on source document content and page count planning...]

---

## X. Speaker Notes Requirements

One speaker note file per page, saved to `notes/`:

- **Filename**: match SVG name (e.g., `01_cover.md`)
- **Content**: script key points, timing cues, transition phrases

---

## XI. Technical Constraints Reminder

### SVG Generation Must Follow:

1. viewBox: `{canvas_info['viewbox']}`
2. Background uses `<rect>` elements
3. Text wrapping uses separate `<text>` lines or `data-box + data-wrap` (`<foreignObject>` FORBIDDEN)
4. Transparency uses `fill-opacity` / `stroke-opacity`; `rgba()` FORBIDDEN
5. FORBIDDEN: `mask`, `<style>`, `class`, `foreignObject`
6. FORBIDDEN: `textPath`, `animate*`, `script`
7. Text characters: write typography & symbols as raw Unicode (em dash `—`, en dash `–`, `©`, `®`, `→`, NBSP, etc.); HTML named entities (`&nbsp;`, `&mdash;`, `&copy;`, `&reg;` …) are FORBIDDEN. XML reserved chars in text MUST be escaped as `&amp;` `&lt;` `&gt;` `&quot;` `&apos;` (e.g. `R&amp;D`, `error &lt; 5%`). See shared-standards.md §1.0
7. `marker-start` / `marker-end` conditionally allowed: `<marker>` must be in `<defs>`, `orient="auto"`, shape must be triangle / diamond / circle (see shared-standards.md §1.1)
8. `clipPath` conditionally allowed **only on `<image>` elements**: `<clipPath>` in `<defs>`, single shape child (circle / ellipse / rect with rx,ry / path / polygon). Do NOT apply to shapes / groups / text — draw the target geometry directly with the matching native element (`<circle>` / `<ellipse>` / `<rect rx>` / `<polygon>` / `<path>`). See shared-standards.md §1.2

### PPT Compatibility Rules:

- `<g opacity="...">` FORBIDDEN (group opacity); set on each child element individually
- Image transparency uses overlay mask layer (`<rect fill="bg-color" opacity="0.x"/>`)
- Inline styles only; external CSS and `@font-face` FORBIDDEN
