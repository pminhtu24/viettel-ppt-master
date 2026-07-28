---
name: viettel-ppt-master
description: >
  Viettel-branded presentation generation workflow that turns source materials
  (PDF, DOCX, URLs, Markdown) into polished SVG slides and PPTX decks through multi-role collaboration,prioritizing corporate-grade design, Viettel brand consistency, clean layouts,data storytelling, and executive-ready slide visuals. Use when user asks to "create PPT", "make presentation", "PPT", "deck slide", or mentions "viettel-ppt-master".
---

# PPT Master Skill

> Multi-role SVG presentation workflow. Converts source documents into high-quality SVG pages and exports them to PPTX.

**Core Pipeline**: `Source Document → Create Project → [Template] → Strategist → [Web Image Acquisition] → Executor Live Preview → Per-page Quality Gates → [Chart Verification] → Native PPTX Export → Rendered Visual QA`

> [!CAUTION]
>
> ## 🚨 Global Execution Discipline (MANDATORY)
>
> **This workflow is a strict serial pipeline. The following rules have the highest priority — violating any one of them constitutes execution failure:**
>
> 1. **SERIAL EXECUTION** — Steps MUST be executed in order; the output of each step is the input for the next. Non-BLOCKING adjacent steps may proceed continuously once prerequisites are met, without waiting for the user to say "continue"
> 2. **BLOCKING = HARD STOP** — Steps marked ⛔ BLOCKING require a full stop; the AI MUST wait for an explicit user response before proceeding and MUST NOT make any decisions on behalf of the user
> 3. **NO CROSS-PHASE BUNDLING** — Cross-phase bundling is FORBIDDEN. (Note: the Eight Confirmations in Step 4 are ⛔ BLOCKING — the AI MUST present recommendations and wait for explicit user confirmation before proceeding. Once the user confirms, all subsequent non-BLOCKING steps — design spec output, SVG generation, quality gates, and export — may proceed automatically without further user confirmation)
> 4. **GATE BEFORE ENTRY** — Each Step has prerequisites (🚧 GATE) listed at the top; these MUST be verified before starting that Step
> 5. **NO SPECULATIVE EXECUTION** — "Pre-preparing" content for subsequent Steps is FORBIDDEN (e.g., writing SVG code during the Strategist phase)
> 6. **NO SUB-AGENT SVG GENERATION** — Executor Step 6 SVG generation is context-dependent and MUST be completed by the current main agent end-to-end. Delegating page SVG generation to sub-agents is FORBIDDEN
> 7. **SEQUENTIAL PAGE GENERATION ONLY** — In Executor Step 6, after the global design context is confirmed, SVG pages MUST be generated sequentially page by page in one continuous pass. Grouped page batches (for example, 5 pages at a time) are FORBIDDEN
> 8. **SPEC_LOCK RE-READ PER PAGE** — Before generating each SVG page, Executor MUST `read_file <project_path>/spec_lock.md`. All colors / fonts / icons / images MUST come from this file — no values from memory or invented on the fly. Executor MUST also look up the current page's `page_rhythm` (`anchor` / `dense` / `breathing`), optional `page_backgrounds` (section-only Viettel background layer, if any), `page_layouts` (which template SVG to inherit, if any), and `page_charts` (which chart template to adapt, if any). Empty / absent entries are intentional Strategist signals; missing `page_backgrounds` means no decorative background for that page — see executor-base.md §2.1. This rule exists to resist context-compression drift on long decks and to break the uniform "every page is a card grid" default
> 9. **SVG MUST BE HAND-WRITTEN, NOT SCRIPT-GENERATED** — Every SVG page is written by the main agent directly, one page at a time (see rules 6 and 7). Writing or running a Python / Node / shell script that produces the SVG files in batch — looping over pages, templating from data, or emitting them via a generator — is FORBIDDEN, including under "save tokens", "quick draft", or "user is in a hurry" pretexts. The script-generation path was tried on a feature branch and abandoned: cross-page visual consistency depends on per-page authoring with full upstream context, which a generator script cannot reproduce
> 10. **PASS EACH PAGE BEFORE CONTINUING** — Immediately after writing each SVG, normalize deterministic Viettel chrome when applicable, run `svg_quality_checker.py` on that file, and fix every error before starting the next page. The cover is the first calibration gate; the first non-cover content/chart/KPI/table page is the normal-shell calibration gate. Still run the full-project quality gate after all pages

