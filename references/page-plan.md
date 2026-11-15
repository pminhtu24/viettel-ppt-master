# Page plan (`<project_path>/plan.md`)

The Strategist writes one short file that says, per slide, **which source blocks it shows** and, for data charts, **which source number drives each mark**. `spec_build.py build` writes `design_spec.md`, `spec_lock.md` and every content lock from it — quotes, index hash, SVG names, fact fields and the fixed Viettel sections are filled by the script, so they cannot be mistyped. Wording on the slides stays free; facts may only come from the blocks listed here.

## Workflow

```bash
python3 ${SKILL_DIR}/scripts/source_index.py <project_path>          # once, if sources/source_index.json is missing — check for it right after import-sources: a missing index makes `spec_build.py source` fail with FileNotFoundError
python3 ${SKILL_DIR}/scripts/spec_build.py source <project_path>     # read once: every block as `ID · text` under its section
Read ${SKILL_DIR}/templates/charts/catalog.md                        # every chart/structure template, one line each
# write <project_path>/plan.md (format below)
python3 ${SKILL_DIR}/scripts/spec_build.py build <project_path> --check   # every mistake in one list; nothing written
python3 ${SKILL_DIR}/scripts/spec_build.py build <project_path>           # writes the spec + lock and runs the plan gate — require `"plan_gate": "pass"`: a failed gate still writes spec files, so after fixing plan.md re-run build to overwrite the stale lock
```

Fix every error `build --check` lists in `plan.md` (one edit per error, never a rewrite of the file), re-run until it prints `"ok": true`, then `build`. Act on every warning too: change the template it names, move detail blocks to `optional`, or leave it with a reason you can state. `uncovered_sections_with_numbers` lists source sections with figures that no slide shows — leave them out on purpose or give them a slide in place of a lower-priority one (the slide count is fixed); never cram them into an existing slide.

## Format

```markdown
# Plan
- title: Báo cáo tình hình thực hiện nhiệm vụ tuần 34
- audience: Ban Tổng Giám đốc
- purpose: Báo cáo tuần — tiến độ chỉ tiêu, sự cố, nhiệm vụ trọng tâm
- style: B) General Consulting
- pages: 28                           # the slide count the user confirmed (or named in the request); build enforces it
- colors: KV1=#12436D, KV2=#28A197, KV3=#7C3AED   # optional: ≤ 6 entities that recur on ≥ 3 slides keep one color (not red)
- density: dense                      # dense (body 20px) | standard (body 24px)
- mode: parallel                      # the 💡 generation-mode line: parallel | sequential
- icons: tabler-filled: calendar, alert-triangle, flag, shield-check
- images: none

## Part 1: Thông tin nổi bật

### P01 Báo cáo tình hình thực hiện nhiệm vụ tuần 34
- rhythm: anchor
- layout: 01_cover
- background: bg_red_corner_sweep
- blocks: B0003-B0005

### P02 Hạ tầng 5G: hàng về cảng so với kế hoạch năm
- job: Mức hàng về cảng của ba nhóm thiết bị 5G so với kế hoạch năm
- template: bullet_chart
- blocks: B0024-B0027
- data: B0025 value=7.480/20.120 category="Hàng vô tuyến"
- data: B0026 value=10.144/20.929 category="Hàng cơ điện (DC)"
- data: B0027 value=12.505/20.513 category="Hàng SRT (IP)"
- why: ba nhóm hàng cùng đo lượng về cảng trên kế hoạch năm của cùng chương trình 5G
- optional: B0028

### P03 Các mốc hợp đồng OS 2027-2029
- template: timeline
- blocks: B0011-B0013
- why: các mốc ký hồ sơ của cùng một hợp đồng OS
```

