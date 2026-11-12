# Plan: Parallel sub-agent generation cho viettel-ppt-master

> **Trạng thái (2026-11-13): đã triển khai, thiết kế đã đổi so với bản kế hoạch gốc bên dưới.** Bản gốc giữ lại làm lịch sử; thiết kế hiện hành:
>
> - **Trước khi vẽ**: agent chính đọc nguồn một lần (`spec_build.py source`), chốt 8 xác nhận, viết `plan.md` (block nguồn + số liệu cho từng slide, [references/page-plan.md](../../references/page-plan.md)); `spec_build.py build` sinh `design_spec.md`, `spec_lock.md` và mọi content lock, chạy plan gate. Không còn sub-agent viết lock (đã thử ở run 2 và bỏ: chậm, sai ngữ nghĩa).
> - **Vẽ**: agent chính vẽ trang anchor (trang nội dung tiêu biểu), tối đa 6 sub-agent vẽ song song (~3 trang/nhóm, mỗi nhóm một `delegate_task`), mỗi trang tự kiểm bằng `page_plan.py check` (checker + binding + `fact_check`).
> - **Review**: không còn sub-agent review (mục D7 bên dưới đã bỏ). `fact_check.py audit` → bảng đối chiếu `fact_check.py table` do agent chính đọc → `fact_check.py draft-review` → `content_check --record-review`.
> - Số đo: run 2 (22 slide, lock song song) 104,5 phút; run 3 (30 slide, lock kiểu 1.0.6) 141 phút, 85 phút trước khi vẽ — lý do chuyển sang `plan.md` + `spec_build`.


> Trạng thái: **chờ duyệt** — chưa sửa file nào trong skill. Nhánh làm việc dự kiến: `feat/parallel-subagent`.
> Host mục tiêu: NetMind desktop (NetClaw `netmind_desktop_v1.1.3`), tool `delegate_task`, tối đa 10 child song song.
> Provider: GLM 5.3 Flash, dùng chung ~1.000 user → ưu tiên giảm context + kiểm soát tải đồng thời.

---

## 0. Bối cảnh và bằng chứng

**Spike đã chạy** (`~/Documents/netmind-demo/spike_parallel_bct34/SPIKE_REPORT.md`): 3 child × 2 trang BCT34.

| Kết quả | Số liệu |
|---|---|
| Song song thật | 3 child start lệch ≤ 13s, overlap 322–669s |
| Context child | Chỉ đọc brief + spec_lock + trang mẫu + template; **không cần SKILL.md/references** |
| Đồng nhất | 7/7 trang khớp khung với trang mẫu; 0 lệch palette/font |
| Lỗi | 6 trang child: 1 error. Trang mẫu do main vẽ: 2 error deep-blue |
| Điểm nghẽn | Main vẽ trang mẫu 914s + **soạn tay 6 brief 1.336s** > child vẽ 6 trang 800s |
| Child time | ~100% là model turnaround; có outlier 561s/trang (nghi retry do quá tải) |

**Kết luận dẫn dắt plan**
1. Phần tuần tự của main chiếm ~74% thời gian → phải cắt (brief do script sinh).
2. Context ngắn nhanh hơn rõ rệt lúc cao điểm: main tuần tự 20 trang ~120K token/request, 30 trang ~170K, 50 trang ~270K; child ~15–40K, không tăng theo độ dài deck.
3. Provider dùng chung → không mặc định 10 child; giới hạn cả số child lẫn số trang/child.

---

## 1. Phạm vi

**Đợt 1 (plan này)**
- ② Vẽ SVG song song + child tự check + `verify-charts` theo trang.
- ③ Semantic review song song (bắt buộc cho export version-1, hiện main làm tuần tự).
- Tối đa 1 lượt phụ song song mỗi đợt (cứu hộ/sửa lỗi).
- Chế độ sinh chọn trong Eight Confirmations: **parallel mặc định**, user chọn "tuần tự" → về chế độ cũ.

**Đợt 2+ (chỉ làm khi số đo đợt 1 chứng minh cần)**
- ① Content lock `design_spec.md` theo chương bằng child (gần như chắc chắn cần cho deck 30+ trang).
- Style kit thay trang mẫu do main vẽ (`anchor: kit`).
- Main làm "worker thứ 11" (vẽ bìa/chương/kết thúc trong lúc chờ).
- Topic research song song.
- Gộp review vào child vẽ (bỏ đợt review riêng) — chỉ xét nếu đợt review quá tốn.

---

## 2. Quyết định đã chốt

| # | Quyết định | Giá trị |
|---|---|---|
| D1 | Cách hỏi user | Dòng 💡 bắt buộc dưới Eight Confirmations (không phải mục thứ 9): "Song song (mặc định)… trả lời 'tuần tự' để vẽ lần lượt như cũ" |
| D2 | Tự chuyển `sequential` | Host không có `delegate_task`; deck < 6 trang; user chọn "tuần tự"; host từ chối giao việc lúc chạy |
| D3 | Tải đồng thời | `max_subagents: 6` (≤ giới hạn host 10); `max_pages_per_subagent: 6`; vượt → nhiều đợt, child mới cho mỗi đợt |
| D4 | Trang mẫu | `anchor: main` — main vẽ trang `dense` đầu tiên có chart/bảng, sửa đến 0 error |
| D5 | Child tự check | `svg_quality_checker.py <file>` + sửa ≤ 2 lần/fingerprint + `verify-charts` cho trang chart của mình |
| D6 | Chia nhóm | Trọng số trang, dải liên tục, ưu tiên cắt tại trang chương; trang khung (bìa/mục lục/chương/kết thúc) gom 1 nhóm |
| D7 | Review | Child **mới**, cùng cách chia nhóm với đợt vẽ. **Không review chéo** — child review luôn là agent khác child đã vẽ (receipt phải sau chrome, child vẽ đã kết thúc) |
| D8 | Lượt phụ | Tối đa 1 lượt song song phụ mỗi đợt; sau đó main tự xử lý; còn lỗi → blocker |

---

## 3. Luồng chạy: bản cũ vs bản mới

### 3.1 Bản cũ 1.0.6 (hiện tại — `sequential`)

Mọi việc sau Eight Confirmations do **một main agent** làm nối tiếp; context phình theo từng trang.