> [!IMPORTANT]
>
> ## 🌐 Language & Communication Rule
>
> - **Response language**: match the user's input and source materials. Explicit user override takes precedence.
> - **Template format**: `design_spec.md` MUST follow its original English template structure (section headings, field names) regardless of conversation language. Content values may be in the user's language.
> - **Viettel section rhythm**: when a Viettel deck has clear source headings or 8+ slides with multiple narrative blocks, Strategist should create meaningful section dividers from the source structure. These are the only normal pages that receive decorative backgrounds; dense content/chart/KPI/table pages keep the clean Viettel shell.

> [!IMPORTANT]
>
> ## 🔌 Compatibility With Generic Coding Skills
>
> - `viettel-ppt-master` is a repository-specific workflow, not a general application scaffold
> - Do NOT create `.worktrees/`, `tests/`, branch workflows, or generic engineering structure by default
> - On conflict with a generic coding skill, follow this skill unless the user explicitly says otherwise

> [!IMPORTANT]
>
> ## 🔒 Viettel Brand Default
>
> - Every normal run of this skill is a Viettel-branded PPT 16:9 run. Initialize with `--brand-profile viettel_default`; do not wait for a Viettel keyword.
> - Use `--brand-profile custom_override` only when the user explicitly says not to use Viettel, names another brand, or supplies an explicit non-Viettel template path. A color/font request alone is not an override.
> - This skill's typography is locked to the single family `"FS Magistral"` for every normal run.
> - During Eight Confirmations, state the typography lock for visibility; do not ask the user to choose or approve a typeface.
> - Use FS Magistral Bold (`font-weight="700"`) for cover/chapter/page titles, section and card headers, KPI/hero numbers, callouts, and highlighted text. Use Book/Regular (`400`) for body, descriptions, captions, sources, and footers; Medium (`500`) is reserved for secondary subtitles/labels.
> - Viettel red `#EE0033` is the brand accent. Deep blue `#12436D` is restricted to chart, diagram/infographic, icon marks, and cataloged builtin backgrounds whose `backgrounds_index.json` item explicitly sets `deep_blue_background: true`. Never use it for text, cards, rails, footer, dividers, ad-hoc backgrounds, or unregistered decoration.
> - Do NOT propose alternative brand colors, font combinations, typefaces, or competing templates unless the run is an explicit `custom_override`.
> - If the host lacks a Viettel font, keep the same declared stack and report `brand fidelity degraded`; do not silently substitute another design font in the recommendation or `spec_lock.md`.

## Main Pipeline Scripts

| Script                                             | Purpose                                                                                                                                 |
| -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `${SKILL_DIR}/scripts/source_to_md/pdf_to_md.py`   | PDF to Markdown                                                                                                                         |
| `${SKILL_DIR}/scripts/source_to_md/doc_to_md.py`   | Documents to Markdown — native Python for DOCX/HTML/EPUB/IPYNB, pandoc fallback for legacy formats (.doc/.odt/.rtf/.tex/.rst/.org/.typ) |
| `${SKILL_DIR}/scripts/source_to_md/excel_to_md.py` | Excel workbooks to Markdown — supports .xlsx/.xlsm; legacy .xls should be resaved as .xlsx                                              |
| `${SKILL_DIR}/scripts/source_to_md/ppt_to_md.py`   | PowerPoint to Markdown                                                                                                                  |
| `${SKILL_DIR}/scripts/source_to_md/web_to_md.py`   | Web page to Markdown (supports WeChat via `curl_cffi`)                                                                                  |
| `${SKILL_DIR}/scripts/project_manager.py`          | Project init / validate / manage                                                                                                        |
| `${SKILL_DIR}/scripts/analyze_images.py`           | Image analysis                                                                                                                          |
| `${SKILL_DIR}/scripts/image_search.py`             | Openly licensed web-image search with attribution metadata                                                                              |
| `${SKILL_DIR}/scripts/svg_quality_checker.py`      | SVG quality check                                                                                                                       |
| `${SKILL_DIR}/scripts/svg_to_pptx.py`              | Export to PPTX                                                                                                                          |
| `${SKILL_DIR}/scripts/update_spec.py`              | Propagate a `spec_lock.md` color / font_family change across all generated SVGs                                                         |
| `${SKILL_DIR}/scripts/check_fonts.py`              | Preflight host font availability, fallback usage, and local bundle install hints                                                        |

