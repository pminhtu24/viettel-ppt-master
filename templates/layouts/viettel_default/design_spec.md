---
summary: "Viettel corporate reporting template for native PPT Master decks with fixed top-right logo and restrained telecom visual system."
keywords:
  - Viettel
  - corporate
  - telecom
  - executive reporting
  - native PPTX
category: corporate
primary_color: "#EE0033"
use_cases: "Viettel business reports, telecom growth reports, digital transformation proposals, executive briefings"
design_tone: "Structured, restrained, brand-led, enterprise telecom"
---

# viettel_default - Viettel Corporate Template

> Native SVG template shell for Viettel-style PPT Master decks. This template keeps the brand layer stable while leaving the content body available for adaptive Viettel charts, diagrams, and content compositions.

---

## I. Template Overview

| Property          | Description                                                                                             |
| ----------------- | ------------------------------------------------------------------------------------------------------- |
| **Template Name** | viettel_default                                                                                         |
| **Use Cases**     | Viettel business reports, telecom growth reports, digital transformation proposals, executive briefings |
| **Design Tone**   | Structured, restrained, brand-led, enterprise telecom                                                   |
| **Theme Mode**    | Light corporate theme with Viettel red accent                                                           |
| **Info Density**  | Medium to high density, optimized for editable PPTX reporting                                           |

---

## II. Canvas Specification

| Property              | Value                                         |
| --------------------- | --------------------------------------------- |
| **Format**            | Standard 16:9                                 |
| **Dimensions**        | 1280 x 720 px                                 |
| **viewBox**           | `0 0 1280 720`                                |
| **Page Margins**      | left/right 64px, top 34px, bottom 42px        |
| **Logo Slot**         | top-right, x=1088, y=28, width=128, height=42 |
| **Content Safe Area** | x: 72-1208, y: 128-640                        |

---

## III. Color Scheme

### Brand Colors

| Role             | Value     | Usage                                                            |
| ---------------- | --------- | ---------------------------------------------------------------- |
| **Viettel Red**  | `#EE0033` | Brand accent, active rules, page number block, primary CTA      |
| **Deep Blue**    | `#12436D` | Chart, diagram/infographic, and icon marks only                   |

### Functional Colors

| Role           | Value     | Usage                                                         |
| -------------- | --------- | ------------------------------------------------------------- |
| **Surface Gray**   | `#F2F2F2` | Subtle content bands, footer, card backgrounds              |
| **Border Gray**    | `#E6E6E6` | Dividers, content frames, card strokes                       |
| **Success Teal**   | `#28A197` | Positive indicators, positive data series                   |
| **Warning Orange** | `#F46A25` | Risk highlights, warning indicators                           |

### Text Colors

| Role              | Value     | Usage                                                    |
| ----------------- | --------- | -------------------------------------------------------- |
| **Primary Text**  | `#000000` | Main titles, body copy                                  |
| **Secondary Text**| `#44494D` | Subtitles, captions, descriptions                       |
| **Tertiary Text** | `#999999` | Footnotes, page numbers, source citations                |
| **White Text**    | `#FFFFFF` | Text on Viettel-red emphasis blocks                      |

### Chart Colors (Series Order)

| Order | Value     | Usage                                      |
| ----- | --------- | ------------------------------------------ |
| 1     | `#EE0033` | Primary data series, key metrics          |
| 2     | `#12436D` | Secondary data series, comparisons        |
| 3     | `#28A197` | Tertiary series, positive trends          |
| 4     | `#F46A25` | Warning series, risk data                 |
| 5     | `#6B7280` | Neutral/background series                 |

> Use chart colors in rotation order for data visualizations (bar charts, line charts, pie charts).

> **Deep-blue hard rule**: `#12436D` is never a text, background, card, rail,
> footer, divider, or decorative color. Every SVG element using it must live
> inside `<g data-viettel-blue-scope="chart|diagram|icon">`.

### Optional Gradient Scheme

```xml
<!-- Optional red accent gradient (horizontal) -->
<linearGradient id="viettelAccent" x1="0%" y1="0%" x2="100%" y2="0%">
  <stop offset="0%" stop-color="#EE0033"/>
  <stop offset="100%" stop-color="#C00028"/>
</linearGradient>

<!-- Optional red vertical gradient -->
<linearGradient id="viettelAccentV" x1="0%" y1="0%" x2="0%" y2="100%">
  <stop offset="0%" stop-color="#EE0033"/>
  <stop offset="100%" stop-color="#C00028"/>
</linearGradient>

```

