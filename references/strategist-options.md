# Strategist options (read only when triggered)

Sections moved out of [`strategist.md`](strategist.md) because a normal Viettel run without slide images never needs them. Read a section only when its trigger applies: an explicit `custom_override`, or image approach B / C / D.


## §e Color scheme — `custom_override` only

**Industry color quick reference (`custom_override` only)** (full 14-industry list in `scripts/config.py` under `INDUSTRY_COLORS`):

| Industry | Primary Color | Characteristics |
|----------|--------------|-----------------|
| Finance / Business | `#003366` Navy Blue | Stable, trustworthy |
| Technology / Internet | `#1565C0` Bright Blue | Innovative, energetic |
| Healthcare / Health | `#00796B` Teal Green | Professional, reassuring |
| Government / Public Sector | `#C41E3A` Red | Authoritative, dignified |

**Color rules**: 60-30-10 rule (primary 60%, secondary 30%, accent 10%); text contrast ratio >= 4.5:1; no more than 4 colors per page.


## §g Typography — non-Viettel overrides only

> The generic pairing guidance below applies only after an explicit non-Viettel override. In the default Viettel flow, hierarchy comes from the assigned static face, size, spacing, and color.

> **⚠️ PPT-safe font discipline (HARD rule).** PPTX has no runtime fallback — missing fonts substitute to Calibri. For explicit non-Viettel overrides, every stack MUST end with a pre-installed font:
> - CJK → `"Microsoft YaHei"` / `SimHei` / `SimSun` / `FangSong` / `KaiTi`
> - Latin sans → `Arial` / `Calibri` / `Segoe UI` / `Verdana` / `Trebuchet MS`
> - Latin serif → `"Times New Roman"` / `Georgia` / `Cambria` / `Palatino` / `Garamond`
> - Mono → `Consolas` / `"Courier New"`
> - Display → `Impact` / `"Arial Black"`
>
> The locked Viettel family is the default bundled-brand exception for this skill. Keep `"FS Magistral"` in the design lock; `scripts/check_fonts.py` searches and auto-installs its three required bundled faces. Other non-pre-installed stacks are acceptable only when the Design Spec notes "requires install or PPTX embed".

**Forbidden — similar-but-not-identical pairings across roles** (do not split title vs body across these; within one stack as cross-platform fallback they remain encouraged):

- `Microsoft YaHei` ↔ `PingFang SC` ↔ `Heiti SC`
- `SimSun` ↔ `Songti SC` ↔ `STSong`
- `Arial` ↔ `Helvetica Neue` ↔ `Segoe UI`
- `"Times New Roman"` ↔ `Times`
- `Georgia` ↔ `Cambria`

**Mandatory for non-Viettel overrides only**: when the user explicitly requests a non-Viettel brand or custom font direction, propose **two** combinations to the user — one concord (safe), one contrast (with tension). For the normal Viettel flow, skip this choice table and use the locked Viettel stack.

**Cross-platform pre-installed reference** (for explicit non-Viettel overrides only):

| Category | Safe families |
|----------|--------------|
| CJK sans | Microsoft YaHei, SimHei, PingFang SC, Heiti SC |
| CJK serif | SimSun, FangSong, KaiTi, Songti SC |
| Latin sans | Arial, Calibri, Segoe UI, Verdana, Trebuchet MS, Helvetica Neue |
| Latin serif | Times New Roman, Georgia, Cambria, Palatino, Garamond, Book Antiqua |
| Mono | Consolas, Courier New |
| Display | Impact, Arial Black |

**Seed combinations** (for explicit non-Viettel overrides only; first column names the contrast axis, not a scenario):

| Contrast axis | Title stack | Body stack | Code stack |
|---|---|---|---|
| Serif × sans | `Georgia, KaiTi, serif` | `"Microsoft YaHei", "PingFang SC", sans-serif` | — |
| Kai × hei | `KaiTi, Georgia, serif` | `"Microsoft YaHei", "PingFang SC", sans-serif` | — |
| Fangsong × hei | `FangSong, "Times New Roman", serif` | `SimHei, "Microsoft YaHei", sans-serif` | — |
| Double serif | `Palatino, FangSong, serif` | `Cambria, SimSun, serif` | — |
| Same family, weight contrast (900 / 300) | `"Microsoft YaHei", "PingFang SC", sans-serif` | same | — |
| Display × neutral | `Impact, "Arial Black", SimHei, sans-serif` | `Arial, "Microsoft YaHei", sans-serif` | — |
| Cool serif (academic) | `Cambria, SimSun, serif` | `"Times New Roman", SimSun, serif` | — |
| Hei × song (政务) | `SimHei, "Microsoft YaHei", sans-serif` | `SimSun, serif` | — |
| Tech / developer | `Arial, "Microsoft YaHei", sans-serif` | same | `Consolas, "Courier New", monospace` |
| Concord (default fallback) | `"Microsoft YaHei", "PingFang SC", sans-serif` | same | — |