For complete tool documentation, see `${SKILL_DIR}/scripts/README.md`.

## Template Index

| Index                   | Path                                                | Purpose                                                                                                                     |
| ----------------------- | --------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Layout templates        | `${SKILL_DIR}/templates/layouts/layouts_index.json` | Query available page layout templates                                                                                       |
| Visualization templates | `${SKILL_DIR}/templates/charts/charts_index.json`   | Query available visualization SVG templates (charts, infographics, diagrams, frameworks)                                    |
| Icon library            | `${SKILL_DIR}/templates/icons/`                     | See `${SKILL_DIR}/templates/icons/README.md`; search icons on demand with `ls templates/icons/<library>/ \| grep <keyword>` |

Normal runs automatically install `${SKILL_DIR}/templates/layouts/viettel_default/`. This is a native SVG shell, not an HTML renderer, and keeps the Viettel logo fixed at the top-right of shell pages.

## Standalone Workflows

| Workflow               | Path                                | Purpose                                                                                                                                                                     |
| ---------------------- | ----------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `topic-research`       | `workflows/topic-research.md`       | Pre-pipeline — gather web sources when the user supplies only a topic with no source files                                                                                  |
| `create-template`      | `workflows/create-template.md`      | Standalone template creation workflow                                                                                                                                       |
| `resume-execute`       | `workflows/resume-execute.md`       | Phase B entry — resume execution in a fresh chat after Phase A (Step 1–5) completed in another session (split mode)                                                         |
| `verify-charts`        | `workflows/verify-charts.md`        | Chart coordinate calibration — run after SVG generation if the deck contains data charts                                                                                    |
| `customize-animations` | `workflows/customize-animations.md` | Object-level PPTX animation customization — run only when the user explicitly asks to tune animation order/effects/timing                                                   |
| `live-preview`         | `workflows/live-preview.md`         | Browser-based live preview — auto-started during generation and re-enterable any time the user mentions "live preview", "preview", or wants to click/select a slide element |

---

## Workflow

### Step 1: Source Content Processing

🚧 **GATE**: User has provided source material (PDF / DOCX / EPUB / URL / Markdown file / text description / conversation content — any form is acceptable).

> **No source content?** When the user supplies only a topic name or requirements without any file or substantive description, run the [`topic-research`](workflows/topic-research.md) workflow first, then return here with its products as input.

When the user provides non-Markdown content, convert immediately:

| User Provides                     | Command                                                                                                               |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| PDF file                          | `python3 ${SKILL_DIR}/scripts/source_to_md/pdf_to_md.py <file>`                                                       |
| DOCX / Word / Office document     | `python3 ${SKILL_DIR}/scripts/source_to_md/doc_to_md.py <file>`                                                       |
| XLSX / XLSM / Excel workbook      | `python3 ${SKILL_DIR}/scripts/source_to_md/excel_to_md.py <file>`                                                     |
| CSV / TSV                         | Read directly as plain-text table source                                                                              |
| PPTX / PowerPoint deck            | `python3 ${SKILL_DIR}/scripts/source_to_md/ppt_to_md.py <file>`                                                       |
| EPUB / HTML / LaTeX / RST / other | `python3 ${SKILL_DIR}/scripts/source_to_md/doc_to_md.py <file>`                                                       |
| Web link                          | `python3 ${SKILL_DIR}/scripts/source_to_md/web_to_md.py <URL>`                                                        |
| WeChat / high-security site       | `python3 ${SKILL_DIR}/scripts/source_to_md/web_to_md.py <URL>` (requires `curl_cffi`, included in `requirements.txt`) |
| Markdown                          | Read directly                                                                                                         |

