# Viettel Slide Generator Skill

Skill tạo deck PowerPoint, tối ưu cho slide Viettel: nhận tài liệu nguồn, lập bố cục nội dung, sinh SVG từng trang, kiểm tra chất lượng và xuất file PPTX.

## Khi nào nên dùng

- Tạo presentation/PPT/deck từ PDF, DOCX, PPTX, Excel, Markdown, URL hoặc nội dung bạn mô tả trực tiếp.
- Tạo deck theo nhận diện Viettel: logo góc phải, màu đỏ `#EE0033`, font FS Magistral và bố cục báo cáo doanh nghiệp.
- Cần slide có hình ảnh, chart, infographic, notes thuyết trình và file PPTX có thể chỉnh sửa tiếp trong PowerPoint.
- Cần preview trên trình duyệt để click vào thành phần slide và để lại annotation sửa nhanh.

## Cách gọi nhanh

Trong NetClaw, Claude, Codex,.. nội dung yêu cầu nên có từ khóa `ppt`, `presentation`, `deck`, `slide`, hoặc `viettel slide`.

Ví dụ:

```text
Sử dụng skill sinh slide của viettel , làm cho tôi bản slide báo cáo từ file /bao_cao.pdf, sử dụng nhiều chart minh họa.
```

```text
Tạo PPT Viettel về chiến lược AI trong viễn thông, 12-15 slide, tạo animation giữa các slide và live-preview sau khi tạo xong.
```

## Input hỗ trợ

| Input           | Cách skill xử lý                            |
| --------------- | ------------------------------------------- |
| PDF             | Chuyển sang Markdown, trích nội dung và ảnh |
| DOCX / Office   | Chuyển sang Markdown, giữ tài sản hình ảnh  |
| XLSX / XLSM     | Đọc sheet thành nội dung bảng               |
| PPTX            | Trích nội dung deck cũ để tái sử dụng       |
| Markdown / text | Đọc trực tiếp                               |
| URL             | Lấy nội dung web làm nguồn                  |
| Chỉ có chủ đề   | Có thể research trước khi tạo deck          |

## Quy trình làm việc

1. Chuẩn hóa source: tài liệu nguồn được đưa về Markdown và đưa vào project.
2. Khởi tạo project: tạo thư mục `projects/<project_name>`.
3. Chọn template: nếu có từ khóa Viettel, skill tự động dùng `templates/layouts/viettel_default/`.
4. Strategist: đề xuất 9 điểm cần xác nhận như số slide, audience, style, màu sắc, typography, icon, image approach và generation mode.
5. Sinh deck: sau khi bạn xác nhận, mặc định skill chạy `serial` cho deck từ 15 slide trở xuống. Với deck trên 15 slide, hoặc khi bạn yêu cầu parallel/sub-agent, skill dùng `chapter_parallel` để tạo work packages; planner thường dùng ranh giới chapter/section để gom slide vào package, nhưng runtime spawn theo `run_manifest.subagent_groups`, không theo object `chapter`.
6. Live preview (Optional): mở editor local để xem slide và gửi annotation.
7. Kiểm tra và export: chạy quality check, tạo speaker notes, finalize SVG và xuất PPTX.

## Điều cần xác nhận với người dùng

Skill sẽ dừng lại một lần ở bước Strategist để bạn xác nhận:

- Định dạng canvas, mặc định `ppt169`.
- Khoảng số slide.
- Đối tượng xem deck.
- Mục tiêu phong cách.
- Bảng màu.
- Cách dùng icon.
- Typography cố định FS Magistral và quy tắc Bold/Regular.
- Cách dùng hình ảnh.
- Chế độ sinh slide: mặc định `serial` với deck từ 15 slide trở xuống; tự recommend `chapter_parallel` khi số slide đã chốt từ 16 trở lên hoặc khi bạn yêu cầu parallel/sub-agent. Ngưỡng này là so sánh cứng, không có buffer kiểu `15+5`.

Với deck Viettel, các lựa chọn thương hiệu được khóa theo template Viettel, gồm màu `#EE0033`, `#12436D`, font family `"FS Magistral"`, logo top-right và footer/page-number treatment. Typography: title/header/KPI/highlight dùng FS Magistral Bold (`700`), nội dung thường dùng Book/Regular (`400`), subtitle phụ dùng Medium (`500`).