| Key | Meaning |
|---|---|
| `title`, `audience`, `purpose`, `style` | §I of the Design Spec (from the confirmed Confirmations) |
| `density` | Typography profile: `dense` for data reports and multi-block pages, `standard` otherwise |
| `mode` | `parallel` or `sequential`, as confirmed in the 💡 generation-mode line |
| `icons` | `<library>: names` — one stylistic library (`chunk-filled`, `tabler-filled`, `tabler-outline`, `phosphor-duotone`); names are drawable objects (`bulb`, `target`, `trending-up`, `alert-triangle`), not concepts (`idea`, `growth`). The bundled icon sets are name subsets, not stock Tabler — common stock names (`target`, `trending-up`, `users`, `cpu`, `rocket`, `chart-bar`) can be absent from `tabler-filled`. Never guess: take names from the suggestion list a `build` error prints, or `ls templates/icons/<library>/` before writing the `icons:` line |
| `images` | `none`, or the image approach (images also need `strategist-options.md` §h) |
| `## Part N: …` | Chapter grouping of the slides that follow |
| `### P<NN> <title>` | One slide, numbered P01… in order; the title may summarise but its numbers and counts must come from its blocks |
| `job` | What the slide must make the reader understand (one line) |
| `rhythm` | `anchor` (cover, chapter, agenda, ending), `dense` (default), `breathing` (a single emphasis) |
| `layout` | Inherited Viettel shell: `01_cover`, `02_chapter`, `02_toc`, `03_content`, `03a_content_two_col`, `03b_content_image`, `03c_content_chart`, `04_ending` |
| `background` | Cover, chapter and ending pages only; an id from `${SKILL_DIR}/templates/layouts/viettel_default/backgrounds/backgrounds_index.json` (the skill copy; `init` copies the same file to `<project_path>/templates/backgrounds/`) |
| `template` | A key from `catalog.md`, or `none` |
| `blocks` | Source blocks the slide shows (`B0024-B0027, B0031`); each must appear on the slide |
| `optional` | Blocks shown only if there is room |
| `data` | One line per chart mark: `<block> value=<number as printed> [category="…"] [period="…"] [series="…"]`. Numbers are taken as printed: `43,90%`, `7.480`, `271.7K`, and ratios — `value=45/50` gives value 45 and, on progress/kpi templates, target 50 (`target=` may also be written). `category=` is the mark's label on every chart |
| `calc` | A number the source does not state, computed from source numbers: `<id> percent|ratio|sum|difference <block>:<n> <block>:<n>` |
| `why` | Required with every `template`: why the source supports it (same unit and period, parts of one whole, ordered stages; for a table, why a chart cannot show it) |

### Spreadsheet sources (`excel_to_md`)

- The unit line above a table ("Đơn vị: tỷ đồng …") and the header row ("Mảng kinh doanh | T1 | … | Lũy kế 9T | …") are their own blocks. A slide that prints the unit caption or a series/legend label like "Lũy kế 9T" must list those blocks in `blocks:` and bind the text to them — binding such labels to `c_label` alone fails the fact check (`editorial-number`, `period-invented`) because the number or period lives only in that block.
- Copy period labels verbatim from the header block's column names ("Lũy kế 9T", "Cùng kỳ 9T 2025"); do not compose "Lũy kế 9T 2026" from the year standing in the title.
- Count a table slide's `- data:` lines from the source's row and column counts before writing the plan. A 12-row × 5-column table will not fit under the ~900-character drawn-slide cap; decide before drawing — split it across two slides, or trim low-value columns (row numbers, priority marks) as a deliberate trade-off with a stated reason — never discover the density violation after the page is drawn.
- Every number on a slide stays bound to the block it comes from, including labels that ride along a row's value ("tăng 3,2%", "73,8% KH năm") — bind them to that row's block, never leave a number decorative; an unbound number escapes the fact check.
- Give every warning/observation block ("Cảnh báo", "Nhận xét") a home in the `blocks:` of the slide about its subject — a warning parked in `optional:` or left unlisted is flagged as a risk item no slide shows. Put a source disclaimer block ("SỐ LIỆU GIẢ LẬP …", "dữ liệu mẫu") in the cover slide's `blocks:` so it stays visible instead of being dropped.
- A wide monthly sheet (a column per month plus quarter, cumulative and comparison columns — 15+ columns) never fits a drawn table: trim it to the decision columns (Lũy kế, KH năm, % KH, Cùng kỳ, Tăng trưởng) and move the month/quarter detail to `optional` at plan time — the reader needs the cumulative picture, not every month.
- For a row-series chart (one row = one entity across months), reference one range block per row (`B0053-B0060` spans the month cells) instead of listing a separate block per cell.
- Block IDs jump over merged and empty cells (a 12-row table can span ~16 IDs); never compute an ID from a row position — take every ID from the `spec_build.py source` output.

Cover, chapter and ending slides (`rhythm: anchor` or `breathing`) may list no block. Title chapter slides `Chương N — <name>`; title the ending slide with its closing phrase (`Trân trọng cảm ơn!`), never "Trang kết".

## Content rules (checked by `build`, then by `fact_check` on the drawn slides)

