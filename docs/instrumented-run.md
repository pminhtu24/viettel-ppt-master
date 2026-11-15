# Instrumented runs: timing log + validation report

Test-only overlay (not loaded by SKILL.md; paste it into the test prompt) for runs where the user mandates instrumentation (timing markers, a validation report). It changes bookkeeping only — never the pipeline order or the quality gates. Apply it on top of the normal workflow whenever the user asks for timed markers or a `VALIDATION_REPORT.md`.

## timing.log

- Write markers to `<project_path>/timing.log` — inside the project, exactly the path the user names. Writing to the workspace root defeats the report, which reads the project path.
- One line per milestone, `<marker> <unix_epoch>`, appended the moment the milestone is reached:

```bash
echo "<marker> $(date +%s)" >> <project_path>/timing.log
```

- Never batch or backfill at the end: the log is the raw evidence for the duration table, and backfilled timestamps are wrong by construction.
- Use the agreed marker names verbatim. Cover intermediate states with the agreed name that actually matches, or explain a variant in the report — invented suffixes silently diverge from the vocabulary the report is parsed against.
- Default vocabulary (the user's message overrides when it lists its own):

| Pipeline point | Markers |
| --- | --- |
| Phase A | `phaseA_start`, `confirm_shown` (Confirmations displayed), `confirm_received`, `plan_written` (plan.md saved), `build_pass` (`spec_build.py build` plan gate pass) |
| Draw waves | `briefs_done`, `anchor_done` (anchor drawn + recorded); per draw wave N: `wave<N>_dispatch`, `wave<N>_collected` |
| Quality gates | `gate_start`, `chart_verify_done`, `chrome_done`, `final_scan_done` |
| Review | `fact_audit_done` (`fact_check.py audit` without errors), `review_recorded` (`content_check --record-review`) |
| Export | `export_done` |

- While a wave runs in the background, fill the report skeleton from `briefs/plan.json` (groups, page counts, brief paths) instead of polling transcripts.

## VALIDATION_REPORT.md

Write `<project_path>/VALIDATION_REPORT.md` after `export_done`. Compute every duration from consecutive `timing.log` markers (script the subtraction, don't do it by hand). Standard 12 sections:

1. Duration per segment (from timing.log) + total pipeline time
2. Briefs/plan.json summary: page count, anchor, groups, waves
3. Draw sub-agents: group, pages, status, api_calls, duration, remaining checker errors, files read beyond the brief
4. `page_plan.py verify` per wave + `record` output (raw JSON); note any content_errors
5. `spec_build.py build`: `--check` runs performed, errors found, `uncovered_sections_with_numbers`
6. `content_check --stage svg` first run: PASS/FAIL, errors
7. Checker sweep, initial vs final scan (errors/warnings)
8. Sample-page conformance: title, divider, footer, page numbers, cover/chapter/ending backgrounds
9. Charts: each sub-agent's `verify-charts` line + the main agent's re-check of its own chart pages
10. Review: `fact_check.py audit` errors per page and how they were fixed; `fact_check.py table` row count; pages failed in `draft-review`
11. Incidents (429/rate limit/timeout/interrupt) with the exact messages quoted
12. PPTX: path, size, slide count, slide order (list SVG filenames in order)

Export with the default path (no `-o`) so section 12 describes the real artifact location.
