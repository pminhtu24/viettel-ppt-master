# Chart SVG Style Guide

> This document defines the visual specifications for all SVG chart templates under `templates/charts/`.  
> Any new or modified charts **must** adhere to these standards to ensure visual consistency across the entire library.

## 0. Upstream Specification Reference

This document is the aesthetic and implementation specification **specifically for chart templates**. All charts must also comply with the project-level common technical constraints:

> **[`references/shared-standards.md`](../../references/shared-standards.md)** — SVG Banned Features Blacklist, PPT Compatibility Alternatives, Canvas Format, Inline tspan Rules, Grouping Specifications, Shadow/Overlay Techniques, and Post-processing Pipeline.

The following sections extract the items from `shared-standards.md` that are most closely related to chart templates. For full details (such as marker conditional constraints, clipPath conditional constraints, arc path calculation formulas, etc.), please consult the upstream document.

---

## 1. Color System (Tailwind CSS Palette)

### 1.1 Typography Colors

| Purpose                  | HEX Color | Tailwind Token | Example                             |
| ------------------------ | --------- | -------------- | ----------------------------------- |
| **Main Title**           | `#0F172A` | Slate 900      | Main chart title                    |
| **Numeric Label**        | `#0F172A` | Slate 900      | Numbers on top of bars, key metrics |
| **Subtitle**             | `#64748B` | Slate 500      | Dates, unit descriptions            |
| **Axis Label**           | `#64748B` | Slate 500      | X/Y axis scale values               |
| **Axis Title / Legend**  | `#475569` | Slate 600      | "Annual Salary ($k)", legend text   |
| **Data Source**          | `#94A3B8` | Slate 400      | Source description at the bottom    |
| **Footnote / Muted Tip** | `#CBD5E1` | Slate 300      | "Adjustable per stage"              |

### 1.2 Theme Colors (Data Series)

| Color Name  | Primary   | Dark (Gradient End) | Purpose                                             |
| ----------- | --------- | ------------------- | --------------------------------------------------- |
| **Blue**    | `#3B82F6` | `#2563EB`           | Series 1 (Default preferred)                        |
| **Emerald** | `#10B981` | `#059669`           | Series 2                                            |
| **Amber**   | `#F59E0B` | `#D97706`           | Series 3                                            |
| **Violet**  | `#8B5CF6` | `#7C3AED`           | Series 4                                            |
| **Rose**    | `#FB7185` | `#E11D48`           | Series 5 / Warning                                  |
| **Pink**    | `#EC4899` | `#BE185D`           | Comparison group (e.g., female in butterfly charts) |

> Radial gradients (e.g., bubble charts) use bright variants: `#60A5FA`, `#34D399`, `#FBBF24`, `#A78BFA`, `#FB7185`.

### 1.3 Semantic Colors

| Purpose                 | HEX Color | Description |
| ----------------------- | --------- | ----------- |
| Target Met / Positive   | `#10B981` | Emerald 500 |
| Warning / Neutral       | `#F59E0B` | Amber 500   |
| Target Unmet / Negative | `#EF4444` | Red 500     |
| Outlier Annotation      | `#F43F5E` | Rose 500    |

### 1.4 UI Auxiliary Colors

| Purpose                      | HEX Color              | Description                 |
| ---------------------------- | ---------------------- | --------------------------- |
| **Axis Line**                | `#94A3B8`              | Slate 400, stroke-width="2" |
| **Grid Line**                | `#E2E8F0` or `#E0E0E0` | stroke-dasharray="4,4"      |
| **Center Divider**           | `#CBD5E1`              | e.g., quadrant crosshairs   |
| **Card Background**          | `#F8FAFC` / `#F8F9FA`  | Slate 50                    |
| **Card Stroke**              | `#E2E8F0`              | Slate 200                   |
| **Row Divider**              | `#F1F5F9`              | Slate 100 (extremely light) |
| **Tint Background** (Blue)   | `#EFF6FF`              | Blue 50                     |
| **Tint Background** (Green)  | `#ECFDF5`              | Emerald 50                  |
| **Tint Background** (Red)    | `#FFF1F2`              | Rose 50                     |
| **Tint Background** (Yellow) | `#FFFBEB`              | Amber 50                    |

---

## 2. Typography Specification

### 2.1 Font Stack

```
font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif"
```

- For pure English scenarios, `'PingFang SC', 'Microsoft YaHei'` can be omitted.
- **Banned**: `@font-face`, external fonts, and `<style>` tags.

### 2.2 Font Size Hierarchy