```
 +-----------------------------------------------+
 | Step 1-3  Source -> init -> template gate     |
 +-----------------------------------------------+
                        |
 +-----------------------------------------------+
 | Step 4    Eight Confirmations   [CHỜ USER]    |
 |           design_spec.md + spec_lock.md       |
 |           content_check --stage plan          |
 +-----------------------------------------------+
                        |
 +-----------------------------------------------+
 | Step 5    ảnh web (nếu có)                    |
 | Step 6    preview, batch read, check_fonts    |
 +-----------------------------------------------+
                        |
 ===================== MAIN (một agent, nối tiếp) =====================
                        |
   [main] re-read spec_lock -> vẽ trang 01          context ~ 30K
                        |
   [main] re-read spec_lock -> vẽ trang 02          context ~ 35K
                        |
   [main]  ...  (mỗi trang context lại dài thêm)  ...
                        |
   [main] re-read spec_lock -> vẽ trang N           context ~120K+
                        |
   [main] quét cả deck -> sửa từng lỗi (tối đa 3 lần quét)
                        |
   [main] verify-charts từng trang chart
                        |
   [main] apply_brand_chrome -> quét lần cuối (0 error)
                        |
   [main] semantic review trang 01 -> 02 -> ... -> N
                        |
   [main] record-review -> content_check --stage export
                        |
 ======================================================================
                        |
 +-----------------------------------------------+
 | Step 7    svg_to_pptx                         |
 +-----------------------------------------------+
```

Điểm nghẽn: vẽ N trang + sửa lỗi + verify-charts + review N trang đều nối tiếp trong cùng một context ngày càng dài (20 trang ~120K, 30 trang ~170K token/request).

### 3.2 Bản mới (`generation_mode: parallel`, mặc định)

Main chỉ làm việc toàn cục + chạy script; việc tăng theo số trang chia cho ≤ 6 child, mỗi child context sạch.

```
 +-----------------------------------------------+
 | Step 1-3  Source -> init -> template gate     |
 +-----------------------------------------------+
                        |
 +-----------------------------------------------+
 | Step 4    Eight Confirmations   [CHỜ USER]    |
 |           + dòng "Chế độ sinh: Song song      |
 |             (mặc định) / tuần tự"             |
 +-----------------------------------------------+
                        |
        +---------------+------------------------------+
        | parallel                                     | tuần tự / host không có
        |                                              | delegate_task / deck < 6 trang
        v                                              v
 +-----------------------------------------------+  +---------------------------+
 | design_spec.md + spec_lock.md (## execution)  |  | chạy luồng 1.0.6 (mục 3.1)|
 | content_check --stage plan                    |  +---------------------------+
 | Step 5  ảnh web (nếu có)                      |
 | Step 6  preview, batch read, check_fonts      |
 +-----------------------------------------------+
                        |
   [main]   vẽ 1 trang mẫu -> checker file đó -> 0 error
                        |
   (script) page_plan.py briefs -> briefs/NN.md + plan.json   (vài giây)
                        |
   [main]   1 lần delegate_task
                        |
 ========== ĐỢT VẼ  (song song, ≤ 6 child × ≤ 6 trang, context ~15-40K) ==========
      |            |            |            |            |            |
  +--------+  +--------+  +--------+  +--------+  +--------+  +--------+
  |child 1 |  |child 2 |  |child 3 |  |child 4 |  |child 5 |  |child 6 |
  |vẽ      |  |vẽ      |  |vẽ      |  |vẽ      |  |vẽ      |  |vẽ      |
  |tự check|  |tự check|  |tự check|  |tự check|  |tự check|  |tự check|
  |verify- |  |verify- |  |verify- |  |verify- |  |verify- |  |verify- |
  | charts |  | charts |  | charts |  | charts |  | charts |  | charts |
  +--------+  +--------+  +--------+  +--------+  +--------+  +--------+
      |            |            |            |            |            |
 ==================================================================================
                        |     (deck lớn hơn 6×6 trang -> đợt vẽ tiếp theo, child mới)
                        v
   [main]   kết thúc lượt, chờ kết quả (không poll) -> kiểm đủ file
                        |
        +---------------+-------------------------+
        | đủ                                      | thiếu trang / > 3 file lỗi
        |                                         v
        |                          {child} lượt phụ song song, 1 trang/child
        |                                         |
        +<----------------------------------------+
                        |
   [main]   quét cả deck -> sửa ít -> apply_brand_chrome
            -> quét lần cuối (0 error) -> content_check --stage svg
                        |
 ========== ĐỢT REVIEW  (song song, child MỚI, cùng cách chia nhóm) ==============
      |            |            |            |            |            |
  +--------+  +--------+  +--------+  +--------+  +--------+  +--------+
  |child 1'|  |child 2'|  |child 3'|  |child 4'|  |child 5'|  |child 6'|
  |review  |  |review  |  |review  |  |review  |  |review  |  |review  |
  |nhóm 1  |  |nhóm 2  |  |nhóm 3  |  |nhóm 4  |  |nhóm 5  |  |nhóm 6  |
  +--------+  +--------+  +--------+  +--------+  +--------+  +--------+
      |            |            |            |            |            |
 ==================================================================================
                        |
   (script) merge-reviews -> content_check --record-review
                        |
        +---------------+-------------------------+
        | pass                                    | có trang fail
        |                                         v
        |                          {child} lượt phụ sửa song song
        |                          [main]  review lại riêng trang đó
        |                                         |
        +<----------------------------------------+
                        |
   [main]   content_check --stage export
                        |
 +-----------------------------------------------+
 | Step 7    svg_to_pptx                         |
 +-----------------------------------------------+
```

Ký hiệu: `[main]` main agent, nối tiếp · `child` / `{child}` sub-agent, song song · `(script)` chạy script, vài giây.

### 3.3 So sánh nhanh

| Đoạn | 1.0.6 (tuần tự) | Bản mới (parallel) |
|---|---|---|
| Vẽ N trang | main, nối tiếp N trang | ≤ 6 child, mỗi child ≤ 6 trang, đồng thời |
| Context mỗi request | tăng dần tới ~120–270K | child ~15–40K, không tăng theo deck |
| Sửa lỗi checker / verify-charts | main, từng trang | child tự làm trên trang mình; main chỉ cổng toàn deck |
| Semantic review | main, từng trang | ≤ 6 child mới, đồng thời |
| Việc của main | toàn bộ | user, trang mẫu, script, gộp kết quả, cổng cuối |
| Host không có sub-agent | — | tự chạy luồng 1.0.6 |

### 3.4 Chi tiết luồng mới (dạng text)