> **Usage**: Gradients are optional accents for generated content. The base shell pages use flat colors for maximum PPTX stability.

---

## IV. Typography System

### Font Stack

**Locked Font Family**: `"FS Magistral"`

> FS Magistral is mandatory and is not presented as a user-selectable option. Project setup copies only the required Book, Medium, and Bold faces from the local `fonts/` bundle; run font preflight before generation and treat fallback rendering as a brand-fidelity warning, not as a silent substitute.

### Role Breakdown

| Role         | Font Stack                                                         | Usage                       |
| ------------ | ------------------------------------------------------------------ | --------------------------- |
| **Title / Header** | `"FS Magistral"` Bold (`700`) | Cover, chapter/page titles, section/card headers |
| **Emphasis** | `"FS Magistral"` Bold (`700`) | KPI/hero numbers, key metrics, callouts, highlighted text |
| **Body** | `"FS Magistral"` Book/Regular (`400`) | Body content, descriptions, ordinary chart labels |
| **Secondary** | `"FS Magistral"` Medium (`500`) | Secondary subtitles and labels only |
| **Caption** | `"FS Magistral"` Book/Regular (`400`) | Footnotes, sources, page numbers |

### Font Size Hierarchy

| Purpose       | Ratio to body | @body=18px (dense) | @body=20px (standard) | Weight  |
| ------------- | ------------- | ------------------ | --------------------- | ------- |
| Cover title   | 2.5-3x        | 45-54px            | 50-60px               | 700     |
| Chapter title | 2-2.5x        | 36-45px            | 40-50px               | 700     |
| Page title    | 1.5-2x        | 27-36px            | 30-40px               | 700     |
| Section/card header | 1-1.3x  | 18-24px            | 20-26px               | 700     |
| KPI/hero number | 1.5-2.5x    | 27-45px            | 30-50px               | 700     |
| Subtitle      | 1.2-1.5x      | 22-27px            | 24-30px               | 500     |
| **Body**      | **1x**        | **18px**           | **20px**              | 400     |
| Caption       | 0.7-0.85x     | 13-15px            | 14-17px               | 400     |
| Page number   | 0.6-0.75x     | 11-14px            | 12-15px               | 400     |

> Keep the single font family exactly as declared in `spec_lock.md`. Do not introduce ad-hoc fonts in page SVGs.
> For Viettel decks, Strategist MUST write `"FS Magistral"` into `spec_lock.md ## typography` as `font_family`. Do not ask the user to choose typography. Use only weights `400`, `500`, and `700`; prominent text uses `700`, never `800`/ExtraBold.
> Viettel template projects ship a local `fonts/` bundle. After project setup, run `scripts/check_fonts.py <project_path>`; if the result is `fallback in use` or `missing`, continue with the same stack but report `brand fidelity degraded`. Installation from the local bundle is opt-in and requires explicit user approval.

---

## V. Layout Principles

### 5.1 Page Structure

| Area | Position | Description |
| --- | --- | --- |
| **Logo Area** | top-right, x=1088, y=28 | Fixed Viettel logo (128×42) on every page |
| **Top Accent Bar** | y: 0-5, full width | Red accent bar (5px) |
| **Brand Rail** | x: 0-24, full height | Red (18px) + neutral gray (6px) vertical rails on cover/ending |
| **Title Bar** | y: 38-102 | Red vertical bar (7×38) + title text |
| **Content Area** | x: 72-1208, y: 132-618 | Main body with optional dashed frame |
| **Footer** | y: 674-720 | Gray bar with section name, source, page number |
| **Page Number Badge** | x=1174, y=684 | Red rounded rect (42×26) with white number |
| **Header Title Safe Slot** | x=88-1048, y=36-92 | Page title text; must leave the fixed logo slot clear |

### 5.2 Structural Rules

