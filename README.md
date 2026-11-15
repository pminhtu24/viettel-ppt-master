# Viettel Slide Generator Skill

Skill tạo deck PowerPoint, tối ưu cho slide Viettel: nhận tài liệu nguồn, lập bố cục nội dung, sinh SVG từng trang, kiểm tra chất lượng và xuất file PPTX.

## Khi nào nên dùng

- Tạo presentation/PPT/deck từ PDF, DOCX, PPTX, Excel, Markdown, URL hoặc nội dung bạn mô tả trực tiếp.
- Tạo deck theo nhận diện Viettel: logo góc phải, màu đỏ `#EE0033`, font FS Magistral và bố cục báo cáo doanh nghiệp.
- Cần slide có hình ảnh, chart, infographic và file PPTX có thể chỉnh sửa tiếp trong PowerPoint.
- Cần preview trên trình duyệt để click vào thành phần slide và để lại annotation sửa nhanh.

## Cách gọi nhanh

Trong netMind Desktop, Claude, Codex, nội dung yêu cầu nên có từ khóa `ppt`, `presentation`, `deck`, `slide`, hoặc `viettel slide`.

Ví dụ:

```text
Sử dụng skill viettel-ppt-master tạo cho tôi bản slide báo cáo từ file /bao_cao.pdf theo phong cách viettel, sử dụng nhiều chart minh họa.
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
3. Template: mọi deck mặc định dùng `templates/layouts/viettel_default/`; chỉ đổi khi bạn nói rõ không dùng nhận diện Viettel.
4. Strategist: đọc nguồn theo từng block có ID, đề xuất số slide và các điểm cần xác nhận (một lần dừng duy nhất). Sau khi bạn xác nhận, skill viết `plan.md` — mỗi slide ghi rõ các block nguồn nó dùng — rồi `spec_build.py build` sinh `design_spec.md` và `spec_lock.md` từ plan đó.
5. Sinh deck: SVG từng slide được agent viết tay, không sinh bằng script. Deck từ 6 slide trở lên và host có sub-agent (netMind: `delegate_task`) thì chạy song song: agent chính vẽ một trang mẫu, tối đa 6 sub-agent vẽ các nhóm trang còn lại; trả lời "tuần tự" ở bước xác nhận để vẽ lần lượt.
6. Live preview (Optional): mở editor local để xem slide và gửi annotation.
7. Kiểm tra và export: `page_plan.py check` và `fact_check.py` dò từng số liệu, nhãn kỳ, tên mục và trạng thái trên slide về block nguồn; quality check phải 0 lỗi rồi mới xuất native PPTX trực tiếp từ `svg_output/`.

## Điều cần xác nhận với người dùng

Skill sẽ dừng lại một lần ở bước Strategist để bạn xác nhận:

- Số slide (skill đề xuất dựa trên độ dài nguồn).
- Đối tượng xem và mục đích của deck.
- Phong cách.
- Bộ icon.
- Cách dùng hình ảnh.

Canvas 16:9, bảng màu và typography không nằm trong danh sách này: chúng được khóa theo nhận diện Viettel.

Với deck Viettel, các lựa chọn thương hiệu được khóa theo template Viettel, gồm màu `#EE0033`, `#12436D`, ba static face FS Magistral, logo top-right và footer/page-number treatment. Typography không phải lựa chọn của user: title/header/KPI/highlight dùng FS Magistral Bold (`FS Magistral-Bold.ttf`), nội dung thường dùng FS Magistral Book (`FS Magistral-Book.ttf`), subtitle phụ dùng FS Magistral Medium (`FS Magistral-Medium.ttf`). Trong SVG, `700` / `400` hoặc bỏ trống / `500` chỉ là selector; khi xuất PPTX, exporter ghi đúng Windows typeface và nhúng từng face thực sự được dùng để ngăn Arial/Calibri substitution.

## Chế độ split mode

Với deck dài hoặc source lớn, nên tách thành 2 chat:

1. Chat 1 làm Phase A: xử lý source, tạo project, xác nhận design và sinh `design_spec.md` / `spec_lock.md`.
2. Chat 2 tiếp tục Phase B bằng lệnh:

```text
continue generation projects/<project_name>
```

Chế độ này giúp giảm áp lực context trong sessions và cho model khi sinh nhiều slide và vẫn đọc lại được source trong project.

## Live preview và sửa slide

Khi cần xem/sửa trực quan:

```text
mở live preview cho projects/<project_name>
```

Editor chạy tại `http://localhost:5050`. Bạn có thể click vào element, ghi yêu cầu sửa, bấm **Submit annotations**, rồi quay lại chat và nói:

```text
apply my annotations
```

Skill sẽ áp dụng annotation vào SVG, kiểm tra lại và export PPTX mới.

## Output

Kết quả chính:

- `projects/<project_name>/svg_output/`: SVG từng slide.
- `projects/<project_name>/exports/<project_name>_<timestamp>.pptx`: file PowerPoint cuối.

Nếu deck có chart dữ liệu, workflow `verify-charts` sẽ được dùng để căn chỉnh tọa độ chart trước khi export.

## Yêu cầu môi trường

```bash
pip install -r requirements.txt
```

Skill tìm đủ FS Magistral Book, Medium và Bold trên host trước. Skill chỉ cài face còn thiếu; trên Windows nó luôn dùng Fonts của user hiện tại, không yêu cầu quyền system/admin. Không dùng shell `copy` hoặc tự expand `%LOCALAPPDATA%`. SVG luôn giữ `"FS Magistral"`; `--allow-font-fallback` chỉ cho phép preview host bị degraded. Exporter vẫn bắt buộc nhúng payload hợp lệ của từng face được dùng và hard-fail nếu payload thiếu hoặc sai metadata.