```
Step 1–3  [main]  giữ nguyên
Step 4    [main]  Eight Confirmations + 💡 chế độ sinh (⛔ chờ user)
                  → design_spec.md + spec_lock.md (có ## execution)
                  → content_check --stage plan
Step 5    [main]  giữ nguyên (ảnh web nếu có)
Step 6    [main]  live preview, batch read, check_fonts
          [main]  vẽ trang mẫu → checker file đó → 0 error
          [main]  page_plan.py briefs → briefs/NN.md + briefs/plan.json
          [≤6]    ĐỢT VẼ (có thể nhiều đợt nếu vượt 6×6 trang):
                  vẽ từng trang → tự check → verify-charts → trả path + lỗi còn lại
          [main]  1 dòng trạng thái, kết thúc lượt, chờ (không poll) → kiểm đủ file
          [≤6]    (lượt phụ: trang thiếu/lỗi, hoặc >3 file lỗi sau quét deck)
          [main]  quét cả deck → sửa → apply_brand_chrome → quét lần cuối 0 error
          [main]  content_check --stage svg
          [≤6]    ĐỢT REVIEW (child mới): reviews/<group>.json theo schema §5
          [main]  page_plan.py merge-reviews → content_check --record-review
          [≤6]    (lượt phụ: sửa trang fail → main review lại riêng các trang đó)
          [main]  content_check --stage export
Step 7    [main]  svg_to_pptx.py
```

`generation_mode: sequential` → Step 6 + review giữ nguyên như 1.0.6.

**Ước lượng phần vẽ** (spike lúc quá tải: ~3,5 phút/trang + ~1,5 phút khởi động/child; `max_subagents: 6`):

| Deck | Trang nội dung | Chia | Thời gian đợt vẽ |
|---|---|---|---|
| 20 trang | ~17 | 3–4 child × 5–6 | ~20 phút |
| 30 trang | ~26 | 5 child × 5–6 | ~20 phút |
| 50 trang | ~45 | 8 nhóm × ~6 → 2 đợt (6 + 2) | ~40 phút |

---

## 4. Thay đổi theo file

### 4.1 `SKILL.md`
- **Rule 3**: chọn chế độ sinh nằm trong lần xác nhận duy nhất; sau đó không hỏi lại.
- **Rule 6** → "SVG generation follows `spec_lock.execution.generation_mode`": `parallel` chạy Protocol; `sequential` main vẽ toàn bộ; host thiếu/từ chối tool → `sequential` + báo 1 dòng.
- **Rule 7** → mỗi agent (main/child) vẽ từng trang một theo thứ tự, re-read brief/spec_lock trước mỗi trang; cấm nhiều trang/1 tool call.
- **Rule 9**: giữ cấm sinh SVG bằng script; nói rõ sinh brief/plan/gộp review bằng script là hợp lệ.
- **Rule 10**: sau đợt vẽ, main chạy cổng kiểm tra cho cả deck.
- **Step 4**: bảng 💡 chế độ sinh (3 biến thể: song song / host không hỗ trợ / deck nhỏ); ghi vào `spec_lock`; giữ nguyên dòng split-mode.
- **Step 6**: tách 2 nhánh; thêm **Parallel Generation Protocol** và **Parallel Semantic Review**.
- **Checkpoint**: Strategist "đã chốt chế độ sinh"; Executor "đủ trang từ child", "review receipt đã ghi".

### 4.2 `templates/spec_lock_reference.md`
```markdown
## execution
- generation_mode: parallel     # parallel | sequential
- max_subagents: 6              # ≤ host limit (NetMind: delegation.max_concurrent_children)
- max_pages_per_subagent: 6
- anchor: main                  # main (đợt 1); kit dành cho đợt 2
```
Thiếu section → coi là `sequential` (tương thích ngược project cũ).

### 4.3 `scripts/page_plan.py` (mới, stdlib, không sinh SVG)
- **`briefs <project> --anchor <svg>`**
  - Đọc `design_spec.md` (`#### Slide NN - …`) + `spec_lock.md`.
  - Ghi `briefs/NN.md` cho mỗi trang trừ trang mẫu, thứ tự nội dung để tối ưu cache provider (phần chung giống hệt nhau lên đầu):
    1. `page_brief_rules.md` (nguyên văn)
    2. Phần chung của `spec_lock` (colors, typography, text_fit, icons, forbidden)
    3. Phần riêng của trang: output path, rhythm/background/layout/chart, đường dẫn tuyệt đối template/chart/trang mẫu, **content lock nguyên văn**
  - Chia nhóm:
    - Trọng số: breathing/chương 0,5 · list 1,0 · bảng 1,3 · chart 1,5 (chỉnh theo số đo).
    - Dải liên tục; nhóm nặng nhất là nhẹ nhất (tìm kiếm nhị phân trên tải tối đa); ưu tiên cắt tại trang chương; trang khung gom 1 nhóm.
    - Ràng buộc: ≤ `max_pages_per_subagent` trang/nhóm; ≤ `max_subagents` nhóm/đợt; vượt → nhiều đợt.
  - Ghi `briefs/plan.json`: danh sách đợt → nhóm → trang; toàn văn `context` cho child vẽ và child review của mỗi nhóm.
- **`merge-reviews <project>`**: gộp `reviews/*.json` thành 1 findings JSON đúng schema §5; báo trang thiếu/fail.

### 4.4 `templates/page_brief_rules.md` (mới, ~15–20 dòng)
Chỉ chứa quy tắc **checker không bắt được**; mỗi dòng ghi nguồn (ví dụ `(executor-base §2.1)`):
- Content grounding: không thêm số/so sánh/xu hướng/nhân quả ngoài content lock; giữ nguyên "dự kiến/khoảng/kế hoạch…".
- `breathing` không dùng lưới card.
- 3–8 nhóm `<g id>` top-level (animation-ready).
- Chart: marker `chart-plot-area` (executor-base §3.1); geometry từ content lock, không từ nhãn hiển thị.
- Không vẽ chrome (top bar/logo/số trang) — `apply_brand_chrome` lo.

Không đưa vào: các quy tắc checker đã bắt (`brand-*`, `native-preflight`, `spec-lock-drift`, `text-*`, `title-zone`) — child tự check sẽ sửa; ràng buộc quy trình (chỉ ghi file của mình, không export, format trả về) — nằm trong `context` do `plan.json` sinh.

### 4.5 Reference / workflow
- `references/strategist.md`: dòng 💡 chế độ sinh trong quy trình Eight Confirmations.
- `references/executor-base.md` §2: ownership + rhythm theo 2 chế độ.
- `references/content-grounding.md` §5: review song song bằng child mới; `reviewer` = định danh model thật; gộp bằng `merge-reviews`; chỉ review sau chrome cuối (receipt khóa SHA256 từng SVG).
- `workflows/verify-charts.md`: chạy được cho danh sách trang (cho child).
- `workflows/resume-execute.md`: đọc `execution.generation_mode`, chạy đúng nhánh.