| Level   | Size      | font-weight  | Purpose                            |
| ------- | --------- | ------------ | ---------------------------------- |
| H1      | `34px`    | `bold` (700) | Main chart title                   |
| H2      | `22px`    | `600`        | Area title (e.g., "Detailed Data") |
| Body L  | `18-20px` | `600`        | Key values, percentages            |
| Body M  | `15-16px` | `600`        | Data labels, category names        |
| Body S  | `14px`    | Normal       | Subtitles, legends, sources        |
| Caption | `12-13px` | Normal       | Axis scales, annotations           |

> **Minimum font size limit: 12px**. No text elements may be smaller than 12px.

### 2.3 `<tspan>` Requirement

All text content in `<text>` elements **must** be wrapped in `<tspan>`:

```xml
<!-- Correct -->
<text x="60" y="80" font-size="34" fill="#0F172A">
    <tspan>Chart Title</tspan>
</text>

<!-- Incorrect -->
<text x="60" y="80" font-size="34" fill="#0F172A">Chart Title</text>
```

### 2.4 Inline Formatting Rules (shared-standards SS4)

**Single logical line = Single `<text>`**. When multiple colors or weights are needed within the same line, use inline `<tspan>` elements. **Do not** use multiple adjacent `<text>` elements:

```xml
<!-- Correct: One text frame, three runs -->
<text x="100" y="200" font-size="24" fill="#333333">
  Achieve <tspan fill="#3B82F6" font-weight="bold">10x</tspan> efficiency gain
</text>

<!-- Incorrect: Three independent text frames, cannot be edited as one line in PPT -->
<text x="100" y="200">Achieve </text>
<text x="160" y="200" fill="#3B82F6">10x</text>
<text x="240" y="200"> efficiency gain</text>
```

> Inline `<tspan>` elements **must not** carry `x`, `y`, or `dy` attributes; otherwise, post-processing will split them into independent text frames. `dx` is safe to use for fine-tuning character spacing.

### 2.5 Data Highlighting Default Behavior

Key data text in charts should be highlighted by default:

- **Numerical Results** — percentages, multipliers, amounts → `<tspan fill="ThemeColor" font-weight="bold">`
- **Comparisons** — increase/decrease, target met/unmet → Semantic colors (Green/Red)
- **Do Not Highlight** — conjunctions, common verbs, structural text (axis labels, legends, page numbers)

---

## 3. Shadow Filters

`<filter>` itself is allowed and is the recommended official path for PPT shadows/glows (see the explanation in the "Banned List" below). This section standardizes the shadow primitive write-up by using the `feFlood` approach. It **prohibits** using `<feComponentTransfer>` inside `<filter>`:

```xml
<filter id="chartShadow" x="-15%" y="-15%" width="130%" height="130%">
    <feGaussianBlur in="SourceAlpha" stdDeviation="2-4"/>
    <feOffset dx="0" dy="1-3" result="offsetBlur"/>
    <feFlood flood-color="#0F172A" flood-opacity="0.08-0.15" result="shadowColor"/>
    <feComposite in="shadowColor" in2="offsetBlur" operator="in" result="shadow"/>
    <feMerge>
        <feMergeNode in="shadow"/>
        <feMergeNode in="SourceGraphic"/>
    </feMerge>
</filter>
```

### Parameter Reference

| Scenario                       | stdDeviation | dy  | flood-opacity |
| ------------------------------ | ------------ | --- | ------------- |
| Heavy elements (arrows, cards) | 4-6          | 2-4 | 0.12-0.15     |
| Medium elements (bars, boxes)  | 2-3          | 1-2 | 0.10-0.15     |
| Light elements (bottom cards)  | 4-6          | 2-4 | 0.06-0.08     |

### Banned List

- `flood-color="#000000"` → must use `#0F172A`
- `<feComponentTransfer>` + `<feFuncA slope=...>` → replace with `<feFlood flood-color flood-opacity>`
- `flood-opacity > 0.20` → shadow is too heavy; max is 0.15-0.20

> **What is banned is the sub-element, not the `<filter>` itself.** `<filter>` is allowed by PPT Master and is the official path for shadows/glows (see [`shared-standards.md`](../../references/shared-standards.md) §1 which does not blacklist filter, and §6 which lists filter shadow as the official implementation of drop-shadow). The converter [`svg_to_pptx/drawingml_styles.py`](../../scripts/svg_to_pptx/drawingml_styles.py) actively maps `feGaussianBlur` + `feOffset` + `feFlood` + `feComposite` + `feMerge` (as well as the shorthand `feDropShadow`) into DrawingML `<a:outerShdw>`.
>
> The reason for banning `feComponentTransfer/feFuncA(slope)` individually: **it can physically only adjust transparency, not carry color**. When the converter reads `feFuncA slope`, it only treats it as alpha, keeping the color field at the default `'000000'`. The shadow color looks normal in the SVG (since SourceAlpha itself is black), but after exporting to PPTX, the shadow color will be locked to pure black `#000000`, creating a visible warm/cool color discrepancy with other cards on the same page using `feFlood flood-color="#0F172A"`.
>
> In short: **using filters is fine, but the primitives must explicitly express "color"; primitives that can only express "transparency" are banned.**

