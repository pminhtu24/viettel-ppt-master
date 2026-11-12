# Role: Strategist

Read the source once, agree the deck with the user, and plan every slide in `plan.md`. The script `spec_build.py build` turns the plan into `design_spec.md`, `spec_lock.md` and the content locks; the Strategist never writes those by hand. The plan format and its content rules are in [page-plan.md](page-plan.md); this file covers the judgement: what to confirm, how to cut the source into slides, which template carries each slide.

> **Viettel brand gate (HARD rule)**: every normal run is `brand.profile: viettel_default` on PPT 16:9 — Viettel logo/chrome, FS Magistral, Viettel red `#EE0033`, white/approved-gray surfaces, dark-neutral text; deep blue `#12436D` only for chart, diagram/infographic and icon marks and cataloged backgrounds marked `deep_blue_background: true`. `custom_override` only when the user explicitly refuses Viettel, names another brand or supplies a non-Viettel template path — a color, font, mood or style request alone does not qualify (then read [strategist-options.md](strategist-options.md) §e §g).

## 1. Eight Confirmations — compact form

⛔ **BLOCKING**: one message, then wait. The fixed Viettel items take one line; only the five open items are recommendations. Template (render in the user's language):

```
Cố định theo nhận diện Viettel: PPT 16:9 · đỏ Viettel #EE0033, nền trắng/xám, chữ tối · FS Magistral Book/Medium/Bold · logo góc phải, footer, số trang.

1. Số trang: <N> — <vì sao: số phần lớn trong nguồn, mật độ số liệu>
2. Đối tượng và mục đích: <ai xem, để quyết định/nắm gì>
3. Phong cách: <A/B/C> + <mô tả ngắn>
4. Icon: <thư viện> — <vì sao>
5. Ảnh: <không / ảnh có sẵn trong nguồn / ảnh web / chỗ trống>
💡 <split-mode line>
💡 <generation-mode line>
```

- **Page count** — from the source: one slide per major block of content, chapter slides for major parts, cover and ending; dense reports land around 1 slide per 1–2 source sections. The user's number wins.
- **Style mode** (decides the Executor style file):

  | Mode | Focus | Typical deck |
  |---|---|---|
  | A) General Versatile | visual impact | public, clients, training, launches |
  | B) General Consulting | data clarity | progress reports, management reviews, proposals |
  | C) Top Consulting | logical persuasion | strategy, board decisions; SCQA, pyramid titles |

  Add a short visual descriptor (e.g. "báo cáo điều hành, tối giản") realised inside the Viettel palette.
- **Icon library** — exactly one stylistic library for the deck: `chunk-filled` (solid, angular, heavy), `tabler-filled` (solid, rounded, medium), `tabler-outline` (line art, light; screen use), `phosphor-duotone` (layered, contemporary). `simple-icons` only for real brand marks. Names go in `plan.md` later.
- **Images** — A none · B user/source-provided · C web-sourced · D placeholders (no AI generation). Images extracted from the source are existing assets: unless the user picks A, run `python3 ${SKILL_DIR}/scripts/analyze_images.py <project_path>/images` and use its output and `images/image_manifest.json`, never open image files. For B/C/D read [strategist-options.md](strategist-options.md) §h before planning image slides.
- **Typography** is fixed (FS Magistral); the plan's `density` picks the size profile: `dense` (body 20 px) for data reports and multi-block pages, `standard` (body 24 px) otherwise.

## 2. Cutting the source into slides

**Narrative by mode** — A: one theme per slide from the source; B: the source's own sections in order, data first, a neutral or conclusion title per slide; C: SCQA and pyramid order, assertion titles — but an assertion title is a claim and needs its blocks to say it. A neutral descriptive title is always valid.

**One slide, one job.** Each slide answers one question for the reader (`job:`). List the blocks that answer it (`blocks:`), in source order, from one source section where possible. Split a long section over two slides rather than crushing it; put "nice to have" blocks in `optional:`. Never merge sibling sections under one heading — a place, project, unit or deadline in a heading belongs to every figure under it.

**Chapters and rhythm.**
- Create chapter slides from the source structure when it has major parts or the deck has 8+ slides with distinct narrative blocks: 1–3 for 8–12 slides, 2–5 for 13+; one per major block, never before every small subsection, never an empty divider.
- `rhythm`: `anchor` for cover, chapter, agenda and ending; `breathing` for a single emphasis (hero number, quote); `dense` for everything else. Do not invent filler slides to vary the rhythm.
- `background` only on cover, chapter and ending slides — soft, low-intensity ids for chapters; `layout` only when the slide really follows a shell (`01_cover`, `02_chapter`, `02_toc`, `03_content*`, `04_ending`). Pair a `layout` with a `template` only when the shell fits the chart.

**Coverage.** `build` lists source sections with figures that no slide shows. Drop them on purpose (out of scope) or give them a slide; warnings and risks ("cảnh báo", "nguy cơ", overdue items) are rarely out of scope.

## 3. Choosing the template

Read `templates/charts/catalog.md` once. Choose by the data's shape first, then the message:

1. **Data shape** — numbers comparable across categories → comparison; achievement against a target or a stated percentage → progress; a series over time → time; dated milestones → milestones; one or a few headline figures → kpi; parts of one whole → composition (needs a hand-written lock, see page-plan.md rule 5).
2. **Structural pages count too** — agendas, steps, processes, frameworks (SWOT → `quadrant_text_bullets`, Porter → `hub_inward_arrows`, value chain → `chevron_chain_with_tail`), rosters, lists of tasks or incidents, plan-vs-actual grids (`metric_table`), grouped tables (`hierarchical_table`) all have `structure` templates. The most common miss is leaving these as plain text.
3. **Prefer the specific** template (`vertical_list` over `numbered_steps` when there is no order), one primary visualization per slide.
4. **Eligibility before beauty** — every mark needs a source number (`data:`), every chart a `why:`; never fill a quadrant, card or step the source does not supply; a single real KPI may use one card; when nothing fits, `template: none` and let the Executor compose.
5. Data-heavy reports normally put most numeric slides on a template; a numeric slide without one should be a deliberate choice.

The templates are brand-neutral starting structures: the Executor adapts composition, density and color to the Viettel shell; the Strategist only names the structure. Style-mode details and the layout pattern library: [strategist-options.md](strategist-options.md) §2, §4.

## 4. Hand-off

After `spec_build.py build` prints `"plan_gate": "pass"` and the font preflight ran, print one status line ("✅ Kế hoạch 30 slide đã build, plan gate đạt — chuyển sang vẽ") and **continue in the same turn** (SKILL.md Global rule 12) with Step 5 or Step 6.
