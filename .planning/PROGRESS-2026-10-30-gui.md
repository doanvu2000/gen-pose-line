# PROGRESS 2026-10-30 — GUI theo design system

Yêu cầu (chuyển từ session gen-asset-studio-e9): restyle `static/index.html` theo `static/design-system/`
— state object + render(), panel/xuất log lỗi, motion ds, tiếng Việt, light theme cố định, fullscreen.
Cách làm: main agent chia việc → subagent code → subagent audit → main sửa. Commit: chờ chủ nhân xác nhận trực tiếp
(CLAUDE.md cấm tự commit; cho phép chỉ được chuyển lời qua peer session).

## Log
- [x] Đọc README/motion/icons ds, index.html (bản restyle bước đầu), app.py.
- [x] app.py: `Batch.state.stopped`, `Batch.error_items` (file/src/error/time), `Batch.cfg`, `GET /api/batch/log`
      (state + config + toàn bộ lỗi + device + time). `/api/batch/status` giữ nguyên shape (+ `stopped`).
- [ ] Subagent code index.html.
- [ ] Subagent audit.
- [ ] Main sửa theo audit, test trình duyệt.
- [ ] Handoff.
