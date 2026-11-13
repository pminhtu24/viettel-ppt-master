---
description: SKILL.md Step 6 (Executor — live preview, SVG generation sequential or parallel, quality gate, chart verification, chrome, semantic review) and Step 7 (native PPTX export). Loaded when Executor starts, not during the Strategist phase.
---

# Execute: Step 6 and Step 7

> Part of the main [SKILL.md](../SKILL.md) pipeline, kept in its own file so the Strategist phase does not carry it in context. Read it once when Step 6 starts (also from [`resume-execute`](resume-execute.md)); the Global Execution Discipline in SKILL.md still applies.

### Step 6: Executor Phase

🚧 **GATE**: Step 4 (and Step 5 if triggered) complete; all prerequisite deliverables are ready.

Read the role definition based on the selected style:

```
Read ${SKILL_DIR}/references/executor-base.md          # REQUIRED: common guidelines
Read ${SKILL_DIR}/references/shared-standards.md       # REQUIRED: SVG/PPT technical constraints
Read ${SKILL_DIR}/references/executor-general.md       # General flexible style
Read ${SKILL_DIR}/references/executor-consultant.md    # Consulting style
Read ${SKILL_DIR}/references/executor-consultant-top.md # Top consulting style (MBB level)
```

> Only read executor-base + shared-standards + one style file. `parallel` mode: skip these reads — `briefs/_shared.md` carries the Viettel visual system (rule 10) and the confirmed style's block from them; the main agent draws the anchor from its brief and that file, exactly like a sub-agent page, and opens a specific section of executor-base / shared-standards only when a checker finding or the repair pass needs it.

**Design Parameter Confirmation (Mandatory)**: before the first SVG, output key design parameters from the spec (canvas dimensions, color scheme, font plan, body font size). See executor-base.md §2.

**Live Preview Auto-Startup (Best-effort, Mandatory attempt)**: before the first SVG, attempt to start the browser editor in live mode and keep it running through Executor + Step 7 export:

```bash
python3 ${SKILL_DIR}/scripts/svg_editor/server.py <project_path> --live
```

- Start it immediately when Executor begins; `svg_output/` may be empty. Editor opens at `http://localhost:5050`; port conflict → `--port <other>` and report the actual URL.
- Run it as a long-running background process; do not wait for it to exit before generating SVG pages.
- **Startup verification (do not block the pipeline)**: the server only prints `SVG Editor running at http://...` *after* the port is successfully bound, so that line is a reliable listening signal. Wait at most ~5 seconds for one of these outcomes:
  - `running at` line appears → preview is up; proceed to generate SVGs.
  - `flask not installed` line appears, or process exits with code `2` → flask is missing on this host. **Skip preview entirely** — no retry, no install attempt. Tell the user in one short line: `Live preview skipped — flask not installed (pip install flask to enable it next time)`. Continue generation.
  - `Error: cannot bind` line appears, or process exits with code `1` → port unavailable. Skip preview (or let the user pick another port manually); do not auto-retry in a loop. Continue generation.
  - No signal within ~5s → skip preview, continue generation.
- **Service must keep running** until one of: (a) the user clicks **Exit preview** in the browser, (b) the user explicitly asks in chat to stop it, or (c) it failed to start (handled above). Generation continues even if the user closes the editor or it never came up.
- **Do NOT read or apply submitted annotations during generation.** Users may annotate at any time, but Executor proceeds without touching them. The window to apply annotations opens only after Step 7 completes — see [`workflows/live-preview.md`](live-preview.md).
- UI button semantics and editor details: see [`workflows/live-preview.md`](live-preview.md) Notes.

**Pre-generation Batch Read (Mandatory)**: before the first SVG, batch-read every distinct background SVG referenced in optional `spec_lock.page_backgrounds`, every distinct layout SVG referenced in `spec_lock.page_layouts`, and every distinct chart SVG referenced in `spec_lock.page_charts` (plus any §VII backup charts). One read per file, up front — do not re-read these during page generation. See executor-base.md §1.0.

**Per-page spec_lock re-read (Mandatory)**: before **each** SVG page, `read_file <project_path>/spec_lock.md` and use only its colors / fonts / icons / images, plus the per-page `page_rhythm` / optional `page_backgrounds` / `page_layouts` / `page_charts` lookups (resolves to background/template/chart SVGs already loaded in the batch read above). Missing `page_backgrounds` means no decorative background for that page. Resists context-compression drift on long decks. See executor-base.md §2.1.