### 4.6 `scripts/test_page_plan.py` (mới — `/tests/` bị gitignore, test tracked nằm ở `scripts/test_*.py`)
- ≤ `max_subagents` nhóm/đợt; ≤ `max_pages_per_subagent` trang/nhóm; mỗi trang đúng 1 nhóm; nhóm liên tục; trang mẫu không trong nhóm nào.
- Cân bằng: nhóm nặng nhất ≤ 1,5× trung bình (khi có thể).
- Brief chứa content lock nguyên văn; phần chung giống hệt nhau giữa các brief.
- `merge-reviews` báo trang thiếu.

---

## 5. Khung `context` cho child (do `plan.json` sinh)

**Child vẽ**
- Đường dẫn tuyệt đối: `SKILL_DIR`, `<project>`, các brief của mình, `spec_lock.md`, trang mẫu.
- Quy trình: vẽ từng trang → `svg_quality_checker.py <file>` → sửa ≤ 2 lần → `verify-charts` cho trang chart.
- **Chỉ được ghi** đúng các file `output` liệt kê trong brief của mình; mọi file khác trong project **chỉ đọc** (mục 12).
- Cấm: đụng trang khác; chạy chrome/export; chạy checker toàn project; dùng `--export` cho checker.
- Trả về: đường dẫn tuyệt đối file đã ghi, lỗi còn lại, vấn đề content lock. Ngôn ngữ trả lời.

**Child review**
- Danh sách trang, SVG path, content lock, `source_index.py --show <block-id>`, schema §5.
- Không sửa SVG. Ghi `reviews/<group>.json`; trả path + danh sách trang fail.

---

## 6. Xử lý sự cố

### 6.1 Khi nào child bị lỗi (theo code NetClaw `tools/delegate_tool.py`, `delegate_tool_child_run.py`)

| Trạng thái child | Khi nào | Khả năng với GLM quá tải |
|---|---|---|
| `completed` | Làm xong, trả kết quả | Bình thường |
| `failed` / `error` | Provider lỗi sau khi đã hết retry (429, 5xx, overload, mất kết nối, sai credential); hoặc child kết thúc không có câu trả lời | **Cao nhất** |
| `timeout` | (a) `delegation.child_timeout_seconds` đã đặt và hết hạn (mặc định **tắt**); (b) heartbeat báo treo: 450s không hoạt động (`_HEARTBEAT_STALE_CYCLES_IDLE`) hoặc 1.200s kẹt cùng một tool (`_IN_TOOL`) → dừng mềm, chờ ân hạn, rồi báo timeout | Trung bình. Model chậm nhưng **vẫn đang trả lời** thì không bị coi là treo |
| `interrupted` | User `/stop`, `/new`, đóng app | Do user |
| `max_iterations` (`exit_reason`) | Hết 250 vòng tool; có tóm tắt → `completed` + `truncated: true`, không có → `failed` | Thấp (≤ 6 trang/child) |
| **"Xong giả"** | Child báo `completed` nhưng thiếu file / sai tên / còn lỗi — NetClaw **không** phát hiện (kết quả child là tự báo cáo) | `page_plan.py verify` bắt |

### 6.2 Skill xử lý theo từng trường hợp

| Tình huống | Xử lý |
|---|---|
| Host không có `delegate_task` / từ chối giao việc | → `sequential`, báo 1 dòng |
| `completed` + verify đạt | Đi tiếp |
| `completed` nhưng verify báo thiếu/sai tên/còn lỗi | Đưa các trang đó vào lượt phụ |
| `failed` do rate limit / quá tải | Lượt phụ với **số child giảm một nửa** |
| `failed` do **hết quota / billing / 402 / auth** | **Không chạy lượt phụ** (sẽ lỗi y hệt). Ghi `page_state`, báo user rõ "hết quota", trang đã xong được giữ; sau đó `continue generation` chạy tiếp đúng chỗ dừng (mục 11) |
| `timeout` | Lượt phụ, 1 trang/child |
| `interrupted` | Không tự chạy lại; báo trang nào đã xong / chưa xong; `continue generation` để chạy tiếp |
| > 3 file còn lỗi sau quét deck | Lượt sửa song song (file + findings); ≤ 3 file → main sửa |
| Review có trang fail | Lượt sửa song song → main review lại riêng các trang đó; finding còn hợp lệ giữ nguyên |
| Lượt phụ vẫn còn trang lỗi | Main tự vẽ trang đó; vẫn lỗi → ghi blocker |

---

## 7. Kiểm tra trước khi sửa

1. **GitNexus impact** cho hàm parse `spec_lock` trong `svg_quality_checker.py`, `update_spec.py`, `content_check.py` — section `## execution` mới có làm hỏng parser không. HIGH/CRITICAL → báo trước khi sửa.
2. Định dạng input của `content_check.py --record-review` → để `merge-reviews` xuất đúng.
3. `verify-charts` / `svg_position_calculator.py` chạy được theo từng trang.
4. ~~`apply_brand_chrome.py` có chạy theo file không~~ → **đã xác nhận**: có `--file svg_output/<file> --slide-number <N>` (dùng cho mục 11). Còn cần kiểm tra: chạy lại trên trang đã chuẩn hoá có giữ nguyên bytes không (idempotent).
5. `content_review.json`: cấu trúc hash theo từng SVG → để `page_plan.py` giữ lại finding của trang không đổi khi review lại một phần.
6. NetClaw: giao nhiều đợt nối tiếp trong chế độ chạy nền; dừng mềm child bị coi là treo có chặn được lần ghi file muộn không (mục 12.2).
7. NetClaw: backoff riêng cho GLM (`agent/retry_utils.py:20`, nhận diện theo `base_url`/`model` endpoint Z.AI Coding GLM-5.2) có áp dụng cho endpoint GLM 5.3 Flash đang dùng không (mục 13).
8. NetClaw: phân biệt được lỗi hết quota/billing (402, quota exceeded) với 429 tạm thời trong kết quả child không — để skill chọn đúng nhánh 6.2.
9. Hỏi vận hành NetMind/GLM: 1 key chung hay theo user; giới hạn đồng thời, RPM/TPM; quota theo user; có prompt caching không.

---

## 8. Kiểm chứng và tiêu chí đạt

1. `scripts/test_page_plan.py` + các `scripts/test_*.py` hiện có pass; GitNexus `detect_changes` chỉ chạm đúng phạm vi.
2. **Deck ~30 trang** (source thật hoặc BCT34 mở rộng), chế độ parallel trên NetMind desktop, `timing.log` từng đoạn. Đạt khi:
   - export 0 error, receipt hợp lệ;
   - Step 6 + review nhanh hơn rõ rệt so với tuần tự (mục tiêu ≥ 2×);
   - khung trang đồng nhất với trang mẫu, 0 lệch palette/font;
   - số lỗi 429/retry trong log không tăng bất thường.