1. **Fixed Brand Chrome**: the Viettel logo appears in the top-right corner across every shell page.
2. **Clean Reporting Surface**: white canvas, restrained dividers, and practical content zones.
3. **Red as Signal, Not Decoration**: red marks hierarchy, section state, page number, or key emphasis.
4. **PPT Master Compatibility**: no CSS, no foreignObject, no embedded web font, no HTML layout dependency.
5. **Chart-First Compatibility**: charts and diagrams from `templates/charts/` should be composed inside the content safe area or receive brand chrome during post-processing.
6. **Brand Rail Consistency**: cover and ending pages use full-height red+neutral rails; content pages use top accent bar only.
7. **Open Canvas Content**: content pages should not reserve large fixed sidebars; keep the canvas flexible for charts and layouts.
8. **Logo Clearance**: no title, subtitle, header text, chart label, or callout may enter the logo reserved slot (`x=1060-1224`, `y=20-82`). Long content-page titles must wrap inside `data-box="88,36,960,58" data-wrap="true"` or be manually split before the logo slot.
9. **Single Page Number Source**: shell pages already own the footer/page number. Post-processing may add Viettel brand chrome only to pages that do not already contain the shell logo/page-number treatment.

### 5.3 Layout Patterns

> **Principle — proportion follows information weight, not preset ratios.** Combine patterns as needed, or break the grid entirely for `breathing` pages. Defaulting every page to a symmetric grid produces the "AI-generated" look — vary intentionally.

| Pattern | Use Cases | Viettel Example |
| --- | --- | --- |
| **Title + Open Canvas** | Executive summary, key messages, cover, ending | `01_cover.svg`, `04_ending.svg` |
| **Two Column (5:5 / 3:7)** | Solution architecture, comparison, chart + text | Content page with image left, text right |
| **Card Grid (2×2 / 3-column)** | Capability modules, initiatives, KPI dashboard | 4 metric cards with red number badges |
| **Timeline / Process** | Implementation roadmap, milestones | Horizontal timeline with red markers |
| **Chart + Notes** | Data dashboards, KPI explanation | Bar chart left, key insights right |
| **Full-bleed + Floating** | Hero moments, breathing pages, chapter dividers | `02_chapter.svg` with watermark number |

**Pattern Selection Guide**:
- Use **Title + Open Canvas** for cover, ending, and key message pages
- Use **Two Column** when content needs side-by-side comparison or image+text
- Use **Card Grid** for capability lists, feature modules, metric displays
- Use **Timeline/Process** for roadmaps, implementation phases
- Use **Chart + Notes** for data-heavy pages with insights
- Use **Full-bleed + Floating** for chapter dividers and breathing moments

### 5.4 Spacing Specification

**Universal** (any container type):

| Element | Value | Notes |
| --- | --- | --- |
| Outer margin | 64px | Left/right safe zone |
| Title-to-content gap | 20px | Title bar to main content |
| Content block gap | 24px | Between content blocks |
| Icon-text gap | 12px | Icon + text spacing |

**Card-based layouts** (when using cards):

| Element | Value | Notes |
| --- | --- | --- |
| Card gap | 20-24px | Between cards |
| Card padding | 20px | Inside card content |
| Card border radius | 6-10px | Rounded corners |
| Three-column card width | ~360px each | Equal width 3 cards |

**Non-card containers** (naked text blocks, full-bleed imagery):

| Element | Value | Notes |
| --- | --- | --- |
| Line-height | 1.4-1.6× body | Vertical rhythm |
| Full-bleed text inset | 64px | From canvas edge |

### 5.5 Text Fit and Overflow Rules

Viettel decks are chart-heavy and often use compact cards. Every text block inside a card, KPI tile, chart label lane, insight panel, or footer must be budgeted before SVG authoring.

| Slot | Default Budget |
| --- | --- |
| KPI value | 1 line; unit below if combined width exceeds tile width |
| KPI caption | 1-2 lines, 14-16px |
| Insight/card body | 2-3 lines, 14-16px, line-height 1.4-1.5 |
| Chart annotation | 1-2 lines, 12-14px |
| Footer/source | 1 line; must leave 64px clearance from page badge |

Implementation rules:

1. Use manual line breaks or `data-box="x,y,w,h" data-wrap="true"` on all bounded text. A plain one-line `<text>` inside a card is allowed only when the text is short enough to fit with 18px inner padding.
2. Keep card text at least 18px from the left/right edges and 14px from header bars/dividers.
3. Do not place chart bars, labels, or callout badges in the large-title zone. On standard Viettel content pages, chart/data marks should stay below y=255 unless the page is intentionally a breathing/hero composition.
4. If a paragraph or bullet list does not fit within its card at the minimum font size, split the content across pages or remove secondary text. Do not shrink body text into unreadable microtype.

