---
name: viettel-ppt-master
description: >
  Viettel-branded presentation generation workflow that turns source materials
  (PDF, DOCX, URLs, Markdown) into polished SVG slides and PPTX decks through multi-role collaboration,prioritizing corporate-grade design, Viettel brand consistency, clean layouts,data storytelling, and executive-ready slide visuals. Use when user asks to "create PPT", "make presentation", "PPT", "deck slide", or mentions "viettel-ppt-master".
---

# PPT Master Skill

> AI-driven multi-format SVG content generation system. Converts source documents into high-quality SVG pages through multi-role collaboration and exports to PPTX.

**Core Pipeline**: `Source Document → Create Project → [Template] → Strategist → [Image_Generator] → Executor Live Preview → Quality Check → Post-processing → Export`

> [!CAUTION]
>
> ## 🚨 Global Execution Discipline (MANDATORY)
>
> **This workflow is a strict gated pipeline. The following rules have the highest priority — violating any one of them constitutes execution failure:**
>
> 1. **PHASE ORDER IS SERIAL** — Steps MUST be executed in order; the output of each step is the input for the next. Non-BLOCKING adjacent steps may proceed continuously once prerequisites are met, without waiting for the user to say "continue". Executor Step 6 may use controlled chapter-level parallelism only after all upstream gates and context snapshots exist
> 2. **BLOCKING = HARD STOP** — Steps marked ⛔ BLOCKING require a full stop; the AI MUST wait for an explicit user response before proceeding and MUST NOT make any decisions on behalf of the user
> 3. **NO CROSS-PHASE BUNDLING** — Cross-phase bundling is FORBIDDEN. (Note: the Eight Confirmations in Step 4 are ⛔ BLOCKING — the AI MUST present recommendations and wait for explicit user confirmation before proceeding. Once the user confirms, all subsequent non-BLOCKING steps — design spec output, SVG generation, speaker notes, and post-processing — may proceed automatically without further user confirmation)
> 4. **GATE BEFORE ENTRY** — Each Step has prerequisites (🚧 GATE) listed at the top; these MUST be verified before starting that Step
> 5. **NO SPECULATIVE EXECUTION** — "Pre-preparing" content for subsequent Steps is FORBIDDEN (e.g., writing SVG code during the Strategist phase)
> 6. **CONTROLLED SUB-AGENT SVG GENERATION ONLY** — Executor Step 6 SVG generation is context-dependent. Sub-agent SVG generation is FORBIDDEN unless `generation_mode=chapter_parallel` and `parallel_runtime=openclaw_subagents` are active, the runtime exposes `sessions_spawn`, each sub-agent receives exactly one package, uses isolated context, writes only to run-local staging, and the main agent merges + validates before export
> 7. **CHAPTER PARALLEL DEFAULT WITH AUDITED SERIAL FALLBACK** — In Executor Step 6, default generation is `generation_mode=chapter_parallel`, `parallel_runtime=auto`, `concurrency=2`. Executor MUST run the parallel preflight gate before the first SVG. Silent serial fallback is FORBIDDEN: fallback to `generation_mode=serial` only after recording the exact reason (`sessions_spawn` absent, `sessions_yield` absent, spawn failed before package work, or no eligible chapter package). Pages inside each chapter package remain sequential for visual continuity
> 8. **SPEC_LOCK RE-READ PER PAGE** — Before generating each SVG page, Executor MUST `read_file <project_path>/spec_lock.md`. All colors / fonts / icons / images MUST come from this file — no values from memory or invented on the fly. Executor MUST also look up the current page's `page_rhythm` (`anchor` / `dense` / `breathing`), optional `page_backgrounds` (section-only Viettel background layer, if any), `page_layouts` (which template SVG to inherit, if any), and `page_charts` (which chart template to adapt, if any). Empty / absent entries are intentional Strategist signals; missing `page_backgrounds` means no decorative background for that page — see executor-base.md §2.1. This rule exists to resist context-compression drift on long decks and to break the uniform "every page is a card grid" default
> 9. **SVG MUST BE HAND-WRITTEN, NOT SCRIPT-GENERATED** — Every SVG page is written directly by the active package author (main agent in serial mode, or the assigned isolated sub-agent in `openclaw_subagents` mode), one page at a time. Writing or running a Python / Node / shell script that produces the SVG files in batch — looping over pages, templating from data, or emitting them via a generator — is FORBIDDEN, including under "save tokens", "quick draft", or "user is in a hurry" pretexts. The script-generation path was tried on a feature branch and abandoned: cross-page visual consistency depends on per-page authoring with full upstream context, which a generator script cannot reproduce

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
> - Viettel red `#EE0033` is the brand accent. Deep blue `#12436D` is restricted to chart, diagram/infographic, and icon marks; never use it for text, backgrounds, cards, rails, footer, dividers, or decoration.
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
| `${SKILL_DIR}/scripts/image_gen.py`                | AI image generation (multi-provider)                                                                                                    |
| `${SKILL_DIR}/scripts/svg_quality_checker.py`      | SVG quality check                                                                                                                       |
| `${SKILL_DIR}/scripts/parallel_generation.py`      | Chapter-parallel planner, OpenClaw sub-agent prompt/staging preparer, staged output merger, and validator; does not generate SVG code    |
| `${SKILL_DIR}/scripts/total_md_split.py`           | Speaker notes splitting                                                                                                                 |
| `${SKILL_DIR}/scripts/finalize_svg.py`             | SVG post-processing (unified entry)                                                                                                     |
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
> references (`finalize_svg.py` skips them) and `svg_to_pptx.py` embeds them as
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