> **Extracted source images are first-class slide assets**:
> converters save embedded/downloaded images beside the generated Markdown in
> `<source>_files/`. During `import-sources`, `project_manager.py` propagates those
> assets into `<project_path>/images/`, namespaces filenames by source, and merges
> metadata into `images/image_manifest.json`. A missing converter manifest MUST NOT
> prevent propagation; `project_manager.py` creates fallback metadata for discovered
> image files. Strategist treats propagated assets as `Acquire Via: user`,
> `Status: Existing`, analyzes them, and selects only report-relevant images.
>
> **Office vector assets (EMF/WMF) from DOCX/PPTX sources**:
> `doc_to_md.py` / `ppt_to_md.py` extract embedded Office vector images (.emf/.wmf)
> alongside bitmap images. After `import-sources`, these land in `images/`
> together with `image_manifest.json` and are first-class assets in §VIII Image Resource List.
>
> **Do NOT convert EMF/WMF to PNG.** The PPT Master pipeline preserves them as external
> references and `svg_to_pptx.py` embeds them as
> PPTX-native media via `image/x-emf` / `image/x-wmf` MIME — PowerPoint renders them at full vector fidelity.
> Converting via LibreOffice/Inkscape introduces CJK font substitution drift and
> rasterization loss; the original EMF/WMF is always higher fidelity than the converted PNG.
>
> Browser-based live preview cannot render EMF (will show blank) — this is expected;
> the PPTX output is the source of truth.

**✅ Checkpoint — Confirm source content is ready, proceed to Step 2.**

---

### Step 2: Project Initialization

🚧 **GATE**: Step 1 complete; source content is ready (Markdown file, user-provided text, or requirements described in conversation are all valid).

```bash
python3 ${SKILL_DIR}/scripts/project_manager.py init <project_name> --format ppt169 --brand-profile viettel_default
```

This skill is locked to `ppt169`. Use `--brand-profile custom_override` only for an explicit hard non-Viettel request; custom override still uses PPT 16:9.

Import source content (choose based on the situation):

| Situation                                   | Action                                                                                                    |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Has source files (PDF/MD/etc.)              | `python3 ${SKILL_DIR}/scripts/project_manager.py import-sources <project_path> <source_files...>`         |
| User provided text directly in conversation | No import needed — content is already in conversation context; subsequent steps can reference it directly |

> ℹ️ `import-sources` automatically selects the safe transfer mode — **no flag needed**:
> - **Binary source files** (PDF, DOCX, PPTX, images) outside the repo are **copied** into `sources/` — the original at `~/Downloads/` or elsewhere is never deleted.
> - **Derived `.md` files** (generated by Step 1 converters) are always **moved** into `sources/` regardless of location — they are temp artifacts, not originals.
> - Any file already inside the repo is moved to avoid accidental commits.
> Intermediate companion directories (e.g., `<stem>_files/`) are handled automatically.

**✅ Checkpoint — Confirm project structure created successfully, `sources/` contains all source files, converted materials are ready. Proceed to Step 3.**

---

### Step 3: Viettel Template Gate

🚧 **GATE**: Step 2 complete; project directory structure is ready and brand profile is known.

**Default — Viettel lock.** `project_manager.py init` MUST have installed `viettel_default` SVGs, `design_spec.md`, logo, and bundled fonts. Verify these assets exist before Step 4. Do NOT wait for Viettel keywords and do NOT query `layouts_index.json`.

**Hard override rule**:

- Explicit statements such as "do not use Viettel", a named different brand, or an explicit non-Viettel template path → re-initialize with `--brand-profile custom_override` and follow that explicit request.
- Requests for a different color, font, mood, or visual descriptor alone do NOT unlock the brand. Interpret compatible parts inside the Viettel design language and keep the lock.
- Normal Viettel pages may use adaptive/free composition inside the content safe area, but they are never brand-free: logo, typography, approved colors, and brand chrome remain mandatory.

**✅ Checkpoint — Confirm brand profile and required template assets are ready. Proceed to Step 4.**

---

### Step 4: Strategist Phase (MANDATORY — cannot be skipped)

🚧 **GATE**: Step 3 complete; Viettel template assets are installed, or an explicit `custom_override` is recorded.

First, read the role definition:

```
Read references/strategist.md
```

> ⚠️ **Mandatory gate**: before writing `design_spec.md`, Strategist MUST `read_file templates/design_spec_reference.md` and follow its full I–XI section structure. See `strategist.md` Section 1.

**Eight Confirmations** (full template: `templates/design_spec_reference.md`):

⛔ **BLOCKING**: present the Eight Confirmations as a single bundled recommendation set and **wait for explicit user confirmation or modification** before outputting Design Specification & Content Outline. This is the single core confirmation point — once confirmed, all subsequent steps proceed automatically.

1. Canvas format
2. Page count range
3. Target audience
4. Style objective
5. Color scheme
6. Icon usage approach
7. Typography plan (fixed FS Magistral family and weight rules; informational, not a font choice)
8. Image usage approach

**Viettel brand lock**: for every normal run, present PPT 16:9, Viettel red `#EE0033`, white/approved-gray reporting surfaces, dark-neutral text, the locked family `"FS Magistral"` and its fixed weight roles, top-right logo slot, footer/page-number treatment, and content safe area as fixed decisions. Typography is informational in the confirmation set, not a user choice. Deep blue `#12436D` is chart/diagram/icon-only except for cataloged builtin backgrounds explicitly marked `deep_blue_background: true`. `spec_lock.md` MUST record `brand.profile: viettel_default` and these values exactly. Only an explicit hard non-Viettel request may record `brand.profile: custom_override`.

**Font preflight (required for bundled brand fonts)**: after `spec_lock.md` is written, run:

```bash
python3 ${SKILL_DIR}/scripts/check_fonts.py <project_path>
```

- `installed` → proceed normally
- `fallback in use` / `missing` → continue generation, but tell the user `brand fidelity degraded`
- local bundle present in `<project_path>/fonts/` → tell the user the font is installable from the local bundle and ask explicit permission before attempting host installation
- default policy: do **not** auto-install fonts