---

## VI. Page Types

### 1. Cover Page (01_cover.svg)

**Layout Structure**:

- White background with left-side brand rails
- Red vertical rail (18px) + neutral-gray rail (6px) on left edge
- Viettel logo fixed at top-right (x=1088, y=28, 128×42)
- Title area centered-left with red underline

**Areas**:
| Area | Position | Content |
|------|----------|---------|
| Brand Rails | x: 0-24, full height | Red + neutral-gray vertical bars |
| Logo | top-right corner | Viettel logo image |
| Label | x=96, y=168 | "VIETTEL REPORT" tag |
| Title | x=96, y=242 | Main report title ({{TITLE}}) |
| Underline | x=96, y=282 | Red accent line (760px) |
| Subtitle | x=96, y=330 | Subtitle ({{SUBTITLE}}) |
| Author Box | x=96, y=492 | Gray card with prepared-by info |
| Date | bottom-right | Report date ({{DATE}}) |
| Bottom Decoration | x=96, y=642 | Red + neutral-gray pill shapes |

**Placeholders**:
| Placeholder | Description | Example |
|------------|-------------|---------|
| `{{TITLE}}` | Main title | "Báo Cáo Kinh Doanh Q4/2025" |
| `{{SUBTITLE}}` | Subtitle/tagline | "Viettel Telecom JSC" |
| `{{AUTHOR}}` | Prepared by | "Phòng Kinh Doanh" |
| `{{DATE}}` | Date/location | "Hà Nội, tháng 12/2025" |

**Signature Elements**:

```xml
<!-- Brand rails -->
<rect x="0" y="0" width="18" height="720" fill="#EE0033"/>
<rect x="18" y="0" width="6" height="720" fill="#E6E6E6"/>

<!-- Red underline -->
<rect x="96" y="282" width="760" height="2" fill="#EE0033"/>

<!-- Author card -->
<rect x="96" y="492" width="520" height="72" rx="6" fill="#F2F2F2" stroke="#E6E6E6" stroke-width="1"/>
```

---

### 2. Table of Contents (02_toc.svg)

**Layout Structure**:

- Top red accent bar (full width, 5px height)
- Logo fixed at top-right
- Page title with summary text
- TOC items with numbered circles
- Page number at bottom-right

**Areas**:
| Area | Position | Content |
|------|----------|---------|
| Top Bar | y: 0-5, full width | Red accent bar |
| Logo | top-right corner | Viettel logo image |
| Title | x=72, y=70 | Page title ({{PAGE_TITLE}}) |
| Summary | x=72, y=104 | TOC description ({{TOC_SUMMARY}}) |
| Divider | y=132 | Gray horizontal line |
| TOC Items | y: 172-492 | 5 numbered items, 80px apart |
| Footer | bottom | Red pill + page number |

**Placeholders**:
| Placeholder | Description | Example |
|------------|-------------|---------|
| `{{PAGE_TITLE}}` | "Mục Lục" or "Nội Dung" | "Nội Dung Chính" |
| `{{TOC_SUMMARY}}` | Brief description | "Các phần trình bày trong báo cáo" |
| `{{TOC_ITEM_1_TITLE}}` | First item title | "Tổng Quan Kinh Doanh" |
| `{{TOC_ITEM_2_TITLE}}` | Second item title | "Phân Tích Thị Trường" |
| `{{TOC_ITEM_3_TITLE}}` | Third item title | "Chiến Lược Phát Triển" |
| `{{TOC_ITEM_4_TITLE}}` | Fourth item title | "Kết Quả Tài Chính" |
| `{{TOC_ITEM_5_TITLE}}` | Fifth item title | "Kế Hoạch Tới Đây" |
| `{{PAGE_NUM}}` | Page number | "02" |

**Signature Elements**:

```xml
<!-- TOC item with number badge -->
<g transform="translate(88,172)">
  <circle cx="18" cy="18" r="18" fill="#EE0033"/>
  <text x="18" y="25" text-anchor="middle" font-size="16" font-weight="700" fill="#FFFFFF">01</text>
  <text x="64" y="26" font-size="24" font-weight="700" fill="#000000">{{TOC_ITEM_1_TITLE}}</text>
</g>
```