1. **One slide, one source section per list item.** A card, row or column shows blocks of one section; never put a sibling section's figures under another section's heading (a place, project or unit in a heading must be the section of every number under it).
2. **Numbers as printed.** `data` and `calc` take numbers exactly as `spec_build.py source` prints them (`7.480`, `37%`, `271.7K`); the block must contain them. Period and scope labels (tháng, quý, lũy kế, năm, tuần) stay with their own number, from the same clause. In a chain of three or more numbers (`21/75/160 trạm ~46,88%` under a legend such as "TH tuần/lũy kế/KH tháng") the legend, not the position, says which two numbers pair: write `value=`/`target=` from the pair the percentage is computed from (`value=75 target=160`), never a pair cut by position (`21/75`).
3. **Statuses as the source says them.** "Chậm", "vượt", "đạt", "hoàn thành" appear only where the source says them, with their hedge ("nguy cơ chậm", "dự kiến hoàn thành", "chưa đạt").
4. **Counts are counts.** "7 nhiệm vụ" in a title equals the blocks listed; ratios keep their noun ("9/9 nhiệm vụ").
5. **Charts first where the data allows.** Choose by the data's shape (catalog family), then by message:
   - completion against a plan (`a/b ~x%`, `x% KH`) → `progress_bar_chart` (percentages) or `bullet_chart` (`value=a/b`); one headline ratio → `gauge_chart`; 2–8 headline figures → `kpi_cards` (the drawn page holds 4–6 cards — trim to the 6 the title names, split the rest onto their subject slides); one unit across categories → `bar_chart` / `horizontal_bar_chart`; dated milestones → `timeline` (blocks only); stages with drop-off → `funnel_chart`.
   - Tables are for data a chart cannot show — a source table, or rows with several columns of different measures. At most 2 slides may turn prose numbers into a table (`metric_table`, `consulting_table`, …); `build` stops at the third.
   - A deck whose slides carry numbers needs a data chart on at least one in three of them; `build` names candidate slides and the chart that fits.
   - Lists, steps and frameworks (`vertical_list`, `numbered_steps`, `quadrant_text_bullets` …) are for text items; vary them — no template on more than 4 slides.
   - A chart may be accompanied by a short supporting list or note on the same slide; it may not be replaced by a table to save a slide.
   - Never fill a template's slots with content the source does not have; `template: none` is valid. Composition charts (pie, donut, treemap, stacked) need explicit wholes, which `build` cannot write yet — use a comparison or progress chart, or write that page's lock by hand ([content-grounding](content-grounding.md) §2–3).
6. **Readable slides.** A slide's `blocks` hold at most 1.800 characters of source text (`build` warns above 1.200); a drawn slide shows at most 900 characters at ≥ 18px. Long sections become two slides, or move detail to `optional`. Slide titles and labels use the source's names — never a code or abbreviation the source does not write.

## Common `build` errors

| Error | Fix in `plan.md` |
|---|---|
| `'49%' is not a number of that block` | Copy the number from the `source` output of that block, or use the block that has it |
| `unknown block B0099` | Use an ID printed by `source` |
| `<template> needs '<role>=' on every data line` | Give every role the template lists in `catalog.md` |
| `its blocks hold N characters of source text` | Move detail blocks to `optional` or drop them (the count is fixed) |
| `the plan has N slides but the user confirmed M` | Return to M slides: merge or drop low-priority slides; ask the user before changing the count |
| `'XYZ' is nowhere in the source` | Write the name as the source does (no invented abbreviation) |
| `<table> — P.., P.. already show prose numbers as a table` | Use the chart the message names, a list or cards |
| `value=55743/75500 is not a number of that block` on a spreadsheet row | The slash ratio parses only when the source prints `a/b` as one token; an Excel row prints the two numbers in separate columns — write `value=55743 target=75500` |
| plan gate `Mixed units in one quantitative encoding` | Percent marks taken from a block whose own unit is a quantity (e.g. the growth column of a tỷ đồng revenue row) trip the gate — chart the underlying same-unit values (two series) instead of the percents |
| the table-limit error names a third table | The 2-table limit counts all table templates together (`metric_table` + `project_schedule_table` + …), not per template — convert one of them to a list or cards |
| `only N data chart(s) for M slides with numbers` | Change the named candidates to the chart in brackets |
| `<template> is a … chart: add one - data: line per mark` | Data charts need `data` lines; for a list use a `structure` template |
| `needs a - why: line` | One line on why the source supports the chart |
| `icon 'x' is not in <library>: use one of …` | Take a suggested name or drop the icon |
| `slides must be numbered P01…` | Renumber in order |
| plan gate `Waterfall anchors missing` | The waterfall template needs anchor columns the plan format cannot express — chart the chain differently: a revenue → cost → profit sequence draws as `kpi_cards` (one card per step), or hand-write that page's lock per [content-grounding](content-grounding.md) §2–3 |