> **Stack length discipline (soft rule).** For the default Viettel flow, keep exactly one family: `"FS Magistral"`. For explicit non-Viettel overrides, use ≤4 fonts per stack, lead with Windows-preinstalled fonts when possible, and keep at most **one** macOS-exclusive family. Converter only picks the first Latin and first CJK font ([`drawingml_utils.py parse_font_family`](../scripts/svg_to_pptx/drawingml_utils.py)); macOS→Windows fallback is auto-mapped via `FONT_FALLBACK_WIN`.

> **Non-pre-installed directions** (require install or PPTX embed; note the constraint in Design Spec):
> - **Retro / pixel** — Press Start 2P / VT323 / Silkscreen
> - **Rounded friendly** — Nunito / Quicksand / M PLUS Rounded / OPPO Sans (closest safe substitute: `Trebuchet MS` / `Verdana`)
> - **Modern web sans** — Inter / HarmonyOS Sans / Source Han Sans / Noto Sans
> - **Brand-specific** — McKinsey Bower, corporate VI typefaces


## §g Font size ramp — explicit custom-brand overrides

The following baseline examples and wider role bands apply to **explicit custom-brand overrides**. Baseline choice follows **content density**, not style. Common: `18px` (dense) / `24px` (relaxed). Other integers are fine — `16px` for chart-heavy, `20-22px` for medium, `28-32px` for poster/cover.

| Common recommendation | Points per Page | Body Baseline | Suitable Scenarios |
|----------------|----------------|---------------|-------------------|
| Relaxed | 3-5 items | 24px | Keynote-style, training materials |
| Dense | 6+ items | 18px | Data reports, consulting analysis |

| Level | Ratio to body | 24px baseline | 18px baseline |
|-------|---------------|---------------|---------------|
| Cover title (hero headline) | 2.5-5x | 60-120px | 45-90px |
| Chapter / section opener | 2-2.5x | 48-60px | 36-45px |
| Page title | 1.5-2x | 36-48px | 27-36px |
| Hero number (consulting KPIs) | 1.5-2x | 36-48px | 27-36px |
| Subtitle | 1.2-1.5x | 29-36px | 22-27px |
| **Body** | **1x** | **24px** | **18px** |
| Annotation / caption | 0.7-0.85x | 17-20px | 13-15px |
| Page number / footnote | 0.5-0.65x | 12-16px | 9-12px |

> Two baseline columns are illustrative only — for any other baseline (16/20/22/28/32…), multiply the row's ratio. Checker reads live `body` from `spec_lock.md`. Executor may pick any px within a role's band without pre-declaring; values outside **every** band require lock extension first.


## §h Image resource list — approaches B / C / D only

**When B / C / D is selected**, add an image resource list to the spec:

| Column | Description |
|--------|-------------|
| Filename | e.g., `cover_bg.png` |
| Dimensions | e.g., `1280x720` |
| Ratio | e.g., `1.78` |
| Layout suggestion | e.g., `Wide landscape (suitable for full-screen/illustration)` |
| **Layout pattern** | **MANDATORY** — one or more `#<id> <name>` joined by ` + ` from `image-layout-patterns.md`. Combine a Primary id with optional Modifier ids when the page needs it (e.g. `#48 side-by-side comparison + #21 rounded rectangle crop + #29 two-stop scrim`). A single Primary is fine when the page calls for it. See the GATE earlier in this section. Empty cells or invented ids are invalid. |
| Purpose | e.g., `Cover background` |
| Type | Narrative shorthand: Background / Photography / Illustration / Diagram / Decorative pattern. |
| **Acquire Via** | `web` / `user` / `placeholder` — drives Step 5 dispatch |
| Status | Initial status must be `Pending`, `Existing`, or `Placeholder`; see [`svg-image-embedding.md`](svg-image-embedding.md) for the full status enum |
| **Reference** | Free-form visual intent description; Image_Searcher converts web intents into provider queries |

**No-crop flag (exception only)**: most images are croppable — Executor defaults to `preserveAspectRatio="xMidYMid slice"`. When an image must NOT lose pixels (data screenshots, charts, certificates, contracts, dense diagrams), append `no-crop` to its `spec_lock.md images` entry. Executor will then size the container to the native ratio and use `meet`. Don't tag the rest.