---

### 3. Chapter Page (02_chapter.svg)

**Layout Structure**:

- White background with left brand rail
- Large watermark chapter number (light gray)
- Centered chapter title with red accent bar
- Chapter badge (red square with number)
- Logo fixed at top-right

**Areas**:
| Area | Position | Content |
|------|----------|---------|
| Brand Rail | x: 0-18, full height | Red vertical rail |
| Logo | top-right corner | Viettel logo image |
| Watermark Number | x=110, y=206 | Light gray {{CHAPTER_NUM}} |
| Accent Bar | x=110, y=238 | Red horizontal bar (90×10) |
| Title | x=110, y=328 | Chapter title ({{CHAPTER_TITLE}}) |
| Description | x=112, y=376 | Chapter subtitle ({{CHAPTER_DESC}}) |
| Chapter Badge | x=952, y=208 | Red square with number |
| Divider | y=620 | Gray horizontal line |
| Page Number | bottom-right | {{PAGE_NUM}} |

**Placeholders**:
| Placeholder | Description | Example |
|------------|-------------|---------|
| `{{CHAPTER_NUM}}` | Chapter number | "01", "02", "03" |
| `{{CHAPTER_TITLE}}` | Chapter title | "Tổng Quan Kinh Doanh" |
| `{{CHAPTER_DESC}}` | Chapter description | "Phân tích kết quả kinh doanh năm 2025" |
| `{{PAGE_NUM}}` | Page number | "03" |

**Signature Elements**:

```xml
<!-- Watermark number (light gray) -->
<text x="110" y="206" font-size="96" font-weight="700" fill="#F2F2F2">{{CHAPTER_NUM}}</text>

<!-- Red accent bar -->
<rect x="110" y="238" width="90" height="10" rx="5" fill="#EE0033"/>

<!-- Chapter badge -->
<rect x="952" y="208" width="144" height="144" rx="10" fill="#EE0033" data-allow-title-zone="true"/>
<text x="1024" y="300" text-anchor="middle" data-box="970,238,108,76" data-wrap="true" font-size="56" font-weight="700" fill="#FFFFFF">{{CHAPTER_NUM}}</text>
```

---

### 4. Content Page (03_content.svg)

**Layout Structure**:

- White background with top red accent bar
- Logo fixed at top-right
- Page title with red vertical bar identifier
- Dashed content area frame
- Gray footer with section name, source, page number

**Areas**:
| Area | Position | Content |
|------|----------|---------|
| Top Bar | y: 0-5, full width | Red accent bar |
| Logo | top-right corner | Viettel logo image |
| Title Bar | x=64-88, y=38-76 | Red vertical bar + title text |
| Title | x=88-1048, y=36-92 | Page title ({{PAGE_TITLE}}), wrapped before logo slot |
| Divider | y=102 | Gray horizontal line |
| Content Area | x=72-1208, y=132-618 | Dashed border frame |
| Footer | y=674-720 | Gray bar with section info |
| Page Number | x=1174, y=684 | Red badge with number |

**Placeholders**:
| Placeholder | Description | Example |
|------------|-------------|---------|
| `{{PAGE_TITLE}}` | Page title | "Phân Tích Doanh Thu" |
| `{{CONTENT_AREA}}` | Placeholder text (remove after fill) | "Nội dung chính" |
| `{{SECTION_NAME}}` | Section/chapter name | "Phần 1: Tổng Quan" |
| `{{SOURCE}}` | Data source citation | "Nguồn: Báo cáo nội bộ" |
| `{{PAGE_NUM}}` | Page number | "04" |

**Signature Elements**:

```xml
<!-- Title vertical bar -->
<rect x="64" y="38" width="7" height="38" rx="3.5" fill="#EE0033"/>
<text x="88" y="66" data-box="88,36,960,58" data-wrap="true" font-size="32" font-weight="700" fill="#000000">{{PAGE_TITLE}}</text>

<!-- Dashed content frame -->
<rect x="72" y="132" width="1136" height="486" rx="6" fill="#FFFFFF" stroke="#E6E6E6" stroke-width="1" stroke-dasharray="6 6"/>

<!-- Footer with section name -->
<rect x="0" y="674" width="1280" height="46" fill="#F2F2F2"/>
<rect x="0" y="674" width="8" height="46" fill="#EE0033"/>

<!-- Page number badge -->
<rect x="1174" y="684" width="42" height="26" rx="4" fill="#EE0033"/>
<text x="1195" y="703" text-anchor="middle" font-size="14" font-weight="700" fill="#FFFFFF">{{PAGE_NUM}}</text>
```

---

### 5. Ending Page (04_ending.svg)

**Layout Structure**:

- White background with left brand rails (red + neutral gray)
- Logo fixed at top-right
- Gray card with thank you message
- Decorative accent bars
- Copyright text

**Areas**:
| Area | Position | Content |
|------|----------|---------|
| Brand Rails | x: 0-24, full height | Red + neutral-gray vertical bars |
| Logo | top-right corner | Viettel logo image |
| Thank You Card | x=116, y=170-460 | Gray card with message |
| Thank You Text | x=164, y=280 | Large red {{THANK_YOU}} |
| Subtitle | x=168, y=330 | Dark-neutral {{ENDING_SUBTITLE}} |
| Contact | x=168, y=392 | Contact info ({{CONTACT_INFO}}) |
| Accent Bars | y=526 | Red + neutral-gray pill shapes |
| Copyright | x=116, y=650 | {{COPYRIGHT}} |
| Page Number | x=1208, y=660 | {{PAGE_NUM}} |

**Placeholders**:
| Placeholder | Description | Example |
|------------|-------------|---------|
| `{{THANK_YOU}}` | Closing message | "Cảm Ơn" |
| `{{ENDING_SUBTITLE}}` | Tagline/slogan | "Viettel - Connect to Succeed" |
| `{{CONTACT_INFO}}` | Contact details | "Email: contact@viettel.com.vn" |
| `{{COPYRIGHT}}` | Copyright text | "© 2025 Viettel Telecom JSC" |
| `{{PAGE_NUM}}` | Page number | "15" |

**Signature Elements**:

```xml
<!-- Brand rails (echoing cover) -->
<rect x="0" y="0" width="18" height="720" fill="#EE0033"/>
<rect x="18" y="0" width="6" height="720" fill="#E6E6E6"/>

<!-- Thank you card -->
<rect x="116" y="170" width="840" height="290" rx="10" fill="#F2F2F2" stroke="#E6E6E6" stroke-width="1"/>
<text x="164" y="280" font-size="64" font-weight="700" fill="#EE0033">{{THANK_YOU}}</text>

<!-- Decorative accent bars -->
<rect x="116" y="526" width="96" height="6" rx="3" fill="#EE0033"/>
<rect x="226" y="526" width="58" height="6" rx="3" fill="#E6E6E6"/>
```

---

### Page Type Summary

| Page    | File             | Purpose         | Key Feature                      |
| ------- | ---------------- | --------------- | -------------------------------- |
| Cover   | `01_cover.svg`   | Opening slide   | Brand rails + logo + title       |
| TOC     | `02_toc.svg`     | Navigation      | Numbered items with red circles  |
| Chapter | `02_chapter.svg` | Section divider | Watermark number + chapter badge |
| Content | `03_content.svg` | Main content    | Dashed frame + footer            |
| Ending  | `04_ending.svg`  | Closing         | Thank you card + copyright       |

### Content Page Variants

| Variant | File | Use Cases |
|---------|------|-----------|
| **Default** | `03_content.svg` | Open canvas, free layout |
| **Two Column** | `03a_content_two_col.svg` | Side-by-side comparison, text+chart |
| **Image + Text** | `03b_content_image.svg` | Left image, right text description |
| **Chart + Insights** | `03c_content_chart.svg` | Large chart area with key insights panel |

---

## VII. Visualization Catalog Mapping

For Viettel reporting decks, content pages should normally pair a Viettel layout shell with a chart-library template. The shell provides brand chrome; the chart catalog provides the visualization structure.