**Viettel brand lock**: for every normal run, present PPT 16:9, Viettel red `#EE0033`, white/approved-gray reporting surfaces, dark-neutral text, the locked family `"FS Magistral"` and its fixed weight roles, top-right logo slot, footer/page-number treatment, and content safe area as fixed decisions. Typography is informational in the confirmation set, not a user choice. Deep blue `#12436D` is chart/diagram/icon-only. `spec_lock.md` MUST record `brand.profile: viettel_default` and these values exactly. Only an explicit hard non-Viettel request may record `brand.profile: custom_override`.

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
- [ ] **Next**: Auto-proceed to [Image_Generator / Executor] phase
```

---

### Step 5: Image Acquisition Phase (Conditional)

🚧 **GATE**: Step 4 complete; Design Specification & Content Outline generated and user confirmed.

> **Trigger**: At least one row in the resource list has `Acquire Via: ai` and/or `Acquire Via: web`. If every row is `user` or `placeholder`, skip to Step 6.

**Always load the common framework**:

```
Read references/image-base.md
```

Then **lazy-load the path-specific reference** for each row that actually needs it:

| Acquire Via            | Load reference (only if any such row exists) | Run                                                                                             |
| ---------------------- | -------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `ai`                   | `references/image-generator.md`              | `python3 ${SKILL_DIR}/scripts/image_gen.py --manifest <project_path>/images/image_prompts.json` |
| `web`                  | `references/image-searcher.md`               | `python3 ${SKILL_DIR}/scripts/image_search.py ...`                                              |
| `user` / `placeholder` | (skip)                                       | (skip)                                                                                          |

A deck with only `ai` rows never loads `image-searcher.md`; a deck with only `web` rows never loads `image-generator.md`. A mixed deck loads both, processes each row through its own path, and writes both `image_prompts.json` and `image_sources.json`.

> ⚠️ **In-pipeline ai path MUST use manifest mode** — even when only 1 ai row exists. Write `images/image_prompts.json` first, then run `image_gen.py --manifest`, then `image_gen.py --render-md` to produce the `image_prompts.md` sidecar. The positional form (`image_gen.py "prompt" ...`) is reserved for **out-of-pipeline one-off testing / single-image fixups** — it skips manifest + sidecar, leaving no audit trail.

Workflow:

1. Extract all rows with `Status: Pending` and `Acquire Via ∈ {ai, web}` from the design spec
2. Generate prompts (ai rows) and/or run search (web rows) per [image-base.md](references/image-base.md) §2 dispatch table
3. Verify every row reaches a terminal status: `Generated` (ai success), `Sourced` (web success), or `Needs-Manual`

**✅ Checkpoint — Confirm acquisition attempted for every row**:

```markdown
## ✅ Image Acquisition Phase Complete

