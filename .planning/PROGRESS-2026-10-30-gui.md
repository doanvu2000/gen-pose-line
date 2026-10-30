# PROGRESS 2026-10-30 — GUI theo design system

Yêu cầu (chuyển từ session gen-asset-studio-e9): restyle `static/index.html` theo `static/design-system/`
— state object + render(), panel/xuất log lỗi, motion ds, tiếng Việt, light theme cố định, fullscreen.
Cách làm: main agent chia việc → subagent code → subagent audit → main sửa. Commit: chờ chủ nhân xác nhận trực tiếp
(CLAUDE.md cấm tự commit; cho phép chỉ được chuyển lời qua peer session).

## Log
- [x] Đọc README/motion/icons ds, index.html (bản restyle bước đầu), app.py.
- [x] app.py: `Batch.state.stopped`, `Batch.error_items` (file/src/error/time), `Batch.cfg`, `GET /api/batch/log`
      (state + config + toàn bộ lỗi + device + time). `/api/batch/status` giữ nguyên shape (+ `stopped`).
- [x] Commit `0b7bf62` (design system + /api/batch/log). Chủ nhân đã cho commit theo bước + tự chạy app test.
- [x] Yêu cầu thêm: xem tiến trình gen + nút preview. app.py: `Batch.results` per file,
      `GET /api/batch/results?since=N`, `GET /api/batch/file?f=rel` (chặn path ngoài thư mục ra).
- [x] Subagent code index.html (state machine, log export, progress list + viewer, fullscreen, light).
- [x] Test trình duyệt (venv .venv tạo mới): preview, batch 8 file + 1 lỗi, viewer ←/→/Esc, xuất log, dừng, fullscreen, không lỗi console.
      Viewer nền mặc định → tối (nét trắng khó nhìn trên caro sáng).
- [x] Model rembg: chủ nhân muốn ngoài C/F (sắp đầy) → `U2NET_HOME` mặc định `<ROOT>/.cache/models` (pose_core.py),
      đã chuyển isnet-general-use 170MB từ C:\Users\dauph\.rembg sang. pip cache 4GB ở C — chưa xoá, hỏi chủ nhân.
- [x] Audit (code-reviewer): 0 high, 8 med. Backend đã sửa: try/except start, finally running=false, lock start,
      stopped chỉ khi dừng giữa chừng, results `started` + cap 1000 + since≥0, /api/open dùng subprocess + 404.
- [x] Frontend sửa theo audit (12 mục) — test lại Chrome OK, không lỗi console.
- [x] Commit `dea6f7d` (GUI restyle + audit fixes + model dir).
- [x] 18:43 Handoff mới: `.planning/HANDOFF-2026-10-30-1843.md`

## Phiên 2026-10-30 19:00 (sau HANDOFF-1843) — UI gọn + GPU + thiết bị
- [x] Push `1a0f9ff` lên origin/main (chủ nhân cho). pip cache 4GB ở C: chủ nhân bảo KHÔNG xoá.
- [x] Chạy thử zip workspace: CPU 100 ảnh 87.4s, 0 lỗi → `workspace/pose-line-out`, sheet `workspace/pose-line-sheet-{1,2}.jpg`.
- [x] Chủ nhân: ảnh có động vật → giữ isnet-general-use, KHÔNG đề xuất u2net_human_seg.
- [x] `.venv-gpu` (onnxruntime-gpu 1.31.1, CUDA ok trên RTX 5070, TMP/pip no-cache trên L). 100 ảnh GPU 40.4s; mask 124ms GPU vs 523ms CPU.
- [x] Plan `.planning/PLAN-2026-10-30-simple-ui.md`: thả thư mục → chạy, sidebar thẻ preset + Cơ bản + Nâng cao, viewer Gốc|Kết quả.
      Backend: /api/folder/pick|upload|info, /api/batch/src. Subagent làm FE, test Chrome OK (72 ảnh GPU 20.4s, viewer 2 cột).
- [x] Audit đợt UI gọn: 4 high. Backend đã sửa: upload `_safe_parts` + `_inside` (chặn `C:`/con/..), chia lô `session`, dọn `.cache/inputs` cũ,
      MAX_FORM_PARTS/MAX_CONTENT_LENGTH, chặn POST khác Origin, pick lock/returncode/focus, scan cap 50k, _fetch ghi tmp+replace, exif_transpose.
- [x] Chủ nhân: thêm kiểm tra thiết bị (Win/Mac). pose_core: `hardware_info`, `set_device`, `benchmark`, `active_provider`; app: /api/device GET/POST, /api/device/test.
      Model + thư viện nằm trong project (chủ nhân muốn để tiện gỡ) — đã đúng: `.cache/models`, `.venv*`.
- [~] Subagent FE: dialog Thiết bị + 10 mục audit FE. Test Mac: chủ nhân tự test sau.