### Shadow Usage Principles (shared-standards SS6)

> **Shadow is an aesthetic choice, not a default treatment.** Restraint, rather than abundance, creates a "designed" feel. "Shadow felt rather than seen" is a high-end aesthetic standard.

**Should have shadow**: Cards floating above photos/colored panels, the unique primary CTA, overlays (tooltips, callouts).

**Should not have shadow**: Background panels/dividers, peer cards in a grid, containers that already have borders/gradients, body paragraph containers, decorative lines/icons, dark backgrounds (black shadows are invisible).

**Per-page Budget**: Up to 2-3 shadowed elements. When a 4th element needs a shadow, remove the shadow from an existing one first.

**Unified Light Source**: All `feOffset` elements on the same page must share the same `dx`/`dy` direction (default `dx=0`, `dy=positive value` for light coming from above).

**Two-tier Elevation Maximum**:

| Tier               | Scenario                                                | dy   | stdDeviation | flood-opacity |
| ------------------ | ------------------------------------------------------- | ---- | ------------ | ------------- |
| Ground (No shadow) | Backgrounds, peer grid cards, dividers, body containers | —    | —            | —             |
| Resting            | Cards on photos/panels, secondary callouts              | 2-4  | 4-8          | 0.06-0.10     |
| Raised             | Primary CTA, focus/recommended cards, overlays          | 6-10 | 10-16        | 0.12-0.20     |

**Do Not Stack**: Shadow + border + rounded corner + gradient fill appearing together = instant template look. The visual "look at me" budget of a container is small; choose just one.

---

## 4. Gradient Specification

### 4.1 Linear Gradient (Column / Bar Charts)

```xml
<linearGradient id="barGrad1" x1="0%" y1="0%" x2="0%" y2="100%">
    <stop offset="0%" style="stop-color:#3B82F6;stop-opacity:1" />
    <stop offset="100%" style="stop-color:#2563EB;stop-opacity:1" />
</linearGradient>
```

- Direction: Light to dark (top-to-bottom or left-to-right).
- Each gradient ID should be semantic: `barGrad1`, `leftGrad`, `actualBarBlue`.

### 4.2 Radial Gradient (Bubble Charts)

```xml
<radialGradient id="bubbleGrad1" cx="30%" cy="30%">
    <stop offset="0%" style="stop-color:#60A5FA;stop-opacity:0.9" />
    <stop offset="100%" style="stop-color:#2563EB;stop-opacity:0.7" />
</radialGradient>
```

- Highlight positioned towards the top-left (`cx="30%" cy="30%"`).
- Outer opacity reduced to 0.7 to create a sense of translucency.

---

## 5. Structural Specification

### 5.1 Layer Grouping (shared-standards SS4 Grouping)

Use `<g id="...">` for semantic grouping to make it easier to manipulate/animate individual components in PPT:

```xml
<g id="chartArea">        <!-- Main Chart Body -->
    <g id="bar-1">...</g>  <!-- Independent group for each data element -->
    <g id="bar-2">...</g>
</g>
<g id="legend">            <!-- Legend Area -->
    <g id="legend-high">...</g>
</g>
<g id="detailList">        <!-- Detail Panel -->
    <g id="list-items">
        <g id="item-1">...</g>
    </g>
</g>
```

**Grouping Unit Reference** (from `shared-standards.md`):

| Grouping Unit      | Contains                                                       |
| ------------------ | -------------------------------------------------------------- |
| Card / Panel       | Background rect + shadow (if applicable) + icon + title + body |
| Process Step       | Number circle + icon + label + description                     |
| List Item          | Bullet / number + icon + title + description                   |
| Icon-Text Combo    | Icon element + adjacent label                                  |
| Page Header        | Title + subtitle + decoration                                  |
| Decorative Cluster | Related decorative shapes (rings, spheres, dots)               |

**Naming Convention**: Use descriptive `id`s (such as `card-1`, `step-discover`, `header`, `footer`).

> Only `<g opacity="...">` is banned (see SS2). Structural `<g>` is required.

### 5.2 viewBox

Fixed to `0 0 1280 720` (PPT 16:9), must not be modified.

### 5.3 Background

The first line must always be a white full-screen background:

```xml
<rect width="1280" height="720" fill="#FFFFFF"/>
```

### 5.4 Data Source

Located at the bottom of the page, using a fixed format:

```xml
<text x="60" y="695" font-family="..." font-size="14" fill="#94A3B8">
    <tspan>Source: XXX</tspan>
</text>
```

---

## 6. SVG Banned Features & Compatibility (shared-standards SS1-2)

### 6.1 Absolute Blacklist

| Banned Feature                                                                            | Alternative                                                        |
| ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| HTML named entities (`&nbsp;` `&mdash;` `&copy;` `&ndash;` `&reg;` `&hellip;` `&bull;` …) | Write raw Unicode characters directly (`—` `–` `©` `®` `→` NBSP …) |
| Bare `& < > " '` in text or attributes                                                    | Must write XML entities `&amp;` `&lt;` `&gt;` `&quot;` `&apos;`    |
| `<style>` / `class`                                                                       | Inline attributes (`id` inside `<defs>` is legal)                  |
| `<foreignObject>`                                                                         | `<text>` + `<tspan>`                                               |
| `mask`                                                                                    | Overlay mask rectangles / gradient overlays                        |
| `<symbol>` + `<use>`                                                                      | Write out full elements directly                                   |
| `textPath`                                                                                | Align `<text>` manually                                            |
| `@font-face`                                                                              | System font stack                                                  |
| `<animate*>` / `<set>`                                                                    | None (animations are handled on the PPT side)                      |
| `<script>` / event attributes                                                             | None                                                               |
| `<iframe>`                                                                                | None                                                               |

### 6.2 PPT Compatibility Alternatives

| Banned Syntax                  | Correct Alternative                                                      |
| ------------------------------ | ------------------------------------------------------------------------ |
| `fill="rgba(255,255,255,0.1)"` | `fill="#FFFFFF" fill-opacity="0.1"`                                      |
| `<g opacity="0.2">...</g>`     | Set `fill-opacity` / `stroke-opacity` individually on each child element |
| `<image opacity="0.3"/>`       | Overlay a `<rect fill="BackgroundColor" opacity="0.7"/>` after the image |

### 6.3 Conditionally Allowed Features

| Feature                       | Condition                                                                     | Conversion Result                         |
| ----------------------------- | ----------------------------------------------------------------------------- | ----------------------------------------- |
| `marker-start` / `marker-end` | `<marker>` inside `<defs>`, `orient="auto"`, shape is triangle/diamond/circle | DrawingML `<a:headEnd>` / `<a:tailEnd>`   |
| `clipPath` on `<image>`       | `<clipPath>` inside `<defs>`, single child element, **used only on image**    | DrawingML `<a:prstGeom>` / `<a:custGeom>` |
| `stroke-dasharray`            | Use presets: `4,4` / `2,2` / `8,4` / `8,4,2,4`                                | PPTX `<a:prstDash>`                       |
| `text-decoration`             | `underline` / `line-through`                                                  | PPTX native text formatting               |
| `transform="rotate(...)"`     | Supported across all element types                                            | PPTX `<a:xfrm rot="...">`                 |

> See [`shared-standards.md`](../../references/shared-standards.md) SS1.1 (marker constraints) and SS1.2 (clipPath constraints) for full conditional constraints.

### 6.4 Dashed Line Preset Mapping

| SVG Value | PPTX Preset   | Best For                             |
| --------- | ------------- | ------------------------------------ |
| `4,4`     | Dash          | General dashed lines, dividers       |
| `2,2`     | Dot (sysDot)  | Placeholder outlines, fine borders   |
| `8,4`     | Long dash     | Timeline connections, process arrows |
| `8,4,2,4` | Long dash-dot | Technical drawings, dimension lines  |

---

## 7. Legacy Color Mapping Lookup Table

When maintaining legacy templates, use the following mapping table for quick replacements:

| Legacy Color (Material/Flat) | →   | New Color (Tailwind)  | Role           |
| ---------------------------- | --- | --------------------- | -------------- |
| `#2C3E50`                    | →   | `#0F172A`             | Primary text   |
| `#7F8C8D`                    | →   | `#64748B`             | Secondary text |
| `#5D6D7E`                    | →   | `#475569`             | Legend text    |
| `#95A5A6`                    | →   | `#94A3B8`             | Data source    |
| `#BDC3C7`                    | →   | `#CBD5E1`             | Muted elements |
| `#2196F3` / `#1976D2`        | →   | `#3B82F6` / `#2563EB` | Blue series    |
| `#4CAF50` / `#388E3C`        | →   | `#10B981` / `#059669` | Green series   |
| `#FF9800` / `#F57C00`        | →   | `#F59E0B` / `#D97706` | Amber series   |
| `#E91E63`                    | →   | `#F43F5E`             | Outliers       |
| `#000000` (shadow)           | →   | `#0F172A`             | Shadow base    |

---