**Font-preflight gate**: Step 4's font preflight covers this step; run `python3 ${SKILL_DIR}/scripts/check_fonts.py <project_path>` again only when Step 4 ran in another session (resume) or the host changed. A still-missing face → `brand fidelity degraded`, continue with the exact locked family; export repeats installation and validation and always rejects Arial/Calibri/Aptos drift.

**Icon inventory**: `spec_build.py build` already checked every icon name of `plan.md`. Only after a hand edit of `spec_lock.md ## icons` run `python3 ${SKILL_DIR}/scripts/page_plan.py icons <project_path>` and apply its suggestions; never `ls`/`grep` the icon folders.

**Visual Construction Phase** → `<project_path>/svg_output/`. Branch on `spec_lock.md ## execution generation_mode` (missing → `sequential`):

- **`sequential`**: the main agent generates every page, one at a time, in page order. After each page passes `python3 ${SKILL_DIR}/scripts/page_plan.py check <project_path> --pages <NN>` (per-file checker + content bindings), run `python3 ${SKILL_DIR}/scripts/page_plan.py record <project_path> --pages <NN>` so an interrupted run can resume without redrawing it.
- **`parallel`**: follow the Parallel Generation Protocol below.

#### Parallel Generation Protocol

Sub-agents start cold and see only what their task context gives them; everything they need lives in project files. In this mode the Pre-generation Batch Read covers only the anchor page's templates (sub-agents read their own).

1. **Briefs + groups** — `python3 ${SKILL_DIR}/scripts/page_plan.py briefs <project_path> --lang <user language>`. It writes `briefs/_shared.md` once (rules, visual system, binding pattern, the deck style's block, shared spec_lock sections — every agent reads it once), `briefs/<PID>.md` per page (the page's verbatim content lock and template paths) and `briefs/plan.json` (anchor page, balanced contiguous groups — about 3 pages per group, up to `max_subagents` groups, never more than `max_pages_per_subagent` pages each, extra groups go to later waves — and the full task context for each group). Do not hand-write briefs.
2. **Anchor (main agent)** — if `plan.json anchor.needs_draw`, draw the anchor page from its brief — it sets the look every page copies, so give it the full rule-10 system (header divider, footer band, focal number, colored bars or cards, status colors where the source states them) — run `page_plan.py check <project_path> --pages <anchor>` until it reports nothing, then `page_plan.py record <project_path> --pages <anchor>`. Every sub-agent matches this page, and `page_plan.py check` compares every page's `viettel-brand-chrome` group with it — draw the anchor without chrome, then add the standard group with `python3 ${SKILL_DIR}/scripts/apply_brand_chrome.py <project_path> --brand-chrome viettel --file svg_output/<anchor file> --slide-number <N>` before its check; never copy chrome from another project's SVGs.
3. **Dispatch one wave** — one parallel sub-agent call **per group** (NetMind: one `delegate_task` call with a single task per group), passing that group's `context` from `plan.json` verbatim. Send every group's call in the **same turn** so all groups run at the same time; never put several groups in one call (the host then reports only when the whole batch ends, and a dead group goes unnoticed). If the host refuses a call because its concurrent-child limit is reached, send that group after the next group finishes. Then give the user one status line and **end the turn**; never poll transcripts or files. Remind the user not to save annotations in the live preview until generation finishes (the editor rewrites SVG files).
4. **Collect per group** — each group reports when it ends. Sub-agent summaries are self-reports — verify, never trust: run `page_plan.py verify <project_path> --wave <N>` when the last group of the wave has reported (it lists missing/broken pages, checker error counts, per-page content-binding errors, extra SVGs and any page outside the plan whose bytes changed). A group that failed before that is handled by step 5 right away, while the others keep running.
5. **Recovery (at most one retry per group)** — classify the failure from the task result:
   - quota / billing / auth (`402`, `insufficient_quota`, `TPM limit=0`, invalid key): do **not** retry. Record finished pages, tell the user the quota is exhausted, and stop; `continue generation projects/<name>` resumes later.
   - user interrupt (`/stop`, app closed): do not retry; report which pages are done. Resuming later draws only the pages `page_plan.py status` reports `missing` / `broken` / `stale`.
   - rate limit / overload (`429`, `503`): wait until the other groups of the wave have reported, then retry the failed groups with half as many concurrent calls.
   - timeout / died / missing or broken pages / > 3 files with checker or content errors: re-send that group's `context` from the same `plan.json` as one new call, adding one line: "Pages whose `page_plan.py check` already prints an empty list are done — keep their files and draw only the rest." Never re-run `briefs` while other groups are running (it rewrites `plan.json`), and never re-assign pages of a group that is still running.
   - still failing after the retry, or ≤ 3 files with errors: the main agent fixes or draws those pages itself, by hand, page by page (`page_plan.py check <project_path> --pages <PID>`); never repair bindings or tags across pages with a script; persistent failures become blockers (see below).