**Reference field**: Write visual intent, not provider mechanics.

| ✅ Intent description | ❌ Avoid |
|---|---|
| "Diverse engineering team collaborating around a laptop, modern office, natural light" | "team laptop office" |
| "Abstract atmospheric backdrop for academic-defense cover, calm center for text overlay, hint of campus skyline" | "use openverse, search 'office'" |
| "Sunlit forest path in autumn" | "team photo" |

**Per-row Reference grammar**:

| Acquire Via | Reference pattern |
|---|---|
| `web` | Concrete subject/place/object first, then 1-3 quality descriptors |

**Allowed web quality descriptors**:

| Descriptor | Use |
|---|---|
| `professional editorial photography` | Stock-style photography |
| `clean composition` | Covers, section dividers, image-text layouts |
| `natural light` | People, workplace, travel, lifestyle scenes |
| `high-resolution` | Large visual areas |

**Forbidden — web negative prompts**: `not tourist snapshot`, `no phone photo`, `avoid amateur style`.

| Mode | Good Reference |
|---|---|
| `web` | "Diverse team collaborating at a modern office desk, professional editorial photography, natural light, laptop visible" |

**Image type descriptions**:

| Type | Suitable Scenarios |
|------|-------------------|
| Background | Full-page backgrounds for covers/chapter pages; reserve text area |
| Photography | Real scenes, people, products, architecture |
| Illustration | Flat design, vector style, concept diagrams |
| Diagram | Flowcharts, architecture diagrams, concept relationship maps |
| Decorative pattern | Partial decoration, textures, borders, divider elements |

🚧 **GATE — before writing §VIII Image Resource List**: when image approach is B/C/D (anything other than A "no images"), this is a three-layer hard requirement, not a suggestion:

1. **Read** — `read_file references/image-layout-patterns.md`. The file enumerates 72 numbered techniques split into **Part 1 — Primary Structures** (#1–#19 container layouts, #38–#46 image-as-canvas + native overlay, #47–#56 multi-image) and **Part 2 — Modifier Layers** (#20–#26 non-rectangular crops, #27–#37 overlays & masks, #57–#61 texture, #62–#72 special). The four `Image narrative intent` values below cover only broad categories.
2. **Produce** — every row in §VIII Image Resource List MUST fill the `Layout pattern` column with one or more `#<id> <name>` joined by ` + ` drawn verbatim from this file (Primary + optional Modifiers). Rows with empty `Layout pattern` or with an id that does not exist in the file are invalid.
3. **Image-as-canvas coverage** — for any deck with ≥4 image-bearing pages, at least one page MUST use a `#38–#46` pattern (image-as-canvas + native overlay) unless every image is a pure cover / chapter divider / atmosphere backdrop. This family is the most-skipped one and is usually the right answer for content-rich pages with photographs. If the deck legitimately has no opportunity for it, state the reason in §VIII directly under the table.

**Skip-detection signal for self-audit**: if you notice that every page's `Layout pattern` column resolves to #2/#3 (left-third or right-third), #5/#6 (top-bottom band), or generic side-by-side, you have not actually consulted the file — re-read and reconsider. The default left/right and top/bottom split bias is the failure mode this gate exists to break.

**Image narrative intent** (decide *before* the ratio table — determines whether the image lives in a container at all):

| Intent | Form | When to use |
|--------|------|-------------|
| **Hero / full-bleed** | Image fills canvas/dominant zone; title floats over with gradient or opacity overlay | Covers, chapter dividers, `breathing` pages — image *is* the message |
| **Atmosphere / background** | Image as low-contrast backdrop (reduced opacity or dark overlay); text reads on top | Section backgrounds, mood-setting — image sets tone, text carries info |
| **Side-by-side** | Image and text as adjacent coequal blocks — ratio table below governs container sizing | Most content pages — image and text read together |
| **Accent / inline** | Small image beside related text, not a container; no ratio matching | Supporting visuals, spot illustrations |

> Intent follows narrative purpose, not image ratio. Don't default every image page to side-by-side.

**Side-by-side ratio alignment** (consult only when the chosen intent is *side-by-side*; detailed calculation rules in `references/image-layout-spec.md`):

| Image Ratio | Recommended Container Layout |
|-------------|-----------------------------|
| > 2.0 (ultra-wide) | Top-bottom split, top full-width |
| 1.5-2.0 (wide) | Top-bottom split |
| 1.2-1.5 (standard landscape) | Left-right split |
| 0.8-1.2 (square) | Left-right split |
| < 0.8 (portrait) | Left-right split, image on left |

Side-by-side only: container ratio must match image ratio. Hero / atmosphere / accent intents ignore ratio alignment.

> **Portrait canvases** (Xiaohongshu, Story): Layout rules differ — top-bottom is preferred for most ratios since left-right columns become too narrow. See "Portrait Canvas Override" in `references/image-layout-spec.md`.

> **Multi-image slides**: When multiple images appear on one page, use the grid formulas in the "Multi-Image Layout" section of `references/image-layout-spec.md`.


## §3 Color knowledge base — `custom_override` only

### Consulting Style Colors

| Brand | HEX |
|-------|-----|
| Deloitte Blue | `#0076A8` |
| McKinsey Blue | `#005587` |
| BCG Dark Blue | `#003F6C` |
| PwC Orange | `#D04A02` |
| EY Yellow | `#FFE600` |

### General Versatile Colors

| Style | HEX |
|-------|-----|
| Tech Blue | `#2196F3` |
| Vibrant Orange | `#FF9800` |
| Growth Green | `#4CAF50` |
| Professional Purple | `#9C27B0` |
| Alert Red | `#F44336` |

### Data Visualization Colors

- Positive trend (green): `#2E7D32` → `#4CAF50` → `#81C784`
- Warning trend (yellow): `#F57C00` → `#FFA726` → `#FFD54F`
- Negative trend (red): `#C62828` → `#EF5350` → `#E57373`

---

## §2 Executor style details — reference


### A) General Versatile — Executor_General

- **Capabilities**: full-width images + gradient overlays; free creative layouts; variants (image-text / minimalist / creative)
- **Scenarios**: promotions, product launches, training, brand campaigns
- **Avoid**: rigid/formal tone, dense data tables

### B) General Consulting — Executor_Consultant

- **Capabilities**: KPI dashboards (4-card, big numbers + trend arrows); chart combinations (bar/line/pie/funnel); status color grading (R/Y/G)
- **Scenarios**: progress reports, financial analysis, government reports, proposals
- **Avoid**: flashy decoration, image-dominated slides

### C) Top Consulting — Executor_Consultant_Top

| Rule | Detail |
|------|--------|
| Data contextualization | Use a comparison only when both comparable values have sources; otherwise show the observed value with unit/scope/period |
| SCQA framework | Situation → Complication → Question → Answer |
| Pyramid principle | Conclusion first; core insight in title |
| Strategic coloring | Color serves information, not decoration |
| Chart vs Table | Trends → charts; precise values → tables |

- **Page elements**: gradient top bar + dark takeaway box, confidential marking + footer, MECE / driver tree / waterfall
- **Scenarios**: strategic decisions, deep analysis, MBB-level deliverables
- **Avoid**: unsupported comparisons/conclusions, subjective statements presented as source facts, decoration

---

## §4 Layout pattern library — reference


> **Principle — proportion follows information weight, not preset ratios.** Combine patterns, break the grid for `breathing` pages, or propose new patterns. Defaulting every page to symmetric grid produces the "AI-generated" look.

| Pattern | Suitable Scenarios | PPT 16:9 Reference Dimensions |
|--------|-------------------|-------------------------------|
| Single column centered | Covers, conclusions, key points | Content width 800-1000px, horizontally centered |
| Symmetric split (5:5) | Comparisons where two sides carry equal weight | Column ratio 1:1, gap 40-60px |
| Asymmetric split (3:7 / 2:8) | One side dominates — chart vs. takeaway, image vs. caption | Heavier side 840-1024px, lighter side 256-440px |
| Three-column | Parallel points, process steps | Column ratio 1:1:1, gap 30-40px |
| Four-quadrant / matrix | Two-axis classification, strategic quadrants | Quadrant 560x250px, gap 20-30px |
| Top-bottom split | Ultra-wide images + text, processes, timelines | Image full-width, text area >= 150px height |
| Z-pattern / waterfall | Storytelling, case studies — blocks alternate left/right | Guide eye in Z; 3-5 alternating blocks |
| Center-radiating | Core concept + surrounding nodes | Center element 200-300px, 4-6 satellite nodes |
| Full-bleed + floating text | `breathing` / feature pages | Image fills 1280x720, text floats over opacity overlay |
| Figure-text overlap | Hero moments — headline over/against image edge | Text partially overlaps image, not beside it |
| Negative-space-driven | Single element in 40-60% whitespace | One idea, weight through emptiness |

**PPT 16:9 (1280x720) key dimensions**: Safe area 1200x640 (40px margins); Title area 1200x100; Content area 1200x500; Footer area 1200x40.

---