- [x] image_prompts.json created (when any ai rows processed)
- [x] image_prompts.md sidecar rendered (when any ai rows processed)
- [x] image_sources.json created (when any web rows processed)
- [x] Each row: status is `Generated` / `Sourced` / `Needs-Manual` (no `Pending` remaining)
```

**Default — auto-proceed to Step 6.** Only when the user's Step 4 response explicitly opted into split mode (in reply to the optional hint), output the Phase A hand-off below and stop this conversation:

```markdown
## ✅ Phase A Complete

- [x] Spec: `design_spec.md`, `spec_lock.md`
- [x] Resources: `sources/`, `images/`, `templates/`
- [ ] **Next**: open a fresh chat window and input `continue generation projects/<project_name>` to enter Phase B via the [`resume-execute`](workflows/resume-execute.md) workflow.
```

> On acquisition failure, do NOT halt — follow the Failure Handling rule in [image-base.md](references/image-base.md) §5: retry once, then mark the row `Needs-Manual`, report to user, and continue to the checkpoint above.

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

> ⚠️ **Controlled package authorship**: SVG generation stays in the main agent unless `generation_mode=chapter_parallel` selects `parallel_runtime=openclaw_subagents`. In that mode, sub-agents may author SVG only for their assigned package, in isolated context, into staging output, followed by main-agent merge + validation.
> ⚠️ **Generation rhythm**: default `generation_mode=chapter_parallel`, `parallel_runtime=auto`, `concurrency=2`. Use OpenClaw `sessions_spawn` only when the runtime exposes it; otherwise fallback to `generation_mode=serial`. Do not treat ad hoc page batches (e.g., 5 per group) as valid parallel mode.

**Generation Mode Selection (Mandatory)**:

- **Default / production**: `generation_mode=chapter_parallel`, `parallel_runtime=auto`, `concurrency=2`.
- **Fallback**: if `sessions_spawn` / `sessions_yield` are unavailable or fail before package work starts, set `generation_mode=serial` and generate through the existing one-agent path, but only after reporting the exact fallback reason.
- Before writing any SVG, run the parallel preflight commands:

```bash
python3 ${SKILL_DIR}/scripts/parallel_generation.py plan <project_path> --concurrency 2
python3 ${SKILL_DIR}/scripts/parallel_generation.py prepare-subagents <project_path> --concurrency 2
```

**Parallel Runtime Preflight Gate (Mandatory before the first SVG)**:

Report this checkpoint before generating any SVG:

```markdown
## Parallel Runtime Decision
- generation_mode: chapter_parallel
- parallel_runtime: openclaw_subagents | serial_fallback
- concurrency: 2
- run_id: <run_id or n/a>
- subagent_packages: <count>
- main_agent_packages: <count>
- fallback_reason: <none or exact reason>
```

- If `sessions_spawn` and `sessions_yield` are available and `subagent_packages > 0`, `parallel_runtime` MUST be `openclaw_subagents`.
- If either tool is unavailable, state exactly: `fallback_reason: sessions_spawn/sessions_yield unavailable in active runtime`.
- If a spawn call fails before package work starts, state the exact tool error and fallback to serial.
- Do not begin SVG generation in the main agent until this checkpoint is printed.

Use the generated `parallel_generation/` work packages as the chapter-level contract. Cover / TOC / ending packages remain main-agent packages. Chapter packages may run concurrently through `sessions_spawn`; pages inside one package stay serial. SVG files are still hand-written from the package context, never script-generated.

**OpenClaw Sub-Agent Spawn Pattern**:

- Spawn only groups listed in `<project_path>/parallel_generation/runs/<run_id>/run_manifest.json` under `subagent_groups`.
- Use isolated context and keep cleanup artifacts for debugging:

```js
sessions_spawn({
  task: "Read and execute the package prompt at <prompt_file>. Do not work outside that scope.",
  taskName: "<task_name>",
  runtime: "subagent",
  mode: "run",
  context: "isolated",
  cleanup: "keep",
  timeoutSeconds: 1800
})
```

- Spawn up to `concurrency=2`, then call `sessions_yield()`.
- After all sub-agents finish, merge staged package SVGs:

```bash
python3 ${SKILL_DIR}/scripts/parallel_generation.py merge <project_path> --run-id <run_id>
```

**Visual Construction Phase**:

- `serial`: generate SVG pages sequentially, one at a time, in one continuous pass → `<project_path>/svg_output/`
- `chapter_parallel` without sub-agent tools: generate packages in order in the main agent → `<project_path>/svg_output/`
- `chapter_parallel` with `openclaw_subagents`: main agent generates standalone packages to `<project_path>/svg_output/`; each sub-agent generates only its package to `<project_path>/parallel_generation/runs/<run_id>/work/<group_id>/svg_output/`; main agent merges after package reports pass.

**Per-page Quality Check Gate (Mandatory)** — after each SVG page is written, before generating the next page in the same serial/package stream:

```bash
python3 ${SKILL_DIR}/scripts/svg_quality_checker.py <project_path>/svg_output/<page_file>.svg
```

- Any `error` MUST be fixed on that page immediately before moving on.
- `warning` entries should be fixed when straightforward; otherwise leave them visible for the final full-project gate.

**Quality Check Gate (Mandatory)** — after all SVGs, BEFORE annotation handling and speaker notes:

```bash
python3 ${SKILL_DIR}/scripts/svg_quality_checker.py <project_path>
```

- Any `error` (banned SVG features, viewBox mismatch, spec_lock drift, text overflow, title-zone content intrusion, etc.) MUST be fixed before proceeding — return to Visual Construction, regenerate that page, re-run check.
- `warning` entries (low-res image, non-PPT-safe font tail, long text without a wrap contract, etc.): fix when straightforward, otherwise acknowledge and release.
- Run against `svg_output/` (not after `finalize_svg.py` — finalize rewrites SVG and masks violations).
- For `generation_mode=chapter_parallel`, merge staged package output first if using sub-agents, then run `python3 ${SKILL_DIR}/scripts/parallel_generation.py validate <project_path>` and fix any missing/duplicate/out-of-order slide or spec snapshot failure before export.

**Logic Construction Phase**: generate speaker notes → `<project_path>/notes/total.md`

**✅ Checkpoint — Confirm all SVGs and notes are fully generated and quality-checked. Proceed directly to Step 7 post-processing**:

```markdown
## ✅ Executor Phase Complete

