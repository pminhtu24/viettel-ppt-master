# Viettel Slide Generator Skill

Skill tạo deck PowerPoint, tối ưu cho slide Viettel: nhận tài liệu nguồn, lập bố cục nội dung, sinh SVG từng trang, kiểm tra chất lượng và xuất file PPTX.

## Khi nào nên dùng

- Tạo presentation/PPT/deck từ PDF, DOCX, PPTX, Excel, Markdown, URL hoặc nội dung bạn mô tả trực tiếp.
- Tạo deck theo nhận diện Viettel: logo góc phải, màu đỏ `#EE0033`, font stack Viettel và bố cục báo cáo doanh nghiệp.
- Cần slide có hình ảnh, chart, infographic, notes thuyết trình và file PPTX có thể chỉnh sửa tiếp trong PowerPoint.
- Cần preview trên trình duyệt để click vào thành phần slide và để lại annotation sửa nhanh.

## Cách gọi nhanh

Trong NetClaw, Claude, Codex, nội dung yêu cầu nên có từ khóa `ppt`, `presentation`, `deck`, `slide`, hoặc `viettel slide`.

Ví dụ:

```text
Sử dụng skill viettel-ppt-master tạo cho tôi bản slide báo cáo từ file /bao_cao.pdf theo phong cách viettel.
```

```text
Tạo PPT Viettel về chiến lược AI trong viễn thông, 10-12 slide, có nhiều chart minh họa và live-preview sau khi tạo xong.
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
4. Strategist: đề xuất 8 điểm cần xác nhận như số slide, audience, style, màu sắc, typography, icon và image approach.
5. Sinh deck: sau khi bạn xác nhận, skill sinh SVG từng slide theo thứ tự, không batch template hàng loạt.
6. Live preview: mở editor local để xem slide và gửi annotation.
7. Kiểm tra và export: chạy quality check, tạo speaker notes, finalize SVG và xuất PPTX.

## Điều cần xác nhận với người dùng

Skill sẽ dừng lại một lần ở bước Strategist để bạn xác nhận:

- Định dạng canvas, mặc định `ppt169`.
- Khoảng số slide.
- Đối tượng xem deck.
- Mục tiêu phong cách.
- Bảng màu.
- Cách dùng icon.
- Typography.
- Cách dùng hình ảnh.

Với deck Viettel, các lựa chọn thương hiệu sẽ được khóa theo template Viettel, gồm màu `#EE0033`, `#12436D`, font stack `"FS PF BeauSans Pro", "FS Magistral", Sarabun`, logo top-right và footer/page-number treatment.

## Chế độ split mode

Với deck dài hoặc source lớn, nên tách thành 2 chat:

1. Chat 1 làm Phase A: xử lý source, tạo project, xác nhận design và sinh `design_spec.md` / `spec_lock.md`.
2. Chat 2 tiếp tục Phase B bằng lệnh:

```text
continue generation projects/<project_name>
```

Chế độ này giúp giảm áp lực context khi sinh nhiều slide và vẫn đọc lại được source trong project.

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
pip install -r ppt-master/requirements.txt
```

Nếu font Viettel chưa cài trên host, skill vẫn tiếp tục sinh deck nhưng sẽ báo `brand fidelity degraded`; font bundle nằm trong `templates/layouts/viettel_default/fonts/`, có thể yêu cầu Agent cài các fonts vào máy.