3. Deck ngắn ở chế độ "tuần tự" → nhánh cũ vẫn đúng.
4. Project cũ không có `## execution` → chạy `sequential`.
5. Đo thời gian viết `design_spec` (Phase A) → quyết định đợt 2.

`max_subagents` giữ mặc định 6, không đo riêng; vận hành/user chỉnh trực tiếp trong `spec_lock` khi cần.

---

## 9. Quy trình làm việc

- Làm trên nhánh `feat/parallel-subagent`, không làm trực tiếp trên `main`.
- Thứ tự: mục 7 → 4.2 → 4.3 + 4.6 + 11.6 (`page_plan.py` + test) → 4.4 → 4.1 → 4.5 + 11.6 (resume/live-preview) → mục 8.
- Quy tắc luồng cần ghi vào protocol (mục 12.3, 6.2): main chỉ đi tiếp khi cả đợt kết thúc; lượt phụ chỉ cho child đã kết thúc; nhắc user không bấm save annotation trong lúc vẽ; hết quota → không lượt phụ.
- Không commit cho tới khi user xem kết quả kiểm chứng.

---

## 10. Điểm mới so với 1.0.6 (dự kiến release notes)

1. **Sinh slide song song mặc định** — Executor chia trang cho tối đa 6 sub-agent (`delegate_task`), mỗi sub-agent ≤ 6 trang; deck lớn tự chia nhiều đợt. User trả lời "tuần tự" ở Eight Confirmations để về cách cũ.
2. **Chọn chế độ sinh trong Eight Confirmations** — dòng 💡 mới, ghi vào `spec_lock.md` `## execution`; phiên resume đọc lại từ đĩa.
3. **Page brief tự động** — `scripts/page_plan.py briefs` sinh brief từng trang (content lock nguyên văn + spec_lock + template) và chia nhóm cân bằng theo trọng số trang, trong vài giây.
4. **Kiểm tra lỗi song song** — mỗi sub-agent tự chạy checker + `verify-charts` trên trang của mình; main chỉ còn cổng kiểm tra toàn deck.
5. **Semantic review song song** — review nội dung từng trang (bắt buộc để export) chia cho sub-agent mới; `page_plan.py merge-reviews` gộp thành receipt.
6. **Tự phục hồi** — trang thiếu/lỗi, rate limit → 1 lượt phụ song song (giảm số child khi bị 429); host không hỗ trợ sub-agent → tự chuyển tuần tự.
7. **Tương thích ngược** — project cũ không có `## execution` chạy tuần tự như 1.0.6; ZeroClaw và host khác không có `delegate_task` không bị ảnh hưởng.
8. **Chạy tiếp đúng chỗ dừng + sửa riêng từng trang** — `continue generation` chỉ vẽ trang thiếu/hỏng/lỗi thời, không đụng trang đã xong hoặc user đã sửa tay; lệnh "vẽ lại trang N" chỉ vẽ lại, check, review và export đúng trang đó (áp dụng cho cả parallel và sequential).

---

## 11. Chạy tiếp và sửa từng trang (vá lỗ hổng resume)

### 11.1 Vấn đề hiện tại (1.0.6)
- `workflows/resume-execute.md` Step 2 nhảy vào Step 6 và chạy lại **toàn bộ** "per-page generation" → vẽ lại mọi trang dù đã có SVG tốt.
  - Tốn token/thời gian (deck 30+ trang).
  - **Nguy hiểm**: ghi đè trang đã review, trang user đã sửa tay hoặc đã áp annotation; làm mất hiệu lực toàn bộ review receipt.
- Sửa nhỏ một trang đã có luồng (`live-preview` Step 2 / "precise chat edit"), nhưng **chưa có luồng "vẽ lại trang N"** hoặc "nội dung trang N đổi → vẽ lại".
- Export đọc mọi `svg_output/*.svg` → file thừa (trang đổi tên, bản nháp) lọt vào PPTX.

### 11.2 Giải pháp: trạng thái từng trang, suy ra từ đĩa
Đổi tên script thành **`scripts/page_plan.py`** (dùng cho cả parallel lẫn sequential, không chỉ song song). Thêm file **`<project>/page_state.json`** do script ghi:

```json
{ "P05": { "file": "05_tien_do_5g.svg", "lock_sha": "…", "svg_sha": "…", "recorded_at": "…" } }
```
- `lock_sha`: hash của content lock trang đó (`#### Slide NN` trong `design_spec.md`) + giá trị per-page trong `spec_lock` (rhythm/background/layout/chart).
- `svg_sha`: hash SVG tại thời điểm trang được xác nhận "xong" (qua checker từng file).
- Ghi bởi `page_plan.py record` — main chạy sau mỗi `verify` (đợt vẽ/lượt phụ) và sau cổng kiểm tra cuối; sequential mode chạy sau mỗi trang đạt checker.

**`page_plan.py status <project>`** phân loại từng trang:

| Trạng thái | Điều kiện | Resume làm gì |
|---|---|---|
| `done` | SVG tồn tại, `svg_sha` + `lock_sha` khớp | **Giữ nguyên** |
| `missing` | Chưa có SVG | Vẽ |
| `broken` | XML không parse được, hoặc checker từng file còn error (vd. file ghi dở khi bị ngắt) | Vẽ lại |
| `stale` | `lock_sha` hiện tại ≠ đã ghi (content lock/spec trang đó đã đổi) | Vẽ lại |
| `edited` | `svg_sha` ≠ đã ghi nhưng `lock_sha` không đổi (user sửa tay, annotation) | **Giữ nguyên**, chỉ check + review lại; không bao giờ tự vẽ đè |
| `unknown` | Có SVG nhưng chưa có trong `page_state.json` (project 1.0.6 / bị ngắt trước khi record) | Checker từng file: 0 error → coi như `done` và record; có error → `broken` |
| `extra` | SVG trong `svg_output/` không thuộc trang nào của design_spec | Báo user; **không export** cho tới khi user xoá/đổi tên |

### 11.3 Luồng resume mới (`continue generation projects/<name>`)
```
Step 1  sanity check (như cũ)
Step 2  page_plan.py status  → in bảng trạng thái cho user (1 dòng/nhóm)
        ├─ mọi trang done/edited → bỏ qua vẽ, nhảy tới cổng kiểm tra
        └─ có missing/broken/stale →
             parallel  : page_plan.py briefs --only missing,broken,stale → đợt vẽ chỉ các trang đó
             sequential: main vẽ đúng các trang đó, theo thứ tự
Step 3  cổng kiểm tra:
        - checker toàn deck (script, rẻ)
        - apply_brand_chrome CHỈ trên trang vừa vẽ/đổi (--file … --slide-number N)
        - semantic review CHỈ trang có svg_sha đổi; giữ finding còn hợp lệ của trang khác
        - record-review → --stage export → svg_to_pptx
```
Không còn đường nào vẽ lại cả deck trừ khi user yêu cầu rõ "vẽ lại toàn bộ".

