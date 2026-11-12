# Page plan (`<project_path>/plan.md`)

The Strategist writes one short file that says, per slide, **which source blocks it shows** and, for data charts, **which source number drives each mark**. `spec_build.py build` writes `design_spec.md`, `spec_lock.md` and every content lock from it — quotes, index hash, SVG names, fact fields and the fixed Viettel sections are filled by the script, so they cannot be mistyped. Wording on the slides stays free; facts may only come from the blocks listed here.

## Workflow

```bash
python3 ${SKILL_DIR}/scripts/source_index.py <project_path>          # once, if sources/source_index.json is missing
python3 ${SKILL_DIR}/scripts/spec_build.py source <project_path>     # read once: every block as `ID · text` under its section
Read ${SKILL_DIR}/templates/charts/catalog.md                        # every chart/structure template, one line each
# write <project_path>/plan.md (format below)
python3 ${SKILL_DIR}/scripts/spec_build.py build <project_path> --check   # every mistake in one list; nothing written
python3 ${SKILL_DIR}/scripts/spec_build.py build <project_path>           # writes the spec + lock and runs the plan gate
```

Fix every error `build --check` lists in `plan.md` (one edit per error, never a rewrite of the file), re-run until it prints `"ok": true`, then `build`. It also lists `uncovered_sections_with_numbers`: source sections with figures that no slide shows — add them to a slide or leave them out on purpose.

## Format

```markdown
# Plan
- title: Báo cáo tình hình thực hiện nhiệm vụ tuần 34
- audience: Ban Tổng Giám đốc
- purpose: Báo cáo tuần — tiến độ chỉ tiêu, sự cố, nhiệm vụ trọng tâm
- style: B) General Consulting
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
- template: progress_bar_chart
- blocks: B0024-B0027
- data: B0025 value=37%
- data: B0026 value=48%
- data: B0027 value=61%
- why: ba tỷ lệ cùng đo hàng về cảng trên kế hoạch năm của cùng chương trình 5G
- optional: B0028

### P03 Các mốc hợp đồng OS 2027-2029
- template: timeline
- blocks: B0011-B0013
- why: các mốc ký hồ sơ của cùng một hợp đồng OS
```

| Key | Meaning |
|---|---|
| `title`, `audience`, `purpose`, `style` | §I of the Design Spec (from the confirmed Eight Confirmations) |
| `density` | Typography profile: `dense` for data reports and multi-block pages, `standard` otherwise |
| `mode` | `parallel` or `sequential`, as confirmed in the 💡 generation-mode line |
| `icons` | `<library>: names` — one stylistic library (`chunk-filled`, `tabler-filled`, `tabler-outline`, `phosphor-duotone`); names are drawable objects (`bulb`, `target`, `trending-up`, `alert-triangle`), not concepts (`idea`, `growth`). `build` rejects names the library lacks and suggests real ones |
| `images` | `none`, or the image approach (images also need `strategist-options.md` §h) |
| `## Part N: …` | Chapter grouping of the slides that follow |
| `### P<NN> <title>` | One slide, numbered P01… in order; the title may summarise but its numbers and counts must come from its blocks |
| `job` | What the slide must make the reader understand (one line) |
| `rhythm` | `anchor` (cover, chapter, agenda, ending), `dense` (default), `breathing` (a single emphasis) |
| `layout` | Inherited Viettel shell: `01_cover`, `02_chapter`, `02_toc`, `03_content`, `03a_content_two_col`, `03b_content_image`, `03c_content_chart`, `04_ending` |
| `background` | Cover, chapter and ending pages only; an id from `templates/layouts/viettel_default/backgrounds/backgrounds_index.json` |
| `template` | A key from `catalog.md`, or `none` |
| `blocks` | Source blocks the slide shows (`B0024-B0027, B0031`); each must appear on the slide |
| `optional` | Blocks shown only if there is room |
| `data` | One line per chart mark: `<block> <role>=<number as printed> [category="…"] [period="…"] [series="…"]` |
| `calc` | A number the source does not state, computed from source numbers: `<id> percent|ratio|sum|difference <block>:<n> <block>:<n>` |
| `why` | One line: why the source supports the chart (same unit and period, parts of one whole, ordered stages …) |

Cover, chapter and ending slides (`rhythm: anchor` or `breathing`) may list no block.

## Content rules (checked by `build`, then by `fact_check` on the drawn slides)

1. **One slide, one source section per list item.** A card, row or column shows blocks of one section; never put a sibling section's figures under another section's heading (a place, project or unit in a heading must be the section of every number under it).
2. **Numbers as printed.** `data` and `calc` take numbers exactly as `spec_build.py source` prints them (`7.480`, `37%`, `271.7K`); the block must contain them. Period and scope labels (tháng, quý, lũy kế, năm, tuần) stay with their own number, from the same clause.
3. **Statuses as the source says them.** "Chậm", "vượt", "đạt", "hoàn thành" appear only where the source says them, with their hedge ("nguy cơ chậm", "dự kiến hoàn thành", "chưa đạt").
4. **Counts are counts.** "7 nhiệm vụ" in a title equals the blocks listed; ratios keep their noun ("9/9 nhiệm vụ").
5. **Charts follow the data.** Choose by the data's shape first (catalog family), then by message. `structure` templates (lists, steps, frameworks, tables) take blocks; every other family needs `data` lines and a `why`. Never fill a template's slots with content the source does not have; a single KPI may use one card; `template: none` is valid. Composition charts (pie, donut, treemap, stacked) need explicit wholes, which `build` cannot write yet — use a comparison or progress chart, or write that page's lock by hand ([content-grounding](content-grounding.md) §2–3).

## Common `build` errors

| Error | Fix in `plan.md` |
|---|---|
| `'49%' is not a number of that block` | Copy the number from the `source` output of that block, or use the block that has it |
| `unknown block B0099` | Use an ID printed by `source` |
| `<template> needs '<role>=' on every data line` | Give every role the template lists in `catalog.md` |
| `<template> is a … chart: add one - data: line per mark` | Data charts need `data` lines; for a list use a `structure` template |
| `needs a - why: line` | One line on why the source supports the chart |
| `icon 'x' is not in <library>: use one of …` | Take a suggested name or drop the icon |
| `slides must be numbered P01…` | Renumber in order |
