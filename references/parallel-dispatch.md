# Parallel sub-agent dispatch on NetMind hosts

How to run the Parallel Generation Protocol's wave dispatch through NetMind's `delegate_task`, and the pitfalls that cost a wave.

## Call shape

- One `delegate_task` call per wave; its `tasks` array holds ONE entry per group — `goal` is a one-line group summary for the user, `context` is that group's `context` string from `briefs/plan.json` **verbatim**. Never paraphrase, shorten or rebuild it: every brief path, file-ownership rule, check command and output contract the cold sub-agent needs lives inside that string.
- A 4k-char context string is too long to retype reliably. Write each group's context to `briefs/ctx_<G>.txt` first, then copy it from the file into the `context` field — retyping from memory corrupts paths and silently strands the group on pages it was never told it owns.
- Send every group's task in the SAME `delegate_task` call, and one task per group — the host reports per task-entry; several groups in one entry report only when the whole batch ends and a dead group goes unnoticed.

## Anchor page

- The anchor is an ordinary page: write it from `briefs/<anchor>.md` + `briefs/_shared.md`, lifting the `viettel-brand-chrome` group (5px red top bar; logo `x=1088 y=28 width=128 height=42`; red page-number pill whose text carries `data-chrome="page-number"`) verbatim from the layout template `templates/layouts/viettel_default/03_content.svg` — then `page_plan.py check --pages <anchor>` prints an empty list without ever running `apply_brand_chrome.py`.
- On NetMind, `read_file` returns line-number-prefixed text and `write_file` refuses to write that display text back — when editing a page inside a code kernel, read and write with plain `open()`; round-tripping through the file helpers wastes a call per fix.

## After dispatch

- Give the user one status line (groups dispatched, anchor done) and end the turn; results re-enter as messages — never poll transcripts or artifact files.
- If the host app restarts mid-wave, background delegation results are lost but files written by sub-agents survive: `ls svg_output/`, read `page_state.json` / `page_plan.py status`, and re-dispatch only groups whose pages are still missing — do not redraw recorded pages.