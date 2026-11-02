# Handoff 2026-11-02 — sửa nốt ảnh lỗi nhỏ (dataset Pose-2026-11-01)

## Trạng thái
- `pose_core.py` + `.planning/PROGRESS-2026-11-01-split-people.md` đã sửa, **chưa commit**.
  Commit msg đề xuất: `Recover occluded and isnet-missed people in group split, drop fused props`.
- Batch 529/529 xong: PNG ở `output/Pose-2026-11-01/`, sheet soát ở `workspace/pose-all-sheets/`
  (`log.jsonl` có model + số mặt từng ảnh). Chi tiết fix xem PROGRESS.
- Chủ nhân yêu cầu: sửa nốt 4 ảnh lỗi nhỏ.

## Đang làm
Debug 4 ảnh bằng `workspace/split-tools/one.py <src> <out.jpg>` (dùng model của preset = isnet,
**không** phải `auto` như batch). Kết quả: `workspace/fix-<tên>.jpg`.

| Ảnh | Model batch (auto) | Phát hiện |
|-----|--------------------|-----------|
| `Group/group_58` | u2net_human_seg (faces=1) | Với isnet render **đạt** (2 người, không rác). Lỗi do `count_people` chỉ đếm 1 mặt (cô gái lộn ngược) → chọn SOLO_MODEL. |
| `Group/group_19` | isnet (faces=2) | Chưa xem `fix-group_19.jpg` (one.py ra 2 người). |
| `Women/Picnic/picnic_15` | u2net (faces=1) | Chưa xem; có thể cùng nguyên nhân đếm mặt thiếu. |
| `Women/Funny/fun_18` | u2net (faces=1) | Chưa xem; ảnh không có người, viền vật trái tim. |

## Hướng sửa
1. `resolve_model` / `count_people` (`pose_core.py:726-737`): ngoài đếm mặt, dùng thêm
   `detect_people` (YOLOX) — nếu YOLOX thấy ≥ 2 người to thì chọn GROUP_MODEL (isnet).
   Giữ isnet-general-use cho nhóm (memory).
2. Xem `fix-group_19.jpg`, `fix-picnic_15.jpg`, `fix-fun_18.jpg` rồi xử lý từng ảnh.
3. Rerun lẻ: `SHEETS=workspace/sheets-fix .venv-gpu/Scripts/python workspace/split-tools/batch_all.py group_58 group_19 picnic_15 fun_18`
   (env `POSE_TOOL_DEVICE=cuda PYTHONIOENCODING=utf-8`). Nếu đổi `resolve_model` thì cân nhắc
   chạy lại các ảnh có faces ≤ 1 trong `log.jsonl` để xem có đổi model không.
4. Cập nhật PROGRESS, báo chủ nhân, dừng trước `git`.

## Lưu ý
- VRAM lúc dừng: ~1,1/12 GB. Không chạy job GPU song song.
- Không tự commit; không thêm trailer.

## Kết quả (cập nhật cuối phiên)
- Đã xong, xem mục "Phiên 2026-11-02" trong PROGRESS. Sheet soát: `workspace/sheets-fix/` (24 ảnh đạt).
- Còn lại (không chặn): group_19 cô áo xanh lá ngả lưng gộp với bạn; picnic_15 vệt chân ghế; fun_18 viền theo hình trái tim. 505 ảnh còn lại của batch chưa render lại với code mới.
