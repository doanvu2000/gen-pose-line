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
- [x] Subagent FE: dialog Thiết bị + 10 mục audit FE. Test Chrome: GPU 148ms / CPU 549ms, đổi CPU<->CUDA OK. Test Mac: chủ nhân tự test sau.
- [x] Commit `a066393` (chưa push).
- [x] 19:25 Handoff mới: `.planning/HANDOFF-2026-10-30-1925.md`
- [x] Push `a066393`, `f2858cc` lên origin/main (chủ nhân cho).
- [x] Ô nhập mã hex cạnh màu nét (normHex #RGB/#RRGGBB, viền đỏ khi sai, presetDirty so màu không phân biệt hoa thường) — test Chrome OK, commit `fbd9d32` (chưa push, chờ chủ nhân).
- [x] 20:04 Handoff mới: `.planning/HANDOFF-2026-10-30-2004.md`

## Phiên 2026-10-31 (sau HANDOFF-2026-10-30-2004) — chủ nhân yêu cầu audit lại
- [x] Audit 2 agent (python-reviewer, typescript-reviewer), 14+14 finding; main lọc và sửa.
- [x] Backend: chặn Host lạ (DNS rebinding); `_fetch` cache theo sha1(URL) + giới hạn 200MB; id catalog JSON qua `_safe_parts`/`_inside`; chặn output trùng/nằm trong input; 409 đổi thiết bị/benchmark khi batch chạy; ghi PNG tmp→rename; mask cache đọc lỗi thì tính lại; `Style.from_dict` ép kiểu + clamp + whitelist; `_session` có lock, `active_provider` không nạp model (thêm `loaded`); hints `{level,text}`; `uploads` LRU 40; `/api/upload` bỏ qua file hỏng; `_run` bắt lỗi ngoài item; parse limit/max_height ở `_start`; skip_existing chỉ khi `_style.json` cũ trùng style; giữ input của batch cuối khi dọn; tên style dành riêng Windows.
- [x] Frontend: modal chồng (toast "Xem kết quả" đóng dialog Thiết bị, drop bị chặn khi có modal, inert chỉ gỡ khi hết modal); Huỷ upload có cờ, hiện cả lúc đọc thư mục; ô đường dẫn sai thì trả lại, Bắt đầu chờ tra cứu xong; `runDevTests` try/finally + benchmark `ok:false` hiện lỗi; viewer prev/next theo bộ lọc + preload; menu lỗi phím mũi tên/Home/End/Tab + aria-expanded; toast tách nút hành động + nút đóng, dừng đếm khi hover/focus; ô hex chỉ áp khi đủ 6 ký tự, Enter/Esc, không xoá khi alt-tab; tab Thử style lọc file theo đuôi ảnh.
- [x] Kiểm: `node --check` OK; curl: host lạ 403, output trong input 400, style "con" 400; Chrome: hex, dialog Thiết bị ("model chưa nạp"), batch 8 ảnh GPU, toast→viewer đóng dialog, inert gỡ đúng, console 0 lỗi.
- [ ] Còn để lại (không sửa): preview chạy full độ phân giải (chậm ảnh lớn), trùng tên output `a.jpg`/`a.png`, chưa có nút dọn cache, nút "Chạy lại ảnh lỗi".
- [x] Chủ nhân thử u2net_human_seg thấy mất người (ban-than/best-friend-101); so 3 model: isnet đủ 4 người, u2net hụt quần jean, human_seg mất bạn bên trái.
- [x] Đếm người + model Tự động + lọc 1 người (chủ nhân chọn "Cả hai"):
  - `pose_core.count_faces` (YuNet `.cache/models/face/face_detection_yunet_2023mar.onnx`, 227KB, tự tải nếu thiếu), `count_blobs` (mask isnet, vùng ≥20% vùng lớn nhất) khi 0 mặt, `count_people`, `resolve_model`; `MODELS` thêm `auto`.
  - `app.py`: preview trả `model`/`people`; batch `only_single` → skip có `reason`; results thêm `people`, `model`, `reason`.
  - FE: tên model có chú thích, checkbox `#bSingle`, dòng kết quả "lọc: N người", chip viewer "· human_seg · 1 người".
  - Đánh giá `workspace/pose-ref` 128 ảnh có nhãn: đúng 123/128 (chỉ đếm mặt: 110/128). Sai: 3 solo → ≥2 (người nền), 2 couple → 1 (sau lưng, nắm tay).
  - Chrome: thư mục couple + lọc → 5 bị lọc, 2 chạy (đúng 2 ca sai đã biết); console 0 lỗi.
- [x] Demo Chrome cho chủ nhân: Tự động (nhóm → isnet, solo → human_seg); batch `pose-ref` + lọc 1 người: 84 tạo / 88 lọc, 34s, ra `output/demo-1nguoi`. Thấy Tự động làm mất con hươu ở `cong-vien-049`. Chủ nhân chốt **giữ nguyên** (mặc định vẫn isnet, Tự động và lọc là tuỳ chọn).
- [x] `state["current"]` dùng `/` (trước lẫn `\`).
