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
- [x] 2026-11-01 Commit `cd4add6` + push origin/main (theo lệnh chủ nhân).

## Phiên 2026-11-01 chiều — data Pose (529 ảnh, zip Downloads)
- Input giải nén: `workspace/pose-input/Pose/{Couple,Friends,Group,Men,Women/*}`.
- Ảnh lỗi chủ nhân gửi = `Group/group_2.jpg` (3 người: váy vàng, váy hoa chữ V phía sau, váy xanh). Lỗi: chỉ tách 2 người, đầu+tay chữ V sang người váy xanh, váy xanh/vàng cụt.
- [x] Fix trong `pose_core.py`:
  - `detect_people` NMS 0.6 (trước 0.45 nuốt người chồng lấn).
  - `face_boxes()` (YuNet); `_people` dùng mặt: mặt chưa ai nhận → pose từ mặt; box người cắt ngang đầu → gộp khớp từ pose theo mặt (`merge`).
  - `person_labels(..., soft)`: SAM được nới vào vùng isnet mờ (`raw > SOFT_MIN`=25) + vượt mask isnet khi IoU SAM > `SAM_TRUST` 0.88 và phần thêm < `SAM_EXTRA` 0.6 diện tích.
  - Bỏ vùng isnet xa mọi người SAM > `BODY_KEEP` 6% H (xích đu couple_21).
  - Người to + YOLOX conf ≥ 0.6 vẫn giữ dù isnet bỏ sót (`OFFBODY_*`); khi đó tin mask SAM trong box (cô nằm couple_30).
  - Cache key `split10`, có hash `soft`.
  - Kết quả: `workspace/dbg-group2f.jpg` đạt.
- [x] Test mẫu 11 ảnh: `workspace/sheets-test/` đạt.
- [x] Batch toàn bộ (chạy lại sau fix), 529/529, 0 lỗi, TB 26 s/ảnh: `workspace/split-tools/batch_all.py` → PNG ở `output/Pose-2026-11-01/`, sheet soát ở `workspace/pose-all-sheets/` + `log.jsonl`. Chạy lại ảnh lẻ: thêm đối số chuỗi con đường dẫn.
- Soát 89 sheet: đa số đạt. Lỗi nhỏ còn lại: `Group/group_58` vệt nét rác bên trái; `Group/group_19` cậu áo xanh phía sau thiếu viền nửa trên; `Women/Picnic/picnic_15` 3 người nhỏ, nét mờ/thiếu; `Women/Funny/fun_18` không có người (vẽ viền vật thể trái tim).
- [ ] Chủ nhân xem output, OK thì đề xuất commit `pose_core.py` (dừng trước `git`).

## Phiên 2026-11-02 — sửa 4 ảnh lỗi nhỏ (HANDOFF-2026-11-02-fix-small)
- Nguyên nhân: (1) YOLOX bỏ sót người nhỏ / tranh vẽ / quay lưng; (2) ảnh 0 mặt → `count_blobs`, người dính nhau = 1 mảng → chọn `u2net_human_seg` cho ảnh nhóm (group_58, picnic_15, group_12 mèo, friend_15/23, group_11).
- [x] `_detect_zoomed`: YOLOX trên cả ảnh + crop bbox cut-out, gộp NMS. Box yếu (0.1–0.3) chỉ nhận khi ≥ 12 keypoint rõ và ≥ 80% nằm trên cut-out.
- [x] `_people(..., soft)`: "trên cut-out" tính cả vùng isnet mờ (`raw > SOFT_MIN`) — gáy/áo tối của người quay lưng (group_19).
- [x] `count_faceless` thay `count_blobs`: 0 mặt → max(mảng mask, người YOLOX zoom ≥ 0.4, cao ≥ 40% người cao nhất); không thấy người (thú, vật) → 0 → isnet.
  Đổi model 11/50 ảnh 0 mặt; behind_2/4/5, fun_17, fun_25 (1 người) cũng sang isnet — chấp nhận.
- [x] Cache key `split11`.
- Kết quả: group_19 tách được cô quay lưng (cô áo xanh lá ngả lưng vẫn gộp với bạn — không detector nào bắt); picnic_15 đủ 3 người; group_58 → isnet. fun_18 (người + bóng hình trái tim) giữ nguyên, coi là giới hạn.
- Render lại 24 ảnh (13 ảnh đổi + 11 ảnh test hồi quy): `workspace/sheets-fix/`, PNG ghi đè ở `output/Pose-2026-11-01/`. Chậm 6–15 phút/ảnh do PID 24236 (ComfyUI) giữ VRAM.
- Các ảnh còn lại trong batch 529 chưa render lại với code mới (khác biệt chỉ ở ảnh YOLOX bỏ sót người).