| Content shape | Preferred chart template | Viettel layout shell |
| --- | --- | --- |
| 4-8 headline metrics / quarterly recap | `kpi_cards` | `03_content.svg` or `03c_content_chart.svg` |
| Ranked sectors, CVEs, domains, malware families | `horizontal_bar_chart` | `03c_content_chart.svg` |
| Short category comparison, 3-8 items | `bar_chart` | `03c_content_chart.svg` |
| Quarter-over-quarter or year-over-year series | `grouped_bar_chart` or `line_chart` | `03c_content_chart.svg` |
| Severity / attack-type proportions | `donut_chart` or `pie_chart` | `03c_content_chart.svg` |
| Dense incident/CVE lists | `basic_table` or `consulting_table` | `03_content.svg` |
| Recommendations / action groups | `vertical_list`, `numbered_steps`, or `icon_grid` | `03_content.svg` |
| Attack lifecycle / remediation process | `process_flow`, `pipeline_with_stages`, or `timeline` | `03_content.svg` |

Selected chart templates must be mirrored into project `spec_lock.md ## page_charts`. If a page truly has no catalog match, record `no-template-match` in the project Design Spec visualization list with the reason.

---

## VIII. Asset Specification

### Core Assets

| Asset | Purpose | Runtime Path |
| --- | --- | --- |
| `viettel-logo.png` | Required Viettel logo fixed at top-right on shell pages | `../images/viettel-logo.png` |
| `fonts/` bundle | Local install source for FS Magistral family | `<project_path>/fonts/` |

### Asset Path Rule

The source asset lives in `templates/layouts/viettel_default/viettel-logo.png`. During project setup, copy it to `<project_path>/images/viettel-logo.png`; generated SVG pages reference it through the runtime path `../images/viettel-logo.png`.
The font bundle lives in `templates/layouts/viettel_default/fonts/`. During project setup, copy it to `<project_path>/fonts/` unchanged. The deck still declares the intended brand stack in `spec_lock.md`; runtime availability is validated by `scripts/check_fonts.py`.

### Optional Official Assets

| Asset | Purpose |
| --- | --- |
| `viettel-logo-white.png` | Optional logo variant for future dark/red full-brand pages |
| `viettel-cover-bg.png` | Optional official cover/ending background |
| `viettel-network-pattern.png` | Optional subtle telecom/network texture for cover or chapter pages |
| `viettel-slogan.png` | Optional official slogan lockup, only when supplied by the project |

> Do not borrow non-Viettel brand imagery from other templates. If no official asset is supplied, keep the shell vector-only and light.

---

## IX. Chart Specifications

### Recommended Chart Dimensions

| Layout / Chart Type | Recommended Size |
| --- | --- |
| `03_content.svg` open canvas | 1136 x 486px |
| `03a_content_two_col.svg` column chart/text area | 540 x 486px per column |
| `03b_content_image.svg` image area | 520 x 486px |
| `03c_content_chart.svg` chart area | 760 x 486px |
| `03c_content_chart.svg` insights panel | 336 x 486px |
| Donut / pie chart | 260-320px diameter |
| KPI card | 160-200 x 96-120px |
| Timeline / roadmap | 1040-1136 x 120-180px |
| Comparison table | 1000-1136 x 300-400px |

### Chart Usage Rules

1. Use `#EE0033` only for the primary series, key metric, or threshold signal.
2. Use `#12436D`, `#28A197`, and `#F46A25` for secondary series, positive trends, and warnings. Place every `#12436D` mark inside a `data-viettel-blue-scope="chart|diagram|icon"` group.
3. Long labels such as CVE IDs, malware names, agency names, and sector names stay outside bars; values sit at the bar end.
4. KPI cards use a two-line structure: large number on line 1, unit/context on line 2.
5. Tables and ranked lists with more than 8 rows should use `basic_table`, `consulting_table`, or split slides; do not shrink body text below 11px to fit.
6. A chart page may omit `page_layouts` if the catalog chart needs the full content area; post-processing must add Viettel brand chrome.

---

## X. Technical Reference

### SVG Technical Constraints