- [x] Live preview started and kept available at the reported URL
- [x] All SVGs generated to svg_output/
- [x] svg_quality_checker.py passed (0 errors)
- [x] Speaker notes generated at notes/total.md
```

> **Chart pages?** If this deck contains data charts (bar / line / pie / radar / etc.), run the standalone [`verify-charts`](workflows/verify-charts.md) workflow before Step 7 to calibrate coordinates. AI models routinely introduce 10–50 px errors when mapping data to pixel positions; verify-charts eliminates that class of error. Skip if no chart pages.

---

### Step 7: Post-processing & Export

🚧 **GATE**: Step 6 complete; all SVGs generated to `svg_output/`; speaker notes `notes/total.md` generated.

🚧 **Image readiness GATE** (when Step 5 left ai rows in `Needs-Manual`): every expected file must exist at `project/images/<filename>` before running 7.1.

> If files are missing: PAUSE, list the missing filenames, point the user to `images/image_prompts.md` (each `### Image N:` block is paste-ready for ChatGPT / Gemini / Midjourney; auto-generated from `image_prompts.json`) and the required placement `project/images/<filename>`. Resume Step 7.1 only after all expected files are in place. `finalize_svg.py` and `svg_to_pptx.py` do not detect missing files at this layer — proceeding with gaps produces a deck with broken image references.

> ⚠️ Run the three sub-steps **one at a time** — each must complete successfully before the next.
> ❌ **NEVER** combine them into a single code block or shell invocation.

Canonical three-command pipeline (mirrors `references/shared-standards.md` §5):

**Step 7.1** — Split speaker notes:

```bash
python3 ${SKILL_DIR}/scripts/total_md_split.py <project_path>
```

**Step 7.2** — SVG post-processing (icon embedding / image crop & embed / text flattening / rounded rect to path):

```bash
python3 ${SKILL_DIR}/scripts/finalize_svg.py <project_path> --brand-chrome viettel --strip-comments
```

For an explicit `custom_override` run only, omit Viettel brand chrome:

```bash
python3 ${SKILL_DIR}/scripts/finalize_svg.py <project_path>
```

`--brand-chrome viettel` applies the logo layer to both `svg_output/` and `svg_final/`, so native PPTX export and SVG snapshot stay consistent. `--strip-comments` removes template XML comments, including non-visible Chinese notes from imported templates.

**Step 7.3** — Export PPTX (embeds speaker notes by default):

