---
name: viettel-ppt-master
description: >
  Viettel-branded presentation generation workflow that turns source materials
  (PDF, DOCX, URLs, Markdown) into polished SVG slides and PPTX decks through multi-role collaboration,prioritizing corporate-grade design, Viettel brand consistency, clean layouts,data storytelling, and executive-ready slide visuals. Use when user asks to "create PPT", "make presentation", "PPT", "deck slide", or mentions "viettel-ppt-master".
---

# PPT Master Skill

> Multi-role SVG presentation workflow. Converts source documents into high-quality SVG pages and exports them to PPTX.

**Content integrity (mandatory for new decks):** every fact on a slide comes from a source block named in `plan.md`; `spec_build.py build` turns the plan into per-page content locks and runs the plan gate, `page_plan.py check` and `fact_check.py` trace each drawn page's numbers, period labels, section names and statuses back to those blocks, and the export gate needs a recorded semantic review. Wording is free; facts, comparisons, trends and causal claims the source does not state must not be added to fill a layout. A source that self-declares simulated or sample data ("SỐ LIỆU GIẢ LẬP", "dữ liệu mẫu") keeps that disclaimer visible on the cover — list the disclaimer block in the cover slide's `blocks:`; never drop or soften it.

**Core Pipeline**: `Source Document → Create Project → [Template] → Strategist → [Web Image Acquisition] → Executor Live Preview → Quality Check → [Chart Verification] → Native PPTX Export`

> [!CAUTION]
>
> ## 🚨 Global Execution Discipline (MANDATORY)
>
> 1. **SERIAL EXECUTION** — Steps run in order; each step's output is the next step's input. Non-blocking steps follow each other without waiting for "continue".
> 2. **BLOCKING = HARD STOP** — At a ⛔ BLOCKING step, stop and wait for the user's explicit reply; never decide for the user.
> 3. **ONE CONFIRMATION** — The Eight Confirmations (Step 4) are the only ⛔ gate of a normal run. After the reply, planning, SVG generation, quality gates and export proceed without asking again; the generation mode (💡 line, parallel by default) is settled in that same reply.
> 4. **GATE BEFORE ENTRY** — Verify each step's 🚧 GATE before starting it.
> 5. **NO SPECULATIVE EXECUTION** — Never prepare a later step's artifacts early (e.g. SVG during the Strategist phase).
> 6. **GENERATION MODE FOLLOWS `spec_lock.execution.generation_mode`** — `parallel`: the main agent draws one anchor page, sub-agents draw grouped pages from script-written briefs through the host's parallel sub-agent tool (NetMind: `delegate_task` — put each group's `context` from `briefs/plan.json` into the sub-agent's `context` field, never its `goal`; if every dispatch of the turn fails with the same host-side error (approval gate, model overload, child limit), stop dispatching for that turn, report, and re-send only the missing groups next turn), the main agent owns every whole-deck gate. `sequential` (or no `execution` section): the main agent draws every page. No sub-agent tool, or a refused delegation → `sequential`, said in one line.
> 7. **ONE PAGE AT A TIME PER AGENT** — Every agent writes its pages one by one, in page order; never several pages in one tool call or one templated pass.
> 8. **LOCK RE-READ PER PAGE** — Before each page re-read its brief (parallel) or `spec_lock.md` and the page's `page_rhythm` / `page_backgrounds` / `page_layouts` / `page_charts` (sequential). Colors, fonts, icons and images come only from the lock; an absent entry is an intentional signal (executor-base.md §2.1).
> 9. **SVG IS HAND-WRITTEN** — Every SVG page is written directly by an agent. Scripts may prepare text inputs and bookkeeping (`spec_build.py`, `page_plan.py`, `fact_check.py`) but never emit SVG; generating pages with a script — loops, data templating, generators — is forbidden under any pretext ("save tokens", "quick draft", "user is in a hurry").
> 10. **CHECK AFTER FULL-DECK GENERATION** — After every page exists, the main agent runs the project checker and repair pass, chart verification, Viettel chrome normalization and the final scan; export requires `0 errors`.
> 11. **SCRIPTS ARE TOOLS, NOT DOCUMENTATION** — Never open, `cat`, `sed`, `grep` or import the source of the skill's `scripts/*.py` to learn a format or decode an error. The references define every format and every check prints what to fix. If an error stays unclear, write it to `<project_path>/skill_feedback.md` and apply the closest documented rule.
> 12. **NO IDLE TURN END** — From the Eight Confirmations reply until export, never end a turn to report progress or to ask whether to continue. End it only while waiting for sub-agents (Step 6), at a ⛔ gate, on a recorded blocker, or when the quota is exhausted.

