---
description: Phase B entry — resume PPT execution in a fresh chat after Phase A (SKILL.md Step 1-5) completed in a previous session. Reads project state from disk and runs Step 6 + Step 7 with no Phase-A context carry-over.
---

# Resume Execute Workflow

> Standalone Phase-B entry. Run when Phase A (SKILL.md Step 1–5) completed in a previous session and the user wants to continue with SVG generation + export. Loads project state from disk and runs Step 6 + Step 7 in a clean session.

This workflow is **independent**: it owns Phase B starting from a fresh chat — no upstream conversation context required. By isolating SVG generation in its own session, the model gains 20–40K context headroom by not carrying Phase A's eight-confirmation dialogue, image search/fetch results, or Strategist references.

## When to Run

The user opens a new chat and gives a phrase that names a project path and signals continuation. Recognize any of:

| Pattern | Example |
|---|---|
| "continue generation projects/<project_name>" | "continue generation projects/ppt169_joe_hisaishi" |
| "resume execution projects/<project_name>" | "resume execution projects/ppt169_joe_hisaishi" |
| Project path + any "continue / resume / finish this project" semantic | "finish projects/ppt169_joe_hisaishi" |

**Prerequisite**: Phase A must have completed in the named project. Verified by file presence in Step 1; do NOT auto-trigger Phase A on missing state.

---

## Step 1: Sanity check

Verify the project's Phase-A artifacts before doing anything else:

| File / Directory | Required when | Reason |
|---|---|---|
| `<project_path>/spec_lock.md` | Always | Strategist's execution contract; Executor reads it per page |
| `<project_path>/sources/source_index.json` and its referenced sources | Version-1 content contract | Exact evidence and source checksums |
| `<project_path>/design_spec.md` | Always | Section IX page outline; Executor cross-references it |
| `<project_path>/images/` | `spec_lock images` references any image | Images must exist for embedding |
| `<project_path>/templates/` | `spec_lock page_layouts` / `page_charts` references any | Layout / chart SVGs needed for batch read |

If any required artifact is missing → report which one(s) and stop. Do NOT auto-fall-back into Phase A; the user must either complete Phase A in the original session or explicitly restart.

---

## Step 2: Load SKILL.md and execute.md, proceed from Step 6

```
Read skills/viettel-ppt-master/SKILL.md
Read skills/viettel-ppt-master/workflows/execute.md   # Step 6 + Step 7
```

**Resume only what is not done — never redraw the whole deck by default.** Before Step 6, classify every page:

```bash
python3 ${SKILL_DIR}/scripts/page_plan.py status <project_path>
```

| Status | Meaning | Resume action |
|---|---|---|
| `done` | SVG recorded, bytes and page lock unchanged | Keep |
| `edited` | Bytes changed after recording, lock unchanged (manual edit, annotation) | Keep; re-check and re-review only. Never redraw without asking the user |
| `unknown` | SVG exists but was never recorded (pre-1.0.7 project, or interrupted before record) and passes the per-file checker | Keep; `page_plan.py record <project_path> --pages <ids>` |
| `missing` | No SVG | Draw |
| `broken` | XML does not parse, or the per-file checker reports errors | Redraw |
| `stale` | The page's content lock / page mappings changed since it was drawn | Redraw |
| `extra` | SVG not belonging to any slide in `design_spec.md` | Report; export is blocked until the user removes/renames it |

Show the user the status summary (one line per status). If nothing is `missing` / `broken` / `stale`, skip drawing and go straight to the quality gate. Redraw everything only when the user explicitly asks ("vẽ lại toàn bộ" / "regenerate all") — confirm first, because `edited` pages lose their manual changes.

Then run [`execute.md`](execute.md) Step 6 **for the selected pages only**:

- Read references (executor-base + shared-standards + chosen style file + image-layout-spec + svg-image-embedding)
- Design Parameter Confirmation
- Pre-generation Batch Read (layout / chart SVGs of the pages being drawn)
- `parallel`: `page_plan.py briefs <project_path> --only missing,broken,stale` → Parallel Generation Protocol; `sequential`: the main agent draws exactly those pages, recording each one
- Project quality gate on the whole deck, then chrome normalization (idempotent: already-normalized pages keep their bytes, so their review findings stay valid) and the final scan
- Chart verification when applicable; re-check only chart SVGs changed by verification
- `page_plan.py record <project_path> --pages all`, then the semantic review of `execute.md` (fact audit → review table → draft review); chart notes of unchanged pages are reused from the previous receipt
- Step 7: Native PPTX export (`svg_to_pptx`)

**Redraw one page** ("vẽ lại trang 7", layout rework): `page_plan.py briefs <project_path> --pages 7` → the main agent draws it from its brief (≥ 3 pages in `parallel` mode: one sub-agent wave) → chrome `--file` for that page → checker on that file → `page_plan.py record` → review only that page → export. **Content change** ("trang 7 sai số / thêm ý X"): change that slide in `plan.md` (its `blocks` / `data` lines) and run `spec_build.py build <project_path>`; the rebuild leaves the other locks byte-identical, so only that page becomes `stale` and follows the redraw path. Small text/visual tweaks on an existing page keep the [`live-preview`](live-preview.md) chat-edit / annotation path.

The fresh session pays the cost of re-reading references (~14K tokens) but earns back substantially more headroom by dropping Phase A's accumulated context. Net win in both window pressure and reasoning budget per page.

**Source materials are required:** Follow [content-grounding](../references/content-grounding.md). Load source index and per-page content locks; run `content_check.py <project_path> --stage plan`. Before each SVG read the page lock, exact source blocks (including table headers/context), and design lock. Do not enrich an outline with new facts. For legacy projects, ground all pages to be exported before continuing content generation; missing sources block affected content, not permission to infer from existing SVGs.

> Note: this workflow does NOT duplicate Step 6 / Step 7 content. SKILL.md + [`execute.md`](execute.md) are the authoritative procedure; resume-execute only adds the resumption entry (When to Run + Step 1 sanity check above) and the source-materials guidance above.

---

## Step 3: Hand-back

When Step 7 completes and `exports/<project_name>_<timestamp>.pptx` is produced, the workflow ends. Report the export path to the user.

If the deck contains data charts, the [`verify-charts`](verify-charts.md) workflow runs between Step 6 and Step 7 as documented in [`execute.md`](execute.md) — resume mode handles it the same way the continuous mode does.