## 8. Placeholder Content Strategy

Since these SVG files are "templates" designed to be consumed by the AI pipeline, their core value lies in demonstrating **graphical structure, typographical constraints, and visual spatial boundaries**, rather than delivering real business data. Therefore, placeholder text in templates must follow these principles:

### 8.0 English-Only Rule

**Mandatory**: All placeholder text in chart templates (including titles, subtitles, axes, legends, data nodes, detailed descriptions, and source info at the bottom) **must be written entirely in English**.

- **Purpose**: Ensures that downstream LLMs in the automation pipeline can parse semantic intent and map structured content more accurately. The natural length of English words is also better suited to demonstrate text-wrapping logic and bounding boxes in layouts.

### 8.1 Structural Boundary Demonstration

- **Show Max Width/Line-wrap Logic**: Deliberately use strings of typical length (e.g., two-to-three word phrases, multi-line `tspan` elements) to clearly demonstrate text frame boundaries. This ensures the AI has a visual reference when filling in real text, preventing overflow.
- **Show Data Formats**: Use placeholder values that reflect full format characteristics (e.g., `$1,234.5M`, `98.5%`) rather than simple integers like `10` to verify that symbol and character widths are properly budgeted.

### 8.2 Universality and Neutrality

- Use generic, professional business placeholders, avoiding highly specific or vertical business data (unless the template itself is designed specifically for a single industry).
- **Recommended**: Use `Category A`, `Q1 Revenue`, `Strategic Objective`, `Phase 01`.
- **Avoid**: Using highly specific, long real-world data (e.g., "Analysis of Special Equipment Sales of Brand X in 2023").

### 8.3 Visual Balance

- Placeholder text should maintain the visual balance of the chart (e.g., the left and right text blocks in a butterfly chart should have roughly equal lengths, and lists should have staggered line lengths) so that the layout design intent can be understood at a glance.

---

## 9. Registration in charts_index.json

When a new SVG template is added, it **must** be registered in [`charts_index.json`](./charts_index.json); otherwise, the Strategist will not discover it when selecting layouts.

### 9.1 Field Specifications

```json
"<key>": {
  "summary": "Pick for <content shape + scale>. Skip if <counter-example → alternative template>."
}
```

- **`key`** = SVG filename without `.svg`, lowercase with underscores (e.g., `bullet_chart`).
- **`summary`** is a **selection clause**, not a description. Syntax follows `meta.summaryGrammar`: state when to choose it, then use `Skip if ... (use <other_key>)` to point to the most easily confused sibling template.
- **`meta.total`** must be incremented by 1.

> **No need** for `label` / `categories` / `quickLookup` / `keywords` — these have all been removed. The Strategist reads the entire summary list for semantic matching, without relying on pre-computed indexes. **Note**: The summary must be in English, but the source documents often contain Chinese/industry terms. The Strategist handles the semantic translation and matching. If a template strongly relies on a specific Chinese term, write its English equivalent in the Pick clause of the summary.

### 9.2 Examples

❌ Description only: `"summary": "Bidirectional comparison chart for two datasets"`  
✅ Selection clause: `"summary": "Pick for two mirrored datasets sharing a common axis (age pyramid, A/B). Skip for >2 sides (use grouped_bar_chart)."`

❌ Summary is too long (>400 characters) — makes it hard to extract key points during selection. Aim for 150-300 characters.

> **Why not stricter**: A single structural template often needs to cover multiple business frameworks/scenarios (for example, `quadrant_text_bullets` covers SWOT + Ansoff, and `top_down_tree` covers org + OKR). The summary needs keyword anchors (such as "principles, key takeaways, action items") so that the Strategist can semantically match "non-numeric structure pages"; therefore, the old 100-180 character baseline is already too tight after structure-oriented naming.

---

## 10. Checklist

After adding or modifying a chart, verify the following:

### Basic Validation

- [ ] `xmllint --noout` passes
- [ ] viewBox is `0 0 1280 720`
- [ ] First line is a white background `<rect width="1280" height="720" fill="#FFFFFF"/>`

### Colors

- [ ] No legacy colors remain (verify with `grep`, see command below)
- [ ] Shadow `flood-color` is `#0F172A`, and opacity is $\le 0.20$
- [ ] Data sources use `#94A3B8`

### Typography

- [ ] No text has a `font-size < 12`
- [ ] All `<text>` content is wrapped in `<tspan>`
- [ ] Multi-styled text in a single line uses inline `<tspan>` elements, **not** multiple adjacent `<text>` elements
- [ ] Inline `<tspan>` elements do not carry `x` / `y` / `dy` attributes
- [ ] Titles are 34px, subtitles are 18px, and sources are 14px

### Structure

