# PROGRESS — tách nét từng nhân vật (ảnh nhóm)

Plan: `L:/AI/gen-pose-line/.planning/PLAN-2026-10-31-split-people.md`.

## Phiên 2026-10-31 → 2026-11-01 01:30 (sau HANDOFF-2026-10-30-2004)
Chủ nhân: sếp chê ảnh nhóm mất nét, cần "đi đủ nét từng nhân vật để phân biệt được từng người".

- [x] Prototype YOLOX + RTMPose + SAM (box + keypoint dương/âm), gán chồng lấn theo chân thấp hơn = đứng trước.
- [x] Loại: SAM chỉ box + argmax logit; Mask R-CNN ONNX (mask 28×28 thô, đã xoá file); tách bộ phận theo nhóm keypoint (quá ít nét).
- [x] Chủ nhân chốt: nét phân cách giữa người = mảnh theo style nét trong.
- [x] Chủ nhân: "viền ngoài ok nhưng bên trong chưa rõ dáng" → "chi tiết hơn nữa" → `person_parts` (crop từng người, lưới điểm SAM).
- [x] Fix mất đầu bạn ngoài cùng phải: nới mask isnet bằng mask SAM ≤ 4% H quanh thân + giữ mảnh rời có keypoint.
- [x] Fix tay cùng màu áo bị gộp: `_limb_mask` theo vai/khuỷu/cổ tay. Kết quả: `L:/AI/gen-pose-line/workspace/split-people-v3.jpg` (chủ nhân chưa phản hồi bản này).
- [x] Fix: SamSession của rembg bỏ qua providers → tự tạo ORT session (trước đó SAM chạy CPU dù có CUDA).
- [~] Test 50 ảnh (`workspace/split-tools/batch50.py`) — **dừng theo lệnh chủ nhân** sau ~2 ảnh/6 phút: VRAM đầy 11,9/12,2 GB (nghi ComfyUI PID 24236 giữ), máy đơ. Chưa có tỉ lệ %.
- [ ] Tối ưu `person_parts` trước khi chạy lại test (bỏ điểm lưới đã nằm trong mảnh đã nhận).
- [x] 01:30 Handoff mới: `.planning/HANDOFF-2026-11-01-0130.md`.