## Chế độ split mode

Với deck dài hoặc source lớn, nên tách thành 2 chat:

1. Chat 1 làm Phase A: xử lý source, tạo project, xác nhận design và sinh `design_spec.md` / `spec_lock.md`.
2. Chat 2 tiếp tục Phase B bằng lệnh:

```text
continue generation projects/<project_name>
```

Chế độ này giúp giảm áp lực context trong sessions và cho model khi sinh nhiều slide và vẫn đọc lại được source trong project.

## Chế độ sinh slide mặc định

Executor mặc định chạy:

```text
generation_mode=serial
parallel_runtime=none
concurrency=1
```

Nếu số slide đã chốt từ 16 trở lên, hoặc bạn yêu cầu parallel/sub-agent, Executor dùng:

```text
generation_mode=chapter_parallel
parallel_runtime=auto
```

Flow parallel:

1. Tạo work packages bằng `python3 scripts/parallel_generation.py plan <project_path>`.
2. Chuẩn bị prompt và staging bằng `python3 scripts/parallel_generation.py prepare-subagents <project_path>`.
3. Nếu ZeroClaw delegate hỗ trợ `background=True`, `session_target="isolated"` và `check_result`, chạy từng `delegate_request` trong `parallel_generation/runs/<run_id>/run_manifest.json`. Mỗi sub-agent nhận đúng một work package từ `run_manifest.subagent_groups` và ghi SVG vào staging riêng: `parallel_generation/runs/<run_id>/work/<group_id>/svg_output/`. Không viết prompt delegate trực tiếp. Mặc định concurrency bằng số package sub-agent; truyền `--concurrency N` chỉ khi muốn chia batch nhỏ hơn.
4. Main agent merge staging về `svg_output/`, chạy validate, rồi mới export PPTX bằng pipeline cũ.

ZeroClaw delegate sub-agent được trigger theo pattern:

```python
task = delegate(
    action="delegate",
    background=True,
    session_target="isolated",
    agentic=True,
    max_iterations=100,
    prompt="Read and execute the package prompt at <prompt_file>. Do not work outside that scope.",
)

delegate(action="check_result", task_id=task["task_id"])
```

Sau khi sub-agents chạy xong, main agent bắt buộc chạy:

```bash
python3 scripts/parallel_generation.py merge <project_path> --run-id <run_id>
python3 scripts/parallel_generation.py validate <project_path>
```

Nếu runtime không hỗ trợ sub-agent trong `chapter_parallel`, skill phải in `Parallel Runtime Decision` kèm lý do fallback, giữ `generation_mode=chapter_parallel`, rồi chạy các work package bằng main agent với `parallel_runtime=main_agent_packages`. Với `serial`, skill bỏ qua parallel preflight và sinh slide tuần tự. Dù chạy bằng sub-agent hay main agent, SVG vẫn được viết theo từng slide/package, không sinh bằng batch template/codegen hàng loạt.

## Live preview và sửa slide

Khi cần xem/sửa trực quan:

```text
mở live preview cho projects/<project_name>
```

Editor chạy tại `http://localhost:5050`. Bạn có thể click vào element, ghi yêu cầu sửa, bấm **Submit annotations**, rồi quay lại chat và nói:

```text
apply my annotations
```

Skill sẽ áp dụng annotation vào SVG, finalize lại và export PPTX mới.

## Output

Kết quả chính:

- `projects/<project_name>/svg_output/`: SVG từng slide.
- `projects/<project_name>/notes/total.md`: notes tổng.
- `projects/<project_name>/exports/<project_name>_<timestamp>.pptx`: file PowerPoint cuối.

Nếu deck có chart dữ liệu, workflow `verify-charts` sẽ được dùng để căn chỉnh tọa độ chart trước khi export.

## Yêu cầu môi trường

```bash
pip install -r requirements.txt
```

Nếu font Viettel chưa cài trên host, skill vẫn tiếp tục sinh deck nhưng sẽ báo `brand fidelity degraded`; font bundle nằm trong `templates/layouts/viettel_default/fonts/`, có thể yêu cầu Agent cài các fonts vào máy.