- [ ] Primary elements use semantic `<g id="...">` grouping
- [ ] No `<style>`, `class`, `<foreignObject>`, `mask`, or `rgba()` are used
- [ ] `<g>` tags do not have an `opacity` attribute
- [ ] Text characters are raw Unicode (`—` `©` `→` NBSP etc.), not HTML named entities (`&nbsp;` `&mdash;` `&copy;` etc.); bare `& < >` are escaped as `&amp; &lt; &gt;`

### Shadows

- [ ] Uses the `feFlood` approach (no `feComponentTransfer`)
- [ ] All shadows on the same page share the same `dx`/`dy` direction
- [ ] No more than 3 shadowed elements per page

### Registration (Only for new templates)

- [ ] Registered in `charts_index.json` under `charts.<key>` with a `summary` field
- [ ] `summary` is written as a selection clause (`Pick for ... Skip if ... (use <other>)`), not a description
- [ ] `summary` length is between 150-300 characters (rewrite if >400); up to 350 characters allowed if it covers multiple business frameworks and needs keyword anchors
- [ ] `meta.total` is incremented by 1

### Coordinate Calibration Marker (Mandatory for calculator-supported charts)

- [ ] Rectangular coordinate charts contain the `<!-- chart-plot-area: x_min,y_min,x_max,y_max -->` marker
- [ ] Pie / donut / radar charts contain the `<!-- chart-plot-area: <type> | center: cx,cy | radius: r -->` marker
- [ ] The marker is located inside `<g id="chartArea">`, after axes, and before data elements
- [ ] Coordinate values match the actual SVG coordinates of the axes

### Validation Commands

```bash
# Quick validation
f="your_chart.svg"
xmllint --noout "skills/viettel-ppt-master/templates/charts/$f" && echo "XML OK" || echo "XML FAIL"
echo "Old colors:" && grep -c '#2C3E50\|#7F8C8D\|#95A5A6\|#5D6D7E\|#000000' "skills/viettel-ppt-master/templates/charts/$f"
echo "Small fonts:" && grep -c 'font-size="[0-9]"' "skills/viettel-ppt-master/templates/charts/$f"
```

---

## 11. Card Container Patterns

Card containers are the most frequently reused visual units in PPT Master (KPI cards, section cards, info cards). The following three patterns are proven "reference implementations" that are round-trip compatible with PPTX. New templates should prioritize these patterns; do not invent functional equivalents with messy implementations.

### 11.1 Half-Rounded Section Tab

**Purpose**: Adds a colored "tab" to a card or block to identify classifications (S/W/O/T, Political/Economic, self-introduction, awards, etc.). More readable than plain text headers and more compact than standalone tag bars.

**Two Configurations** — select based on the tab's "visual anchor" (top or bottom):

| Configuration              | Shape                                      | Visual Semantics                                 | Typical Scenario                                      |
| -------------------------- | ------------------------------------------ | ------------------------------------------------ | ----------------------------------------------------- |
| **Round Top, Flat Bottom** | Top corners rounded, bottom corners square | A label "growing out" from the card              | Section cards, quadrant headers, info card categories |
| **Flat Top, Round Bottom** | Top corners square, bottom corners rounded | A tag "hanging down" from the header/chapter bar | Chapter anchors, header bar extensions, TOC markers   |

> Requirement for both: **Round only one pair of corners**, drawn directly via a single path. Do not use the hack of "full-rounded rectangle + overlapping rectangle of the same color" (this splits into two separate shapes in PPTX, causing editing issues).

**Implementation 1: Round Top, Flat Bottom (Default)**

```xml
<!-- Template: Width W, Height H, Radius R, Top-Left Origin (x, y) -->
<path d="M {x+R} {y} h {W-2R} a {R} {R} 0 0 1 {R} {R} v {H-R} h -{W} v -{H-R} a {R} {R} 0 0 1 {R} -{R} Z"
      fill="#2563EB"/>

<!-- Example: 240x50, r=25, Origin (245, 140) -->
<path d="M 245 140 h 190 a 25 25 0 0 1 25 25 v 25 h -240 v -25 a 25 25 0 0 1 25 -25 Z" fill="#2563EB"/>
```

**Implementation 2: Flat Top, Round Bottom (Hanging Tag)**

```xml
<!-- Template: Width W, Height H, Radius R, Top-Left Origin (x, y) -->
<path d="M {x} {y} h {W} v {H-R} a {R} {R} 0 0 1 -{R} {R} h -{W-2R} a {R} {R} 0 0 1 -{R} -{R} Z"
      fill="#2563EB"/>

<!-- Example: 240x50, r=25, Origin (245, 140) -->
<path d="M 245 140 h 240 v 25 a 25 25 0 0 1 -25 25 h -190 a 25 25 0 0 1 -25 -25 Z" fill="#2563EB"/>
```