6. **Next wave** — repeat 3–5 for each remaining wave in `plan.json`.
7. **Record** — `page_plan.py record <project_path> --pages all` for every page that now passes the per-file checker and its content check; then continue with the project quality gate below. Cross-page consistency against the anchor (title positions, card/table/status styles, palette) is part of the main agent's repair pass.

Sub-agent ownership: each sub-agent may write only the SVG files listed in its context; briefs, `spec_lock.md`, `design_spec.md`, images, templates and other pages are read-only. Sub-agents never run the whole-project checker, `--export`, `apply_brand_chrome.py`, `content_check.py --record-review` or `svg_to_pptx.py`.

```bash
python3 ${SKILL_DIR}/scripts/svg_quality_checker.py <project_path>
```

- Run the initial project scan only after every SVG page has been generated.
- Treat `(rule code, SVG file, element locator)` as the stable finding fingerprint. Bounds/value changes do not create a new finding.
- Run the checker on the full project at most three times: **initial scan** → batch-fix all reported findings → **batch verification** → targeted per-file repair → post-chrome **final scan**. Between batch verification and the final scan, check only the SVG being repaired. Chart-verification re-checks do not count against these three generation scans.
- Fix in batches: native/XML/icon compatibility first, brand/font/palette/spec-lock second, then text overflow/title-zone. Do not reproduce `_estimate_svg_text_width()` or write inline scripts to expand/remap icons.
- Before chrome normalization, defer only missing top bar/logo/page-number findings that `apply_brand_chrome.py` can add deterministically. Duplicate chrome, logo-clearance, background, rail, palette, and font errors are never deferred.
- A fingerprint gets at most two direct repair attempts. If it persists, stop guessing and use its fallback once:
  - text overflow/title-zone: render the affected SVG/slide; fix confirmed visual breakage, or mark intentional layout with `data-allow-overflow="true"` on the text / `data-allow-title-zone="true"` on the shape or ancestor group;
  - brand/font/palette/spec-lock: inspect inherited attributes and brand chrome; annotations are forbidden;
  - unresolved icon/native element: choose an existing icon under `templates/icons/` or replace that one icon with SVG primitives; do not rewrite the deck in bulk;
  - XML/missing image: repair the exact structure/reference reported by the checker.
- If the same fingerprint remains after its fallback, record the file, locator, rule, and attempted fixes as a blocker; do not export and do not continue the loop.
- All non-deferred errors MUST be fixed before chart verification.
- `warning` entries (low-res image, non-PPT-safe font tail, long text without a wrap contract, etc.): fix when straightforward, otherwise acknowledge and release.
- After the project repair pass, chart decks run [`verify-charts`](verify-charts.md). `sequential`: every chart page. `parallel`: sub-agents already verified their own chart pages (their final answers carry the `verify-charts:` lines), so the main agent verifies only chart pages it drew itself (anchor, fallback pages) or changed after the wave record (`page_plan.py status` → `edited`); skip the rest. If chart verification changes an SVG, re-run the checker for that SVG.
- After chart verification (or immediately for non-chart decks), normalize `viettel_default` chrome once, then run the final full-project scan:

```bash
python3 ${SKILL_DIR}/scripts/apply_brand_chrome.py <project_path> --brand-chrome viettel
python3 ${SKILL_DIR}/scripts/svg_quality_checker.py <project_path>
```

Chrome normalization also removes marked background groups and near-full-height Viettel-red left rails from every page except cover, chapter, and ending before the final scan. `Processed 0 SVG file(s)` is normal when the pages already carry the anchor's `viettel-brand-chrome` group; the final scan confirms coverage, so do not re-run it.