**Mandatory — split-mode note** (not a ninth confirmation): after listing the eight confirmation details, you MUST append exactly one short line (rendered in the user's language, prefixed with 💡) about generation mode. Pick the variant by qualitative read of Phase A signals — recommended page count, source-material bulk, whether `topic-research` ran with substantial web-fetch accumulation:

| Signal read                                                            | Line content                                                                                                                                                                                                                                                                                                                   |
| ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Heavy (long page count / bulky sources / heavy web-fetch accumulation) | State estimated page count and large source size; recommend switching to [split mode](workflows/resume-execute.md) after Step 5 — stop this chat, open a fresh window and input `continue generation projects/<project_name>` to enter Phase B (SVG generation + export); no response or "continue" = default continuous mode. |
| Normal (default)                                                       | State scale is moderate, default continuous mode generates in one go; if mid-way window switch is desired, input `continue generation projects/<project_name>` after Step 5 to switch to [split mode](workflows/resume-execute.md).                                                                                            |

This line is required output every run — the user must always see the mode choice exists. Whether to act on it is the user's call.

If `<project_path>/images` contains any existing images, including assets extracted
from source documents, run analysis **before outputting the design spec**, unless the
user explicitly confirmed `No images`:

```bash
python3 ${SKILL_DIR}/scripts/analyze_images.py <project_path>/images
```

> ⚠️ **Image handling**: NEVER directly read / open / view image files (`.jpg`, `.png`, etc.).
> Use `analyze_images.py` output, `images/image_manifest.json`, source Markdown image
> references, or the Design Spec's Image Resource List. When a manifest exists, read it
> alongside the analysis to map extracted assets back to source pages / slides / URLs.

**Output**:

- `<project_path>/design_spec.md` — human-readable design narrative
- `<project_path>/spec_lock.md` — machine-readable execution contract (skeleton: `templates/spec_lock_reference.md`); Executor re-reads before every page

**✅ Checkpoint — Phase deliverables complete, auto-proceed to next step**:

```markdown
## ✅ Strategist Phase Complete

- [x] Eight Confirmations completed (user confirmed)
- [x] Split-mode note appended below the eight items (heavy or normal variant)
- [x] Design Specification & Content Outline generated
- [x] Execution lock (spec_lock.md) generated
- [ ] **Next**: Auto-proceed to [Web Image Acquisition / Executor] phase
```

---

### Step 5: Image Acquisition Phase (Conditional)

🚧 **GATE**: Step 4 complete; Design Specification & Content Outline generated and user confirmed.

> **Trigger**: At least one resource-list row has `Acquire Via: web`. If every row is `user` or `placeholder`, skip to Step 6.
>
> **Supported acquisition values**: `web`, `user`, and `placeholder`. AI image generation is not part of this skill. If the user requests a generated image, offer web sourcing, a user-provided file, or a placeholder.
>
> **Legacy rows whose `Acquire Via` value is `ai`**: when the referenced file already exists, change the row to `Acquire Via: user`, `Status: Existing`, then continue. If the file is absent, stop before Executor and ask the user to choose `web`, provide a file, or use `placeholder`. Never silently convert an AI intent into a web search.

Read `references/image-base.md` and `references/image-searcher.md`, then run `python3 ${SKILL_DIR}/scripts/image_search.py ...` for each pending web row. Skip `user` and `placeholder` rows.

Workflow:

1. Extract rows with `Status: Pending` and `Acquire Via: web` from the design spec
2. Run search per [image-base.md](references/image-base.md) and [image-searcher.md](references/image-searcher.md)
3. Verify every row reaches `Sourced` or `Needs-Manual`

Checkpoint: `image_sources.json` exists and every web row is `Sourced` or `Needs-Manual`; no `Pending` row remains.

**Default — auto-proceed to Step 6.** Only when the user's Step 4 response explicitly opted into split mode (in reply to the optional hint), output the Phase A hand-off below and stop this conversation:

```markdown
## ✅ Phase A Complete

- [x] Spec: `design_spec.md`, `spec_lock.md`
- [x] Resources: `sources/`, `images/`, `templates/`
- [ ] **Next**: open a fresh chat window and input `continue generation projects/<project_name>` to enter Phase B via the [`resume-execute`](workflows/resume-execute.md) workflow.
```

> On acquisition failure, do not halt — follow [image-base.md](references/image-base.md) §3: retry once, then mark the row `Needs-Manual`, report it, and continue.

---

### Step 6: Executor Phase

🚧 **GATE**: Step 4 (and Step 5 if triggered) complete; all prerequisite deliverables are ready.

Read the role definition based on the selected style:

```
Read references/executor-base.md          # REQUIRED: common guidelines
Read references/shared-standards.md       # REQUIRED: SVG/PPT technical constraints
Read references/executor-general.md       # General flexible style
Read references/executor-consultant.md    # Consulting style
Read references/executor-consultant-top.md # Top consulting style (MBB level)
```

> Only read executor-base + shared-standards + one style file.

**Design Parameter Confirmation (Mandatory)**: before the first SVG, output key design parameters from the spec (canvas dimensions, color scheme, font plan, body font size). See executor-base.md §2.

**Live Preview Auto-Startup (Mandatory)**: before the first SVG, automatically start the browser editor in live mode and keep it running continuously through Executor + Step 7 export:

```bash
python3 ${SKILL_DIR}/scripts/svg_editor/server.py <project_path> --live
```

- Start it immediately when Executor begins; `svg_output/` may be empty. Editor opens at `http://localhost:5050`; port conflict → `--port <other>` and report the actual URL.
- Run it as a long-running side process/session; do not wait for it to exit before generating SVG pages. Do not wait for user confirmation after startup.
- **Service must keep running** until one of: (a) the user clicks **Exit preview** in the browser, or (b) the user explicitly asks in chat to stop it. Generation continues even if the user closes the editor.
- **Do NOT read or apply submitted annotations during generation.** Users may annotate at any time, but Executor proceeds without touching them. The window to apply annotations opens only after Step 7 completes — see [`workflows/live-preview.md`](workflows/live-preview.md).
- UI button semantics and editor details: see [`workflows/live-preview.md`](workflows/live-preview.md) Notes.

**Pre-generation Batch Read (Mandatory)**: before the first SVG, batch-read every distinct background SVG referenced in optional `spec_lock.page_backgrounds`, every distinct layout SVG referenced in `spec_lock.page_layouts`, and every distinct chart SVG referenced in `spec_lock.page_charts` (plus any §VII backup charts). One read per file, up front — do not re-read these during page generation. See executor-base.md §1.0.

**Per-page spec_lock re-read (Mandatory)**: before **each** SVG page, `read_file <project_path>/spec_lock.md` and use only its colors / fonts / icons / images, plus the per-page `page_rhythm` / optional `page_backgrounds` / `page_layouts` / `page_charts` lookups (resolves to background/template/chart SVGs already loaded in the batch read above). Missing `page_backgrounds` means no decorative background for that page. Resists context-compression drift on long decks. See executor-base.md §2.1.

**Font-preflight gate (Mandatory for bundled brand fonts)**: before the first SVG page, if `<project_path>/fonts/` exists or `spec_lock.md typography` leads with a non-preinstalled brand font, run `python3 ${SKILL_DIR}/scripts/check_fonts.py <project_path>`. If the result is `fallback in use` or `missing`, surface `brand fidelity degraded` and continue only after making that runtime state explicit to the user. Installing from the local bundle is opt-in and requires explicit user approval.

> ⚠️ **Main-agent only**: SVG generation MUST stay in the current main agent — page design depends on full upstream context. Do NOT delegate to sub-agents.
> ⚠️ **Generation rhythm**: generate pages sequentially, one at a time, in the same continuous context. Do NOT batch (e.g., 5 per group).

**Visual Construction Phase**: generate SVG pages sequentially, one at a time, in one continuous pass → `<project_path>/svg_output/`

```bash
python3 ${SKILL_DIR}/scripts/apply_brand_chrome.py <project_path> --brand-chrome viettel --file svg_output/<page>.svg --slide-number <N>  # viettel_default only
python3 ${SKILL_DIR}/scripts/svg_quality_checker.py <project_path>/svg_output/<page>.svg
```

- After each page, run the commands above (`custom_override`: omit chrome normalization). This deterministic chrome step is allowed post-processing, not scripted page generation.
- Any `error` MUST be fixed and the same file re-checked before starting the next page. Treat the cover and first normal non-cover page as calibration gates.
- `warning` entries (low-res image, non-PPT-safe font tail, long text without a wrap contract, etc.): fix when straightforward, otherwise acknowledge and release.
- After all pages pass individually, chart decks run [`verify-charts`](workflows/verify-charts.md). If chart verification changes an SVG, re-run the per-file checker for that SVG before export. Non-chart decks proceed directly to export.

**✅ Checkpoint — Confirm all SVGs are fully generated and quality-checked. Proceed directly to export**:

```markdown
## ✅ Executor Phase Complete

- [x] Live preview started and kept available at the reported URL
- [x] All SVGs generated to svg_output/
- [x] svg_quality_checker.py passed (0 errors)
```

---

### Step 7: Native PPTX Export

🚧 **GATE**: Step 6 complete; every SVG in `svg_output/` passed its per-page gate, and chart verification passed when applicable.

```bash
python3 ${SKILL_DIR}/scripts/svg_to_pptx.py <project_path>
# Output:
#   exports/<project_name>_<timestamp>.pptx
```

The exporter reads `svg_output/` directly and produces editable native DrawingML.

**Optional animation flags** (the defaults already enable rich entrance animations — adjust only when the user asks for something different):

- `-t <effect>` — page transition. Default `fade`. Options: `fade` / `push` / `wipe` / `split` / `strips` / `cover` / `random` / `none`.
- `-a <effect>` — per-element entrance animation. Default `mixed` (auto-vary across the deck). Pass `none` to disable, or pick a specific effect like `fade`. Requires top-level `<g id="...">` groups (already required by Executor).
- `--animation-trigger {on-click,with-previous,after-previous}` — Start mode (matches PowerPoint's animation-pane Start dropdown). Default `after-previous` (click-free cascade; pace via `--animation-stagger`). Use `on-click` for presenter-paced reveals, or `with-previous` for all-at-once.
- `--animation-config <path>` — optional object-level sidecar. Default: `<project_path>/animations.json` when present.
- `--auto-advance <seconds>` — kiosk-style auto-play.

**Optional custom animations** (only when the user asks to tune animation order/effects/timing for specific objects):

Run the standalone [`customize-animations`](workflows/customize-animations.md) workflow. Default export already has global entrance animation; do not create `animations.json` unless object-level customization was requested.

Full effect list, anchor logic, and limits: [`references/animations.md`](references/animations.md).

**Step 7.1 — Rendered Visual QA (Mandatory)**:

After PPTX export, render the produced PPTX to PDF/images and inspect the rendered slides before declaring completion:

```bash
python3 /home/tupham/.codex/skills/pptx/scripts/office/soffice.py --headless --convert-to pdf <output.pptx> --outdir <exports_dir>
pdftoppm -jpeg -r 120 <output.pdf> <exports_dir>/qa_slide
```

Review the generated slide images for text overflow, clipped labels, chart marks entering title/footer zones, and footer/source collisions. If any issue is found, fix the corresponding SVG in `svg_output/`, rerun `svg_quality_checker.py`, re-export, and rerender affected slides. Do not report success from SVG validation alone.

> **Post-export annotation window**: the preview service from Step 6 typically remains running after export. If the user submitted annotations in the browser (during Executor or after export) and now asks to apply them — they may quote the browser prompt (`Annotations saved. ... apply my annotations`), say "apply my annotations" / "apply annotations" / equivalent — run [`live-preview`](workflows/live-preview.md) Step 2 to apply and re-export. Annotations submitted during generation are also handled here, not earlier.

> **Preview not running?** Any time the user mentions "live preview", "preview", "view preview", or wants to select/click a slide element and the service is not running, run [`live-preview`](workflows/live-preview.md) Step 1 to start it. If the service is already running, just point them at the URL — do not restart.

---

## Role Switching Protocol

Before switching roles, **MUST first read** the corresponding reference file. Output marker:

```markdown
## [Role Switch: <Role Name>]

📖 Reading role definition: references/<filename>.md
📋 Current task: <brief description>
```

---

## Reference Resources

| Resource                                                                           | Path                                  |
| ---------------------------------------------------------------------------------- | ------------------------------------- |
| Shared technical constraints                                                       | `references/shared-standards.md`      |
| Canvas format specification                                                        | `references/canvas-formats.md`        |
| Image-text layout patterns (Primary structures + Modifier layers — combine freely) | `references/image-layout-patterns.md` |
| Image layout sizing (math for side-by-side container dimensions)                   | `references/image-layout-spec.md`     |
| SVG image embedding                                                                | `references/svg-image-embedding.md`   |
| Icon library                                                                       | `templates/icons/README.md`           |

---

## Notes

- Local preview: `python3 -m http.server -d <project_path> 8000` then open `/svg_output/`
- **Troubleshooting**: on generation issues (layout overflow, export errors, blank images, etc.), check `docs/faq.md` for known solutions