```bash
python3 ${SKILL_DIR}/scripts/svg_to_pptx.py <project_path>
# Output:
#   exports/<project_name>_<timestamp>.pptx           ← native pptx (canonical output, reads svg_output/)
#
# Add --svg-snapshot to also emit the SVG-image preview pptx + svg_output/ backup:
#   backup/<timestamp>/<project_name>_svg.pptx        ← SVG preview pptx (reads svg_final/)
#   backup/<timestamp>/svg_output/                    ← Executor SVG source backup
```

> The native pptx consumes `svg_output/` directly so the converter can preserve
> high-fidelity primitives (icon `<use>` placeholders, image `preserveAspectRatio`
> → `srcRect`, rounded rect `rx/ry` → `prstGeom roundRect`). The SVG snapshot is
> opt-in via `--svg-snapshot` — live preview already provides the SVG visual
> reference, so the snapshot pptx is only needed when you want a self-contained
> file to share or to rebuild without re-running the LLM. Pass `-s output` or
> `-s final` to force a single source if you need it.

**Optional animation flags** (the defaults already enable rich entrance animations — adjust only when the user asks for something different):

- `-t <effect>` — page transition. Default `fade`. Options: `fade` / `push` / `wipe` / `split` / `strips` / `cover` / `random` / `none`.
- `-a <effect>` — per-element entrance animation. Default `mixed` (auto-vary across the deck). Pass `none` to disable, or pick a specific effect like `fade`. Requires top-level `<g id="...">` groups (already required by Executor).
- `--animation-trigger {on-click,with-previous,after-previous}` — Start mode (matches PowerPoint's animation-pane Start dropdown). Default `after-previous` (click-free cascade; pace via `--animation-stagger`). Use `on-click` for presenter-paced reveals, or `with-previous` for all-at-once.
- `--animation-config <path>` — optional object-level sidecar. Default: `<project_path>/animations.json` when present.
- `--auto-advance <seconds>` — kiosk-style auto-play.

**Optional custom animations** (only when the user asks to tune animation order/effects/timing for specific objects):

Run the standalone [`customize-animations`](workflows/customize-animations.md) workflow. Default export already has global entrance animation; do not create `animations.json` unless object-level customization was requested.

**Optional recorded narration** (only when the user asks for narrated/video export):

Run the standalone [`generate-audio`](workflows/generate-audio.md) workflow. The AI picks a narration backend (`edge` by default, or a configured cloud provider such as ElevenLabs / MiniMax / Qwen / CosyVoice for high-quality or cloned voices), asks the user once (backend + voice + rate/settings + embed-or-not, all with recommended values), then executes `notes_to_audio.py` and (if chosen) re-exports the PPTX with `--recorded-narration audio`.

Do NOT call `notes_to_audio.py` directly without going through the workflow — `--voice` / `--voice-id` is required and the workflow produces the locale/provider-aware recommendation that makes the choice meaningful.

Full effect list, anchor logic, and limits: [`references/animations.md`](references/animations.md).

> ❌ **NEVER** substitute `cp` for `finalize_svg.py` — finalize performs multiple critical processing steps
> ❌ **NEVER** force `-s output` for the legacy/preview pptx (PowerPoint's internal SVG parser drops icons and rounded corners). The default auto-split already gives native the high-fidelity source it needs without touching legacy.

**Step 7.4 — Rendered Visual QA (Mandatory)**:

After PPTX export, render the produced PPTX to PDF/images and inspect the rendered slides before declaring completion:

```bash
python3 /home/tupham/.codex/skills/pptx/scripts/office/soffice.py --headless --convert-to pdf <output.pptx> --outdir <exports_dir>
pdftoppm -jpeg -r 120 <output.pdf> <exports_dir>/qa_slide
```

Review the generated slide images for text overflow, clipped labels, chart marks entering title/footer zones, and footer/source collisions. If any issue is found, fix the corresponding SVG in `svg_output/`, rerun `svg_quality_checker.py`, re-export, and rerender affected slides. Do not report success from SVG validation alone.

> ❌ **NEVER** use `--only` (it suppresses one of the two output files)

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

- Local preview: `python3 -m http.server -d <project_path>/svg_final 8000`
- **Troubleshooting**: on generation issues (layout overflow, export errors, blank images, etc.), check `docs/faq.md` for known solutions
