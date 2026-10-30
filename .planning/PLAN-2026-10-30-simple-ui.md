# PLAN 2026-10-30 — UI gọn: thả thư mục → chạy, sidebar ít config, viewer so sánh 2 bên

Chủ nhân: "Chạy hàng loạt hơi khó dùng, bên trái nhiều config loạn. Muốn drop folder input rồi ấn chạy.
Preview output cần 2 bên so với ảnh gốc."

## Backend (main làm, xong)
- `POST /api/folder/pick` → hộp chọn thư mục native (tkinter, process con) → `{input, name, count, sample[], output}` | `{cancelled}`.
- `POST /api/folder/upload` (multipart `files` + `paths` relpath song song) → lưu `.cache/inputs/<stamp>/…`,
  trả `{input, name, count, sample, output: <ROOT>/output/<name>-<stamp>, uploaded: true}`.
- `POST /api/folder/info {path}` → như pick (cho ô nhập đường dẫn ở Nâng cao).
- `GET /api/batch/src?i=N` → ảnh gốc của result i (URL thì tải về cache). results có thêm `src`.
- Output mặc định: thư mục chọn → `<cha>/<tên>-line`; thư mục thả (upload) → `output/<tên>-<stamp>` (gitignore).

## Frontend (subagent)
1. Tab Chạy hàng loạt: `.empty-drop` lớn "Thả thư mục ảnh vào đây" + nút "Chọn thư mục…"; sau khi có input → card tóm tắt
   (tên, số ảnh, vài thumb, Lưu vào: path + nút Đổi/Mở) + nút Bắt đầu lớn; "Nâng cao" `<details>` đóng: đường dẫn/URL JSON,
   hậu tố, lọc, giới hạn, chiều cao, bỏ qua file đã có. Chạy xong: Tiến trình + list + viewer như cũ.
2. Sidebar: thẻ preset (list chọn 1) + Cơ bản (Loại đầu vào seg, Kiểu nét chính, Độ dày, Màu, Nét phụ bật/tắt) + `<details>` "Tùy chỉnh nâng cao".
3. Viewer: 2 cột Gốc | Kết quả; kết quả nền: Trên ảnh (PNG đè lên ảnh gốc bằng CSS) / Tối / Caro; mặc định Trên ảnh.

## Kiểm
Audit subagent → test Chrome (thả thư mục thật bằng DataTransfer giả lập khó → test upload qua fetch + pick bằng tay chủ nhân) → commit.