> [!IMPORTANT]
>
> ## 🔒 Viettel brand, language, scope
>
> - Every normal run is a Viettel-branded PPT 16:9 deck: initialize with `--brand-profile viettel_default` without waiting for a Viettel keyword. `--brand-profile custom_override` only when the user explicitly refuses Viettel, names another brand or supplies a non-Viettel template path; a color or font request alone is not an override. Never propose other brand colors, typefaces or competing templates in a normal run.
> - Typography is locked to three bundled static faces, stated in the confirmations but never offered as a choice: FS Magistral Bold (`FS Magistral-Bold.ttf`, SVG weight `700`: titles, KPIs, emphasis), Book (`FS Magistral-Book.ttf`, `400`/omitted: body, captions, sources), Medium (`FS Magistral-Medium.ttf`, `500`: subtitles, secondary labels). No synthetic bold, no Arial/Calibri substitution; PPTX writes the exact face name and embeds every face used. `check_fonts.py` finds or installs the faces (Windows: current user's Fonts directory and HKCU only); a face still missing → keep `"FS Magistral"`, report `brand fidelity degraded`; export hard-fails on a missing or invalid embedded payload.
> - Viettel red `#EE0033` is the accent. Deep blue `#12436D` only for chart, diagram/infographic and icon marks and cataloged backgrounds with `deep_blue_background: true` — never for text, cards, rails, footers, dividers or ad-hoc backgrounds.
> - Reply in the user's language (an explicit request wins); `design_spec.md` keeps its English headings and field names (the script writes them).
> - This is a repository workflow, not an application scaffold: never create `.worktrees/`, `tests/` or branch workflows by default. On a conflict with a generic coding or PPTX skill, follow this skill; the Viettel typography contract always wins.

## Scripts and templates

Pipeline scripts live in `${SKILL_DIR}/scripts/` (full list: `scripts/README.md`); the ones each step needs are named in that step. Chart and structure templates: `templates/charts/catalog.md` (index `charts_index.json`); icons: `templates/icons/<library>/`, chosen by name in `plan.md` and checked by `spec_build.py build`. Normal runs install `templates/layouts/viettel_default/`, a native SVG shell with the Viettel logo fixed top-right.

## Standalone Workflows

| Workflow | Path | Purpose |
|---|---|---|
| `topic-research` | `workflows/topic-research.md` | Pre-pipeline — gather web sources when the user supplies only a topic with no source files |
| `create-template` | `workflows/create-template.md` | Standalone template creation workflow |
| `resume-execute` | `workflows/resume-execute.md` | Phase B entry — resume execution in a fresh chat after Phase A (Step 1–5) completed in another session (split mode) |
| `verify-charts` | `workflows/verify-charts.md` | Chart coordinate calibration — run after SVG generation if the deck contains data charts |
| `customize-animations` | `workflows/customize-animations.md` | Object-level PPTX animation customization — run only when the user explicitly asks to tune animation order/effects/timing |
| `live-preview` | `workflows/live-preview.md` | Browser-based live preview — auto-started during generation and re-enterable any time the user mentions "live preview", "preview", or wants to click/select a slide element |

---

## Workflow

### Step 1: Source Content Processing

🚧 **GATE**: User has provided source material (PDF / DOCX / EPUB / URL / Markdown file / text description / conversation content — any form is acceptable).

> **No source content?** When the user supplies only a topic name or requirements without any file or substantive description, run the [`topic-research`](workflows/topic-research.md) workflow first, then return here with its products as input.

When the user provides non-Markdown content, convert immediately:

| User Provides | Command |
|---|---|
| PDF file | `python3 ${SKILL_DIR}/scripts/source_to_md/pdf_to_md.py <file>` |
| DOCX / Word / Office document | `python3 ${SKILL_DIR}/scripts/source_to_md/doc_to_md.py <file>` |
| XLSX / XLSM / Excel workbook | `python3 ${SKILL_DIR}/scripts/source_to_md/excel_to_md.py <file>` |
| CSV / TSV | Read directly as plain-text table source |
| PPTX / PowerPoint deck | `python3 ${SKILL_DIR}/scripts/source_to_md/ppt_to_md.py <file>` |
| EPUB / HTML / LaTeX / RST / other | `python3 ${SKILL_DIR}/scripts/source_to_md/doc_to_md.py <file>` |
| Web link | `python3 ${SKILL_DIR}/scripts/source_to_md/web_to_md.py <URL>` |
| WeChat / high-security site | `python3 ${SKILL_DIR}/scripts/source_to_md/web_to_md.py <URL>` (requires `curl_cffi`, included in `requirements.txt`) |
| Markdown | Read directly |

> **Extracted source images** (`<source>_files/`, including Office vector EMF/WMF) are first-class slide assets: `import-sources` copies them into `<project_path>/images/` with `images/image_manifest.json`. Keep EMF/WMF as they are — `svg_to_pptx.py` embeds them natively; never convert them to PNG (the browser preview shows them blank, the PPTX is the truth). Treat them as `Acquire Via: user`, `Status: Existing`.

**✅ Checkpoint — Confirm source content is ready, proceed to Step 2.**

---

### Step 2: Project Initialization

🚧 **GATE**: Step 1 complete; source content is ready (Markdown file, user-provided text, or requirements described in conversation are all valid).

```bash
python3 ${SKILL_DIR}/scripts/project_manager.py init <project_name> --format ppt169 --brand-profile viettel_default
```

This skill is locked to `ppt169`. Use `--brand-profile custom_override` only for an explicit hard non-Viettel request; custom override still uses PPT 16:9.

Import source content (choose based on the situation):

| Situation | Action |
|---|---|
| Has source files (PDF/MD/etc.) | `python3 ${SKILL_DIR}/scripts/project_manager.py import-sources <project_path> <source_files...>` |
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

Read the role definition and the plan format — for a Viettel deck without slide images nothing else is needed:

```
Read ${SKILL_DIR}/references/strategist.md
Read ${SKILL_DIR}/references/page-plan.md
```

| Only when | Also read |
|---|---|
| Explicit non-Viettel override | `references/strategist-options.md` §e §g, `templates/design_spec_reference.md`, `templates/spec_lock_reference.md` |
| Images go on slides (approach B/C/D) | `references/strategist-options.md` §h, `references/image-layout-patterns.md` |
| A content lock must be written by hand (composition chart, unusual data) | `references/content-grounding.md` §2–3 |
| No source file, only a topic | `workflows/topic-research.md` first |

**Read the source once** — `python3 ${SKILL_DIR}/scripts/source_index.py <project_path>` (only if `sources/source_index.json` is missing), then `python3 ${SKILL_DIR}/scripts/spec_build.py source <project_path>`: every block as `ID · text` under its section. Never read the Markdown source or dump blocks another way; every later step uses these IDs.

**Eight Confirmations** ⛔ **BLOCKING** — one bundled message, then wait for the user's confirmation or changes ([strategist.md](references/strategist.md) §1 gives the compact form):

- **Fixed by the Viettel brand (one line, not a choice)**: PPT 16:9; Viettel red `#EE0033` with white/approved-gray surfaces and dark-neutral text, deep blue `#12436D` only for chart/diagram/icon marks; FS Magistral Book/Medium/Bold; logo top-right, footer and page number. Only an explicit hard non-Viettel request may record `brand.profile: custom_override`.
- **To confirm**: page count, audience and purpose, style mode, icon library, image approach.

**Mandatory — split-mode note** (not a ninth confirmation): after listing the eight confirmation details, you MUST append exactly one short line (rendered in the user's language, prefixed with 💡) about generation mode. Pick the variant by qualitative read of Phase A signals — recommended page count, source-material bulk, whether `topic-research` ran with substantial web-fetch accumulation:

| Signal read | Line content |
|---|---|
| Heavy (long page count / bulky sources / heavy web-fetch accumulation) | State estimated page count and large source size; recommend switching to [split mode](workflows/resume-execute.md) after Step 5 — stop this chat, open a fresh window and input `continue generation projects/<project_name>` to enter Phase B (SVG generation + export); no response or "continue" = default continuous mode. |
| Normal (default) | State scale is moderate, default continuous mode generates in one go; if mid-way window switch is desired, input `continue generation projects/<project_name>` after Step 5 to switch to [split mode](workflows/resume-execute.md). |

This line is required output every run — the user must always see the mode choice exists. Whether to act on it is the user's call.

**Mandatory — generation-mode note** (not a ninth confirmation): directly after the split-mode line, append exactly one more 💡 line (user's language):

| Condition | Line content | `plan.md` value |
|---|---|---|
| Host exposes a parallel sub-agent tool (NetMind: `delegate_task`) and the deck has ≥ 6 pages | **Parallel (default)**: the main agent plans the slides and a script writes the content locks; after the main agent draws the anchor page, up to `max_subagents` (6) sub-agents draw and self-check their pages at the same time; reply "sequential" / "tuần tự" to draw pages one by one instead | `mode: parallel` |
| No parallel sub-agent tool on this host | Host has no sub-agent support → pages are drawn sequentially | `mode: sequential` |
| Deck < 6 pages | Small deck → pages are drawn sequentially | `mode: sequential` |

A reply of "sequential" / "tuần tự" / "làm lần lượt" (or equivalent) records `sequential`; any other confirmation keeps the line's default.

If `<project_path>/images` contains any existing images, including assets extracted
from source documents, run analysis **before outputting the design spec**, unless the
user explicitly confirmed `No images`. A spreadsheet or text-only source typically
extracts no images — when `images/` is empty, skip `analyze_images.py` (it fails on
an empty directory) and confirm `images: none` in the Eight Confirmations:

```bash
python3 ${SKILL_DIR}/scripts/analyze_images.py <project_path>/images
```

> ⚠️ **Image handling**: NEVER directly read / open / view image files (`.jpg`, `.png`, etc.).
> Use `analyze_images.py` output, `images/image_manifest.json`, source Markdown image
> references, or the Design Spec's Image Resource List. When a manifest exists, read it
> alongside the analysis to map extracted assets back to source pages / slides / URLs.

**After the confirmation — in the same turn (Global rule 12)**:

1. `Read ${SKILL_DIR}/templates/charts/catalog.md` — every chart and structure template, by the data it needs.
2. Write `<project_path>/plan.md` in one write ([page-plan.md](references/page-plan.md)); for more than 40 slides, one write per Part.
3. `python3 ${SKILL_DIR}/scripts/spec_build.py build <project_path> --check` lists every mistake at once (unknown block, a number not in its block, a missing role or `why`, an icon the library lacks); fix each in `plan.md` with a small edit and re-run until it prints `"ok": true`. Look at `uncovered_sections_with_numbers` and decide.
4. `python3 ${SKILL_DIR}/scripts/spec_build.py build <project_path>` writes `design_spec.md` and `spec_lock.md` (every content lock, the fixed Viettel sections, `page_*` maps, icons, `## execution`) and runs the plan gate; it must print `"plan_gate": "pass"`.
5. Font preflight: `python3 ${SKILL_DIR}/scripts/check_fonts.py <project_path>` (native Windows PowerShell: `py -3 …`). It finds or installs the three FS Magistral faces; a face still missing → report `brand fidelity degraded` and continue with the locked family.
6. One status line, then Step 5 (if a web image is needed) or Step 6.

**Output**: `plan.md` (written by Strategist); `design_spec.md` and `spec_lock.md` (written by `spec_build.py build`; never hand-edit a lock — change `plan.md` and build again).

**✅ Checkpoint — Phase deliverables complete, auto-proceed to next step**:

```markdown
## ✅ Strategist Phase Complete

- [x] Eight Confirmations completed (user confirmed), split-mode and generation-mode 💡 lines shown
- [x] plan.md written; `spec_build.py build` passed the plan gate
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

```
Read ${SKILL_DIR}/workflows/execute.md
```

Read it now and follow it for Step 6 (Executor role files, live preview, Icon inventory check, SVG generation — `sequential` or the Parallel Generation Protocol —, project quality gate, chart verification, chrome normalization, semantic review) and Step 7. It is part of this workflow, loaded only when Executor starts so the Strategist phase keeps a smaller context.

### Step 7: Native PPTX Export

🚧 **GATE**: Step 6 complete (see [`workflows/execute.md`](workflows/execute.md) Step 7). `python3 ${SKILL_DIR}/scripts/svg_to_pptx.py <project_path>` → `exports/<project_name>_<timestamp>.pptx`.

> **Post-export annotation window**: if the user submitted annotations in the browser and now asks to apply them (they may quote `Annotations saved. ... apply my annotations`), run [`live-preview`](workflows/live-preview.md) Step 2 to apply and re-export.

> **Preview not running?** When the user mentions "live preview" / "preview" or wants to click a slide element and the service is not running, run [`live-preview`](workflows/live-preview.md) Step 1; if it is running, give the URL — do not restart.

---

## Role Switching Protocol

Before switching roles, **MUST first read** the corresponding reference file. Output marker:

```markdown
## [Role Switch: <Role Name>]

📖 Reading role definition: references/<filename>.md
📋 Current task: <brief description>
```

---

## Notes

- Local preview: `python3 -m http.server -d <project_path> 8000` then open `/svg_output/`
- **Troubleshooting**: on generation issues (layout overflow, export errors, blank images, etc.), check `docs/faq.md` for known solutions