1. `viewBox` must remain `0 0 1280 720`
2. Use `<rect>` for backgrounds; use separate `<text>` lines or `data-box + data-wrap` for text wrapping
3. Transparency must use `fill-opacity` / `stroke-opacity`; **DO NOT use `rgba()`**
4. **FORBIDDEN**: `mask`, `<style>`, `class`, `foreignObject`, `textPath`, `animate*`, `script`
5. `clipPath` allowed only on `<image>` elements (in `<defs>`, single shape child)
6. `marker-start` / `marker-end` allowed (in `<defs>`, `orient="auto"`, triangle/diamond/circle)
7. Text characters: use raw Unicode (`—`, `→`, `©`, `®`); **DO NOT use HTML entities** (`&mdash;`, `&copy;`)
8. XML reserved chars must be escaped: `&amp;` `&lt;` `&gt;` `&quot;` `&apos;`
9. **DO NOT use `<g opacity="...">`** — set opacity on each child element individually
10. Image transparency uses an overlay rectangle with `fill-opacity`; do not use SVG `<mask>` or group opacity.
11. Inline styles only; external CSS and `@font-face` **FORBIDDEN**

### Complete Placeholder Reference

| Placeholder | Description | Page Type |
| ----------- | ----------- | --------- |
| `{{TITLE}}` | Main title | Cover |
| `{{SUBTITLE}}` | Subtitle/tagline | Cover |
| `{{AUTHOR}}` | Prepared by | Cover |
| `{{DATE}}` | Date/location | Cover |
| `{{PAGE_TITLE}}` | Page title | TOC, Content |
| `{{TOC_SUMMARY}}` | TOC description | TOC |
| `{{TOC_ITEM_1_TITLE}}` | First TOC item | TOC |
| `{{TOC_ITEM_2_TITLE}}` | Second TOC item | TOC |
| `{{TOC_ITEM_3_TITLE}}` | Third TOC item | TOC |
| `{{TOC_ITEM_4_TITLE}}` | Fourth TOC item | TOC |
| `{{TOC_ITEM_5_TITLE}}` | Fifth TOC item | TOC |
| `{{CHAPTER_NUM}}` | Chapter number | Chapter |
| `{{CHAPTER_TITLE}}` | Chapter title | Chapter |
| `{{CHAPTER_DESC}}` | Chapter description | Chapter |
| `{{CONTENT_AREA}}` | Content placeholder (remove after fill) | Content |
| `{{LEFT_CONTENT}}` | Left column content | Content Two Column |
| `{{RIGHT_CONTENT}}` | Right column content | Content Two Column |
| `{{IMAGE_PLACEHOLDER}}` | Image area placeholder | Content Image |
| `{{TEXT_CONTENT}}` | Text description area | Content Image |
| `{{CHART_AREA}}` | Chart visualization area | Content Chart |
| `{{INSIGHT_1}}` | First key insight | Content Chart |
| `{{INSIGHT_2}}` | Second key insight | Content Chart |
| `{{INSIGHT_3}}` | Third key insight | Content Chart |
| `{{INSIGHT_4}}` | Fourth key insight | Content Chart |
| `{{SECTION_NAME}}` | Section/chapter name in footer | Content |
| `{{SOURCE}}` | Data source citation | Content |
| `{{PAGE_NUM}}` | Page number | TOC, Chapter, Content, Ending |
| `{{THANK_YOU}}` | Closing message | Ending |
| `{{ENDING_SUBTITLE}}` | Tagline/slogan | Ending |
| `{{CONTACT_INFO}}` | Contact details | Ending |
| `{{COPYRIGHT}}` | Copyright text | Ending |

### Usage Guide

1. **Copy template files** to project `templates/` directory before starting generation
2. **Copy `viettel-logo.png`** to project `images/` directory
3. **Select page types** based on content structure:
   - Use `01_cover.svg` for opening slide
   - Use `02_toc.svg` for table of contents (supports 5 items)
   - Use `02_chapter.svg` for section dividers
   - Use `03_content.svg` as the main content shell
   - Use `03c_content_chart.svg` for chart-library pages that need an insights panel
   - Use `04_ending.svg` for closing slide
4. **For chart/KPI/table/flow pages**, select a matching `templates/charts/` template and write the page into `spec_lock.md ## page_charts`
5. **Replace placeholders** with actual content (remove `{{CONTENT_AREA}}` after filling)
6. **Apply brand chrome** during post-processing if generating charts/pages without template shell:
   ```bash
   python3 scripts/finalize_svg.py <project_path> --brand-chrome viettel --strip-comments
   ```
7. **Export to PPTX** after all content is filled:
   ```bash
   python3 scripts/svg_to_pptx.py <project_path>
   ```