### 11.4 Luồng "sửa / vẽ lại trang N"
| User nói | Luồng |
|---|---|
| Sửa nhỏ: "đổi tiêu đề trang 3 thành …", annotation trong editor | Giữ luồng hiện có (`live-preview` Step 2 / chat edit): sửa SVG → chrome `--file` → checker file → review lại trang đó → export. Trang thành `edited` |
| "Vẽ lại trang 7" (bố cục xấu, muốn làm lại) | `page_plan.py briefs --pages 7` → main vẽ (1–2 trang: main; ≥ 3 trang ở parallel: đợt vẽ nhỏ) → chrome `--file` → checker → review trang 7 → export |
| "Trang 7 sai số / thêm ý X" (đổi nội dung) | Strategist cập nhật content lock trang 7 trong `design_spec.md` (theo content-grounding, có nguồn) → trang tự thành `stale` → chạy như "vẽ lại trang 7" |
| "Vẽ lại toàn bộ" | Xác nhận với user (ghi đè trang đã sửa tay) → chạy luồng đầy đủ |

### 11.5 Bảo vệ chống ghi đè
- Đợt vẽ/lượt phụ chỉ nhận trang `missing`/`broken`/`stale`; brief chỉ sinh cho các trang đó → child không có đường ghi vào trang `done`/`edited`.
- `page_plan.py verify` sau mỗi đợt: trang `done`/`edited` phải giữ nguyên `svg_sha`; lệch → báo lỗi, không đi tiếp.
- Trang `edited` muốn vẽ lại → phải hỏi user (mất chỉnh sửa tay).

### 11.6 Thay đổi file bổ sung
- `scripts/page_plan.py` (thay tên cũ `parallel_plan.py`): thêm `status`, `record`, `briefs --only/--pages`, `verify` kiểm `done`/`edited`/`extra`.
- `workflows/resume-execute.md`: Step 2 viết lại theo 11.3.
- `workflows/live-preview.md`: sau sửa/annotation → `page_plan.py record`; thêm dòng trỏ luồng "vẽ lại trang N".
- `SKILL.md` Step 6: sequential cũng `record` sau mỗi trang đạt checker; Step 7 gate: `status` không còn `extra`/`broken`.
- `scripts/test_page_plan.py`: phân loại đủ 7 trạng thái; `--only` không sinh brief cho trang `done`/`edited`; `verify` bắt trang `done` bị đổi.

---

## 12. Ghi file song song và race condition

### 12.1 Không có bước gộp — mỗi file đúng một chủ
- Child ghi **thẳng vào `svg_output/`**. `plan.json` gán sẵn tên `NN_<slug>.svg` cho từng trang, mỗi trang thuộc đúng một child → hai child không bao giờ ghi cùng một file.
- Live preview thấy trang ngay khi child ghi xong (giữ trải nghiệm như sequential).

### 12.2 Tài nguyên dùng chung (đã kiểm code các script)

| Tài nguyên | Ai ghi | Rủi ro | Xử lý |
|---|---|---|---|
| `svg_output/NN_*.svg` | Mỗi file một child | Child ghi nhầm tên (vd. 05 thay 15) đè file child khác | Tên lấy từ brief; `page_plan.py verify`: tập file khớp `plan.json`, không file lạ, trang mẫu + trang `done`/`edited` giữ nguyên SHA256 |
| `spec_lock.md`, `design_spec.md`, `briefs/`, `images/`, `templates/` | Chỉ main, trước khi giao việc | Child sửa nhầm | Child **chỉ đọc** (ghi rõ trong `context`); lệch → `spec-lock-drift` + hash receipt báo |
| `svg_quality_checker.py <file>` | Child, đồng thời | Chỉ ghi `svg_quality_report.txt` khi có `--export` | Child không dùng `--export` (mặc định không ghi file — đã kiểm code) |
| `svg_position_calculator.py` | Child | Không ghi file | An toàn |
| `apply_brand_chrome.py`, `content_check.py` (ghi `content_review.json`), `check_fonts.py`, `page_state.json` | Chỉ main, khi không có child chạy | — | Đã nằm trong luồng: main chạy sau khi đợt kết thúc |
| `reviews/<group>.json` | Mỗi file một child review | — | `merge-reviews` gộp |
| `timing.log` (chỉ khi kiểm chứng) | Nhiều child append | Dòng xen nhau | Append 1 dòng ngắn — chấp nhận được |

### 12.3 Hai race thật sự và cách chặn
1. **Child bị coi là lỗi/treo nhưng vẫn đang chạy** → lượt phụ và child cũ cùng ghi một file.
   - Main chỉ đi tiếp khi NetClaw báo **cả đợt kết thúc** (mọi child ở `completed`/`failed`/`timeout`/`interrupted`).
   - Lượt phụ chỉ nhận trang của child đã kết thúc; không bao giờ sửa song song với child còn chạy.
   - NetClaw dừng child treo bằng **dừng mềm** (child tự kiểm tra giữa các bước) — chưa xác nhận chặn được lần ghi muộn (mục 7.6). Lưới an toàn: `verify` chạy lại ngay trước cổng kiểm tra toàn deck, và receipt review khoá SHA256 từng SVG → `content_check --stage export` từ chối nếu file đổi sau review. Tệ nhất là review lại một trang, không bao giờ export nội dung sai.
2. **Live preview editor ghi đè** — `/api/save-all` (`scripts/svg_editor/server.py:324`) parse và ghi lại SVG có annotation; nếu trùng lúc child đang ghi cùng file → mất một trong hai lần ghi.
   - Rủi ro đã có từ 1.0.6, song song làm cửa sổ rộng hơn.
   - Protocol nhắc user không bấm save annotation trước khi đợt vẽ xong (skill vốn chỉ áp annotation sau Step 7); `verify` báo file bị đổi ngoài lần ghi của child.

### 12.4 Phương án chặt hơn (chưa dùng)
Mỗi child ghi vào `svg_parts/<group>/`, `verify` xong script mới chuyển sang `svg_output/`. An toàn tuyệt đối với ghi nhầm tên, nhưng live preview không thấy trang tới khi gộp và thêm một bước. Chỉ bật nếu kiểm chứng phát hiện child ghi sai file.