**Bad Practice Counter-Example** (frequently found in legacy PEST/SWOT/comparison_columns templates):

```xml
<!-- ❌ DO NOT DO THIS: full-rounded rectangle + white rectangle covering one rounded edge -->
<rect width="260" height="120" rx="12" fill="#EFF6FF"/>
<rect y="100" width="260" height="20" fill="#EFF6FF"/>
```

The overlapping rectangle will turn into an independent shape in the SVG-to-PPTX export, meaning that editing the header color in PPT will require modifying both shapes, which is error-prone.

### 11.2 Nested Card Border

**Purpose**: Gives the card a "bordered" look while avoiding using the SVG `stroke` attribute. Strokes are often rendered as thin lines in PPTX, and stacking them with shadows can look dated.

**Approach**: Place a light gray rounded rect at the outer layer, and a slightly smaller white rounded rect at the inner layer, leaving a gap of 8–20px to form a border effect.

```xml
<!-- Outer "border" layer -->
<rect x="60" y="140" width="560" height="255" rx="20" fill="#F1F5F9"/>
<!-- Inner white content card (inward offset of 20px, smaller radius) -->
<rect x="80" y="210" width="520" height="165" rx="12" fill="#FFFFFF"/>
```

**Applicable Conditions**:

- When the card has a tab (§11.1) above it, the outer frame serves as the background for the tab.
- Use only **one** style of border per page: outer border frame OR stroke OR shadow. Do not stack them (see §3 Shadow principles).

### 11.3 Card Grid as Page Skeleton

**Purpose**: When a slide needs to display 4 peer concepts (pillars, aspects, quadrants), prioritize using a 2×2 grid over vertical stacking.

**Grid Dimension Guidelines** (1280×720 canvas):

| Grid Style       | Single Card W × H | Gap | Start Coordinate (x, y)                      |
| ---------------- | ----------------- | --- | -------------------------------------------- |
| 2×2              | 560 × 255         | 40  | (60, 140), (660, 140), (60, 420), (660, 420) |
| 2×3 (Horizontal) | 370 × 260         | 25  | (50, 130), row distance 290                  |
| 1×3 (Wide)       | 400 × 540         | 30  | (60, 130), column distance 430               |
| 1×4 (Top)        | 280 × 250         | 20  | (60, 150), column distance 300               |

**Determination**: "4 parallel aspects" → 2×2; "3 parallel aspects" → 1×3; "6 capability points" → 2×3; "4 key metrics" → 1×4. Slides marked as `breathing` in `page_rhythm` **must not** use card grids (see `executor-base.md §2.1`).

### 11.5 Diagonal Dashed Connector

**Purpose**: Expresses "cross-quadrant/cross-level" relationships — priority migrations, influence propagation, dotted-line reporting, or diagonal trends. Horizontal/vertical arrows express "process flows", whereas diagonal dashed arrows denote "guidance or relationships".

**Approach**: Single `<line>` + `stroke-dasharray="6 5"` + `marker-end`. Define a separate marker for this line (avoid reusing the main process flow arrow color; Slate 600 `#475569` is recommended to denote a "suggestive, non-mandatory" tone).

```xml
<defs>
  <marker id="migrationArrow" markerWidth="12" markerHeight="12"
          refX="10" refY="6" orient="auto" markerUnits="strokeWidth">
    <path d="M 0,0 L 10,6 L 0,12 Z" fill="#475569"/>
  </marker>
</defs>

<!-- Diagonal migration arrow from Q4 (bottom-right) to Q2 (top-left) -->
<line x1="850" y1="605" x2="385" y2="200"
      stroke="#475569" stroke-width="2"
      stroke-dasharray="6 5" stroke-linecap="round"
      marker-end="url(#migrationArrow)"/>

<!-- Center label: White pill overlaying the arrow to prevent visual clashes -->
<rect x="525" y="385" width="190" height="28" rx="14"
      fill="#FFFFFF" stroke="#CBD5E1" stroke-width="1"/>
<text x="620" y="403" text-anchor="middle" font-size="12"
      font-weight="700" fill="#475569" letter-spacing="1">PRIORITY MIGRATION</text>
```

> **Requirement**: Every diagonal dashed arrow must be accompanied by a midpoint label (a small capsule or a line of text); otherwise, readers will be confused about what the connection implies. Unlabeled arrows are only allowed in simple horizontal/vertical process flows (such as `process_flow`).

### 11.6 Ground Anchor Ellipse — Depth without `<filter>`

**Purpose**: Provides visual grounding for floating elements (circular icons, avatars, trophies, or badges) **without using `<filter>` shadows**.