- `custom_override` omits chrome normalization but still runs the final scan. The final project scan must report `0 errors` before native export.
- After the final scan, run `python3 ${SKILL_DIR}/scripts/page_plan.py record <project_path> --pages all` (chrome changed the bytes) and `page_plan.py status <project_path>`; any `extra` SVG blocks export until the user removes or renames it.

**Semantic review** ([content-grounding §5](../references/content-grounding.md)) — the main agent, both modes, no review sub-agents. After the final scan and record:

1. `python3 ${SKILL_DIR}/scripts/content_check.py <project_path> --stage svg`.
2. `python3 ${SKILL_DIR}/scripts/fact_check.py audit <project_path>` must list no `error`. Every number, period label, section name, status word, ratio and title count on a slide is traced to the source blocks its text is bound to. Fix each error on its page by hand (or one recovery call for that page) → `apply_brand_chrome.py --file svg_output/<file> --slide-number <N>` → `page_plan.py check` → `page_plan.py record` (`--accept-lock` when the fix updated that page's content lock from the source) → audit again.
3. `python3 ${SKILL_DIR}/scripts/fact_check.py table <project_path>` prints only the rows a machine could not settle (warnings and review rows), each slide text beside the source clause it is bound to. Read it once, in full. A row that misstates the source → fix that page as in step 2. A row that is right (a faithful summary, an allowed label) stays — it is recorded as judged.
4. Collect the sub-agents' `verify-charts:` lines (and your own, for pages you drew) into `reviews/charts.json` as `{"P07": {"v1": "<line>"}, …}`.
5. `python3 ${SKILL_DIR}/scripts/fact_check.py draft-review <project_path> --reviewer <your real model id> --charts <project_path>/reviews/charts.json` writes `reviews/draft.json`; it exits non-zero and names the pages that still have an error or a chart without a note — fix them, then draft again.
6. `content_check.py <project_path> --record-review reviews/draft.json`, then `--stage export`.

**✅ Checkpoint — Confirm all SVGs are fully generated and quality-checked. Proceed directly to export**:

```markdown
## ✅ Executor Phase Complete

- [x] Live preview startup attempted (running at the reported URL, or skipped if flask missing / bind failed)
- [x] All SVGs generated to svg_output/ (parallel: every wave verified with page_plan.py verify)
- [x] svg_quality_checker.py passed (0 errors); page_plan.py status shows no extra/broken/missing page
- [x] Semantic review recorded (content_check.py --stage export passes)
```

---

### Step 7: Native PPTX Export

🚧 **GATE**: Step 6 complete; the project quality check passed, chart verification passed when applicable, and `content_check.py <project_path> --stage export` passes with a current semantic review receipt. Follow [content-grounding §5](../references/content-grounding.md) to review and record it after final chrome normalization. Legacy export explicitly warns that content is unverified.

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

Run the standalone [`customize-animations`](customize-animations.md) workflow. Default export already has global entrance animation; do not create `animations.json` unless object-level customization was requested.

Full effect list, anchor logic, and limits: [`references/animations.md`](../references/animations.md).

> **Post-export annotation window**: the preview service from Step 6 typically remains running after export. If the user submitted annotations in the browser (during Executor or after export) and now asks to apply them — they may quote the browser prompt (`Annotations saved. ... apply my annotations`), say "apply my annotations" / "apply annotations" / equivalent — run [`live-preview`](live-preview.md) Step 2 to apply and re-export. Annotations submitted during generation are also handled here, not earlier.

> **Preview not running?** Any time the user mentions "live preview", "preview", "view preview", or wants to select/click a slide element and the service is not running, run [`live-preview`](live-preview.md) Step 1 to start it. If the service is already running, just point them at the URL — do not restart.

---

## Reference resources (Executor)

| Resource | Path |
|---|---|
| Shared technical constraints | `${SKILL_DIR}/references/shared-standards.md` |
| Canvas format specification | `${SKILL_DIR}/references/canvas-formats.md` |
| Image-text layout patterns (Primary structures + Modifier layers — combine freely) | `${SKILL_DIR}/references/image-layout-patterns.md` |
| Image layout sizing (math for side-by-side container dimensions) | `${SKILL_DIR}/references/image-layout-spec.md` |
| SVG image embedding | `${SKILL_DIR}/references/svg-image-embedding.md` |
| Icon library | `${SKILL_DIR}/templates/icons/README.md` |