---

## 13. Retry khi provider quá tải / rate limit / timeout

### 13.1 Ba lớp xử lý

**Lớp 1 — NetClaw retry từng request** (áp dụng cho main và mọi child: child là `AIAgent` dùng chung vòng xử lý)

| Cơ chế | Cấu hình | Hoạt động |
|---|---|---|
| Retry lỗi API | `api_max_retries` (mặc định 3) | Mất kết nối, timeout, 5xx, 429; backoff có jitter; tôn trọng `Retry-After` |
| Backoff riêng GLM quá tải | Có sẵn (`agent/retry_utils.py:20`) | Z.AI GLM trả 429 code 1305: retry nhanh 3 lần rồi giãn 30 → 60 → 90 → 120s. **Cần xác nhận áp dụng cho GLM 5.3 Flash** (mục 7.7) |
| Provider dự phòng | `fallback_providers` (child: `delegation.fallback_providers`, không đặt thì kế thừa main) | Hết retry → chuyển provider/model kế tiếp |
| Tự phục hồi khi provider sập tạm | `auto_recovery_cycles` (mặc định 5) | Sau khi hết retry + hết dự phòng mà vẫn lỗi tạm thời: chờ 15/30/60/60/60s rồi thử lại. Lỗi auth/billing/policy không vào nhánh này |

→ Child chỉ `failed` khi đã qua **vài phút retry** mà provider vẫn không trả lời.

**Lớp 2 — NetClaw giám sát child**
- Heartbeat phát hiện treo (450s không hoạt động / 1.200s kẹt một tool) → `timeout`. Model chậm nhưng đang trả lời không bị tính.
- `delegation.child_timeout_seconds`: mặc định tắt; không cần bật vì heartbeat đã đủ.

**Lớp 3 — Skill** (mục 6.2)
- Lượt phụ (giảm nửa số child khi rate limit) → main tự vẽ → blocker.
- Hết quota/billing: không retry, báo user, giữ trang đã xong, chạy tiếp bằng `continue generation` (mục 11).
- Host từ chối giao việc → `sequential`.
- `verify` bắt "xong giả".

### 13.2 Đề xuất cấu hình cho vận hành NetMind (không sửa skill)
- Giữ `api_max_retries: 3`, `auto_recovery_cycles: 5` mặc định.
- Cân nhắc `delegation.fallback_providers` sang một endpoint GLM khác **cùng model** (khác model dễ lệch style giữa các trang).
- Xác nhận backoff riêng GLM áp dụng cho GLM 5.3 Flash; nếu không, cân nhắc mở rộng nhận diện trong NetClaw (thay đổi phía NetClaw, ngoài phạm vi skill).

---

## 14. Trạng thái triển khai (nhánh `feat/parallel-subagent`, chưa commit)

### 14.1 Kết quả kiểm tra trước khi sửa (mục 7)
| # | Kết quả |
|---|---|
| 1 | `parse_lock` (update_spec.py) rủi ro HIGH (9 symbol, 3 luồng) nhưng **không sửa**; mọi nơi dùng chỉ `.get()` đúng section → `## execution` an toàn |
| 2 | Findings JSON: dict keyed theo page ID (`P01`), schema như `review_entries()`; receipt `hashes` có hash từng `svg_output/*.svg` + sources + `design_spec.md` + `spec_lock.md`. Tên SVG lấy từ trường `svg` của content-lock |
| 3 | `verify-charts`/`svg_position_calculator.py` theo từng trang được; calculator không ghi file |
| 4 | `apply_brand_chrome.py --file` có sẵn và **idempotent** (chạy lại theo file hay toàn project không đổi bytes) |
| 5 | Receipt có hash từng SVG → giữ finding trang không đổi được |
| 6 | NetClaw dừng child treo bằng **hard interrupt** (huỷ request đang chờ, bỏ vòng tool kế tiếp) → rủi ro ghi muộn thấp; lưới an toàn hash vẫn giữ |
| 7 | Backoff riêng GLM **không áp dụng**: endpoint thật là LiteLLM `stream-netmind.viettel.vn/aigw/ai/v1`, model `zai-org/GLM-5.3-Flash` (chỉ nhận Z.AI GLM-5.2) → chỉ có retry thường |
| 8 | NetClaw coi mọi 429 như nhau → skill phân loại theo thông báo: `TPM limit=0`/`insufficient_quota`/402 = cố định; `saturation`/`throttling` = tạm thời |
| 9 | Log desktop: rate limit là **TPM dùng chung theo model** (`Model TPM: 25.000.000`, `Model RPM: not configured`, `Model saturation: 95,7%`, priority-based). Sub-agent giảm context/request → giảm tổng token gửi lên, đỡ tải TPM chung |

### 14.2 Đã làm
- `scripts/page_plan.py` (mới): `briefs` (`--only`, `--pages`), `status`, `record`, `verify` (`--wave`), `reviews`, `merge-reviews`. Chia nhóm theo trọng số, liên tục, ưu tiên cắt tại `### Part` khi không làm tăng số nhóm; project legacy giữ tên `NN_*.svg` có sẵn; `plan.json` có `frozen` (hash trang ngoài plan) để `verify` bắt ghi đè.
- `scripts/test_page_plan.py` (mới): 10 test (giới hạn nhóm/đợt, phủ đủ trang, cân bằng, brief chung prefix, 7 trạng thái, resume `--only`, record từ chối stale/lỗi, verify frozen/extra, merge + carry-forward, legacy).
- `templates/page_brief_rules.md` (mới, 8 quy tắc có nguồn).
- `templates/spec_lock_reference.md`: `## execution`.
- `SKILL.md`: rule 3/6/7/9/10, dòng 💡 chế độ sinh ở Step 4, Parallel Generation Protocol + record + semantic review song song ở Step 6, checkpoint.
- `references/executor-base.md`, `strategist.md`, `content-grounding.md` §5; `workflows/resume-execute.md` (resume theo trạng thái + vẽ lại một trang), `live-preview.md`, `verify-charts.md`.
- Test: `test_page_plan` 10/10, `test_content_grounding` 13/13, `test_text_box_fit` 13/13, `test_font_gate`, `test_native_export`, `test_provider_common`, `test_server_startup` OK. GitNexus `detect_changes`: 8 file, 0 luồng code bị ảnh hưởng, risk low.

### 14.3 Còn lại
- Kiểm chứng mục 8 trên NetMind desktop (deck ~30 trang) — cần cài bản nhánh này vào `~/.netmind_desktop/skills/viettel-ppt-master` (đang là 1.0.6).
- Bump `_meta.json` → 1.0.7 khi release.
- Commit sau khi user xem kết quả kiểm chứng.