**Why it is useful**:

1. It uses a native PPTX circle/ellipse object, which is consistent across renderers and does not map to `<a:outerShdw>` (avoiding shadow color loss or reordering issues).
2. It aligns with §3 "Shadow restraint" — the remaining elements can use this approach to establish depth without exceeding the shadow budget.
3. It is **much easier to edit in PPT** than filter shadows (users can resize, recolor, or delete it directly).

**Approach**: Draw a flat ellipse (`ry << rx`) directly **below** the floating element, using low opacity and either the primary brand color or Slate 900:

```xml
<!-- Ground shadow ellipse below the avatar/badge, cy is 10-15px below the avatar's bottom -->
<ellipse cx="80" cy="172" rx="70" ry="5" fill="#0F172A" opacity="0.10"/>
<!-- Draw the avatar itself (order is critical; ellipse must be drawn first) -->
<circle cx="80" cy="80" r="80" fill="#E2E8F0"/>
```

**Parameters Reference**:

| Floating Element Radius | Ellipse rx | Ellipse ry | opacity   |
| ----------------------- | ---------- | ---------- | --------- |
| 30-50 px                | r × 0.85   | 3-4        | 0.10-0.15 |
| 50-100 px               | r × 0.85   | 5-6        | 0.10-0.12 |
| 100+ px                 | r × 0.85   | 7-9        | 0.08-0.10 |

Color: defaults to `#0F172A` (neutral dark gray), but can be changed to a darker variant of the theme color (e.g., `#1E3A8A` for blue elements) to express a "branded shadow".

**Banned**: Do not draw the ellipse too round (`ry/rx > 0.25` looks unnatural). Do not stack it on top of a `<filter>` shadow — choose one or the other.

### 11.7 Bidirectional Interaction Arrows

**Purpose**: Expresses paired relationships like "request/response", "push/pull", "uplink/downlink", or "supply/demand". Differs from sequential single-direction flow arrows.

**Approach**: Two parallel `<line>` elements with opposite directions and distinct marker colors. **Each line must carry a label**:

```xml
<defs>
  <marker id="reqArrow" markerWidth="10" markerHeight="10" refX="9" refY="5"
          orient="auto" markerUnits="strokeWidth">
    <path d="M0,0 L10,5 L0,10 Z" fill="#3B82F6"/>
  </marker>
  <marker id="respArrow" markerWidth="10" markerHeight="10" refX="9" refY="5"
          orient="auto" markerUnits="strokeWidth">
    <path d="M0,0 L10,5 L0,10 Z" fill="#10B981"/>
  </marker>
</defs>

<!-- Request: Left-to-right, Blue -->
<line x1="380" y1="250" x2="926" y2="250" stroke="#3B82F6" stroke-width="2.5"
      marker-end="url(#reqArrow)"/>
<rect x="500" y="216" width="280" height="26" rx="11" fill="#FFFFFF"
      stroke="#3B82F6" stroke-width="1"/>
<text x="640" y="234" text-anchor="middle" font-size="14" font-weight="700"
      fill="#3B82F6">① Login Request · POST /auth/login</text>

<!-- Response: Right-to-left, Green -->
<line x1="926" y1="290" x2="384" y2="290" stroke="#10B981" stroke-width="2.5"
      marker-end="url(#reqArrow)"/>
<!-- ...with similar label... -->
```

**Color Convention**: Use blue `#3B82F6` for the initiator (request) and green `#10B981` for the responder. For symmetric peer relationships (e.g., A↔B collaboration), use Slate 600 `#475569` for both.

**Banned**: Drawing bare lines is not permitted — **both arrows must have labels** explaining the action; otherwise, the directional semantics are ambiguous.

### 11.8 Reference Implementations

| Pattern                                    | Reference Templates                                                                               |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| §11.1 Half-Rounded Section Tab (Round Top) | `quadrant_text_bullets.svg`, `labeled_card.svg`, `vertical_pillars.svg`, `comparison_columns.svg` |
| §11.2 Nested Card Border                   | `labeled_card.svg`                                                                                |
| §11.3 2×2 Card Grid                        | `kpi_cards.svg`, `quadrant_text_bullets.svg`, `labeled_card.svg`                                  |
| §11.3 2×3 Card Grid                        | `icon_grid.svg`                                                                                   |
| §11.3 1×3 / 1×4 Card Grid                  | `comparison_columns.svg`, `vertical_pillars.svg`                                                  |
| §11.5 Diagonal Dashed Connector            | `matrix_2x2.svg`                                                                                  |
| §11.6 Ground Anchor Ellipse                | `team_roster.svg`                                                                                 |
| §11.7 Bidirectional Arrows                 | `client_server_flow.svg`                                                                          |