## 15. Validation run 1 (BCT34, 35 pages, 2026-11-10) and fixes

Result: 35/35 pages drawn, 0 checker errors, export passed, no 429/timeout. Total 67 min. Drawing (anchor + 2 waves) took 20.6 min wall-clock against 70 min of summed agent time, about 3.4×.

| Problem seen | Cause | Fix |
|---|---|---|
| Wave 2 with 1 agent for 4 pages (+251 s) | `briefs` partitioned frame pages separately: 5 + 2 = 7 groups > 6 | One contiguous partition, so a deck of ≤ 36 pages is 1 wave |
| P03 = `02_chapter.svg`, P35 = `04_ending.svg`; the checker mapped them to P02/P04, and the agent removed the background markers to work around it | The Strategist put the layout name into the lock's `svg` field | `Project` refuses any name without the `NN_` prefix; content-grounding §2 states the rule |
| 903 unbound texts, 12 pages missing `data-chart`; a binding script broke 5 tags; review + repair took about 20 min | The brief had no binding rule, and children had no tool to check bindings per page | Brief rules 1 and 3; new `page_plan.py check --pages`; `verify` reports `content_errors`; `record` refuses pages with content errors |
| `record` refused stale pages, so the agent hand-edited the `lock_sha` values in plan.json | No way to accept a deliberate lock change | `record --accept-lock`; content-grounding requires editorial IDs for every label so the lock rarely changes |
| One review agent for 35 pages (924 s) | The agent ignored `page_plan.py reviews` | SKILL.md: always use `page_plan.py`, one task per group |

## 16. Plan: writing content locks in parallel (Phase A)

Status: **proposal, awaiting approval**. Wave 1 (drawing) and fix #3 (lenient quote matching) are done.

### 16.1 Problem

The main agent writes 30 content locks (about 100 quotes) one after another, in its heaviest context (sources, references, the 8 confirmations, sections I–VIII). In run 1, the stretch from `confirm_received` to `anchor_start` took about 11.5 minutes; in run 2 it was still stuck at P15. Writing locks is per-page work with no cross-page dependency, so it can be parallelised the same way as drawing.

### 16.2 Flow

```
OLD (sequential)                          NEW (generation_mode: parallel)
Main: 8 confirmations                     Main: 8 confirmations
Main: design_spec I–VIII                  Main: design_spec I–VIII
Main: IX outline + 30 locks  (slow)       Main: IX outline per page (title, points,
Main: spec_lock                                 block-ids, chart template), spec_lock
Main: plan gate (repeat on failure)       Main: page_plan.py lock-briefs → locks/plan.json
Main: draw…                               ┌ child L1: P01–P06 → locks/P01.json …  ┐
                                          │ child L2: P07–P12                     │ 1 wave
                                          │ …  (≤ 6 children, each self-checks)   │ end turn
                                          └ child L5: P25–P30                     ┘
                                          Main: page_plan.py merge-locks → IX fences
                                          Main: content_check --stage plan (1 pass)
                                          Main: draw (wave 1 as before)
```

### 16.3 Ownership (no race conditions)

| Who | Writes | Reads |
|---|---|---|
| Main | design_spec.md (I–IX outline), spec_lock.md; merges locks into IX | everything |
| Child L* | only `locks/<PID>.json` for its own pages | lock brief, content-grounding §2–3, its source blocks (`source_index.py --show`), charts_index entries for its templates |

The children never touch design_spec.md; only the main agent merges.

### 16.4 Changes

1. **Strategist (strategist.md, SKILL.md Step 4)**: in parallel mode, IX holds only the outline per page: title, key points, the source block IDs to use, chart template (as in §VII / page_charts) and SVG name `NN_slug.svg`. Sequential mode keeps the old flow.
2. **`page_plan.py lock-briefs`**:
   - writes `locks/briefs/<PID>.md`: the page outline, verbatim source blocks, the `data_requirements` of the chosen chart template, the lock template and the rules (§2–3);
   - writes `locks/plan.json` with groups (reusing `partition`, cut at Part boundaries) and task contexts.
3. **`page_plan.py lock-check --pages`**: runs `check_page` + the source hash + the SVG name check on `locks/<PID>.json` before merge. Children run it themselves.
4. **`page_plan.py merge-locks`**:
   - inserts or replaces the ```content-lock``` fence under each `#### Slide NN`;
   - is idempotent;
   - refuses a lock whose page/svg/hash does not match the outline;
   - reports missing pages.
5. **Recovery**: same as drawing (quota → stop; rate limit → half the sub-agents; failing pages → main writes them itself).
6. **Resume**: `status` gains a `no-lock` state; resume runs `lock-briefs --only no-lock`.
7. **Tests**: grouping, merge idempotency, refusing bad locks, lock-check per page.

### 16.5 Expected effect

- Locks for 30 pages: about 8 minutes → about 2–3 minutes (one wave of 5–6 children, each 5–6 pages, short context).
- The main agent's context arrives at drawing without 30 locks of reasoning, so later steps are lighter too.
- Quality: the same mechanical checks (quotes, raw tokens, calculations, chart roles) per page, plus the full plan gate after merge. The final semantic review is unchanged.

### 16.6 Alternatives considered

- **B. One child writes the locks and then draws the same pages** (one dispatch instead of two). Faster still, but it skips the whole-deck plan gate before drawing, and lock errors flow straight into the SVGs. Revisit after A has been measured.
- **C. Keep sequential, rely on fixes #1–#3.** Fewer loops, but the 30 locks stay serial.

### 16.7 Open questions

1. Should the main agent skim the merged conclusions/titles (about 1 minute) before the plan gate, or rely on the final semantic review?
2. Should the anchor page's lock be written by the main agent before the wave, so the anchor can be drawn while the children write locks?

### 16.8 Implementation status (done, awaiting validation)

- Decisions: the main agent writes the anchor's lock and draws the anchor while the lock wave runs; there is no skim before the plan gate, which together with the final semantic review is enough.
- `page_plan.py lock-briefs | lock-check | merge-locks`. `briefs` keeps an anchor that was drawn earlier.
- SKILL.md Step 4 "Parallel Content Locks"; strategist.md §IX row; content-grounding §2.
- Test on a copy of BCT34 (35 locks removed, keeping a `Sources:` line):
  - `lock-briefs` grouped the pages as 6 groups in 1 wave, with briefs of about 2.7 KB each;
  - `lock-check` reported every broken quote and broken JSON in a single run;
  - merging was idempotent, and after the merge `content_check --stage plan` and `--stage svg` both PASS against the 35 real SVGs.
- 16/16 page_plan tests pass.
