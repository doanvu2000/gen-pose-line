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

## Phiên 2026-11-02 (2) — vệt đồ vật + chạy lại batch
- [x] `_drop_spurs` (cuối `person_labels`): cắt đuôi mảnh (chân ghế, cột) dài ≥ 8% chiều cao người, rộng < 3%, không chứa keypoint; xoá mảnh vụn < 1% sau khi cắt. picnic_15 hết vệt chân ghế; group_58/group_1 không đổi.
- Cache key `split13`.
- group_19 (cô ngả lưng, tranh vẽ): YOLOX/YuNet không bắt cả khi xoay 90/180 → giới hạn. fun_18 (người + bóng hình trái tim) → giới hạn.
- Batch 529 ảnh chạy lại qua GUI (`/api/batch/start`, skip_existing=false, model auto, preset 2) → `output/Pose-2026-11-01/`.
- [x] Batch chậm dần (~4 phút/ảnh) do VRAM tràn: ComfyUI + arena ORT nhân đôi không trả. Tắt ComfyUI; `_session_providers` đặt `arena_extend_strategy=kSameAsRequested`, `cudnn_conv_algo_search=HEURISTIC` cho mọi session CUDA → ~4–14 s/ảnh, VRAM ổn định ~10,9 GB.
- [x] Batch 529/529 xong, 0 lỗi (106 ảnh lượt đầu + 423 lượt sau). PNG cũ chưa chạy lại đã chuyển sang `output/_old-Pose-2026-11-01/` (có thể xoá).

## Phiên 2026-11-02 (3) — soát 529 ảnh, sửa lỗi nặng
- [x] Giữ bàn tay giơ cao: blob "far" cỡ bàn tay (≤ 0.2 người) trong tầm 0.2 người quanh khuỷu/cổ tay không bị coi là đồ vật; `_drop_spurs` neo ngón tay theo cổ tay/khuỷu (group_2 chữ V, couple_4).
- [x] `subject_mask`: model chọn ra mask < 1% → đổi u2net_human_seg ↔ isnet (group_26 tranh vẽ trống viền, group_37 chân chụp từ trên).
- [x] Ảnh 1 người: blob far ≥ 30% diện tích label giữ lại (box YOLOX cắt ngang váy xoè, fun_1 mất chân).
- [x] `_drop_crumbs`: mảnh rời < 2% mảnh lớn nhất, không chứa keypoint → xoá (group_60/61).
- Cache key `split17`. Soát 89 sheet (`workspace/review-sheets/`) bằng 5 agent; đa số báo là dính đồ vật sát người (bàn, ghế, bậu cửa, thảm picnic) — giới hạn của model tách nền, chưa xử lý. Còn: cafe_4 đĩa, book_28, poster hình người (friend_1, cafe_7), couple_1 cọc lan can.
- Batch 529 chạy lại qua GUI.
- Kết quả: 529/529, 0 lỗi, ~44 phút. Commit `4c34d38`.

## Phiên 2026-11-02 (4) — nét trong rõ người
- Thử siết `BODY_KEEP` 0.06 → 0.015 để bỏ đồ vật sát người (`workspace/props-compare.jpg`): chỉ đỡ vài ảnh (picnic_18 giỏ). Chủ nhân: đồ vật không quan trọng, ưu tiên nét đầu/tay/chân/thân → bỏ hướng này.
- [x] `person_parts`: thêm SAM theo khung xương cho 2 chân (hông-gối-cổ chân) và đầu (mũi/mắt/tai, âm bản vai/hông); tay giữ như cũ. Cache key `split18`.
- [x] Preset 2: nét trong `inner_width` 2 → 3, `inner_opacity` 0.6 → 0.9 (cả `workspace/batch-cfg.json`).
- So sánh: `workspace/parts-test1.jpg`, `parts-test2.jpg` (script `split-tools/parts.py`, so code HEAD vs mới).
- Lưu ý: chạy script thử song song app GPU dễ tràn VRAM 12 GB → chậm ~3 phút/ảnh; tắt app trước khi thử.
- Batch 529 chạy lại qua GUI với code mới.

## Phiên 2026-11-02 (5) — sếp báo group fail (21 ảnh `Downloads/Group_Fail.zip`) + data Photobooth
- Input: `workspace/group-fail-in/Group_Fail/` (trùng md5 với `pose-input/Pose/Group`, riêng `group_8.png` là ảnh output lỗi sếp chụp lại).
- Nguyên nhân chung: isnet bắt đủ người, nhưng YOLOX/YuNet chỉ thấy 2–3 người (tranh vẽ, xếp chồng, lộn ngược) → vùng mask cách người đã nhận > `BODY_KEEP` bị xoá như đồ vật → mất cả người (group_40, 35, 4, 44) hoặc tay chân vượt box SAM (group_31, 43).
- [x] `_recover_far` (chỉ khi ≥ 2 người): vùng xa mảnh (lõi sau opening < `FAR_CORE`) mới bỏ; vùng dày giữ lại (gán người gần nhất); vùng ≥ `FAR_PERSON` × diện tích người → YOLOX zoom vào crop (`_far_seeds`) + SAM thành người mới, phần còn dư cũng thành người.
- [x] `_rotated_pose`: mặt YuNet thấy nhưng pose thẳng đứng hỏng → thử pose trên ảnh xoay 180/90/270 (group_8 cô tóc vàng lộn ngược).
- Cache key `split22`. `workspace/split-tools/one.py` dùng `subject_mask`; `batch_all.py` nhận env `ROOT`/`OUT`.
- Kết quả 21 ảnh: `workspace/sheets-groupfail/`, PNG ghi đè `output/Pose-2026-11-01/Group/`. So sánh trước/sau: `workspace/compare-groupfail/` (+ `.zip`).
- [x] group_37 (chỉ chân, chụp từ trên): isnet + u2net_human_seg không thấy 2 cặp chân hai bên → `subject_mask` khi mask rỗng thử thêm `birefnet-portrait` (`FALLBACK_MODEL`), lấy mask phủ nhiều nhất < `FULL_MASK`. group_26 không đổi.
- Photobooth 109 ảnh (`1 mình` 40, `Bạn thân` 36, `Cặp đôi` 33): input `workspace/photobooth-in/Photobooth/`, output `output/Photobooth-2026-11-02/`, sheet `workspace/sheets-photobooth/`.
- [x] Batch Photobooth chậm dần tới ~250 s/ảnh: VRAM 11,7/12,2 GB do arena SAM-L giữ activations → `_sam_embed` chạy với RunOptions `memory.enable_memory_arena_shrinkage=gpu:0` (chỉ CUDA). VRAM ~4–6 GB, 5–15 s/ảnh. `batch_all.py` thêm env `SKIP=1` bỏ ảnh đã có PNG.
- Soát 109 ảnh Photobooth (`workspace/review-photobooth/g*.jpg`, `index.txt`): đủ người, tách tốt. Lỗi lặp: logo watermark "✦" góc dưới thành hình thoi trên áo; #84 ảnh có viền trắng in quanh → vẽ khung chữ nhật.
- [x] `_frame_pad` + `render_photo`: viền đồng màu kết thúc bằng bước nhảy màu (`PAD_*`) → render trên phần trong rồi dán lại. Khớp 10/638 ảnh (đều là viền thật).
- [x] `_merge_specks` trong `person_parts`: mảnh nét trong < `PART_MIN` 0,6% diện tích người gộp vào mảnh bao quanh (watermark, nút áo, con ngươi lẻ).
- Cache key `split24`. Chạy lại 109 Photobooth + 21 group fail. 529 ảnh Pose còn lại chưa render lại với code mới.
- [x] `PART_MIN` 0,3% → 0,6% (watermark #89 = 825 px, sát ngưỡng cũ). Cache `split24`. Chạy lại 109 Photobooth + 21 group fail: 130/130, 0 lỗi; hết hình thoi watermark, hết khung #84. Grid soát `workspace/review-photobooth/`, so sánh `workspace/compare-groupfail(.zip)`.
- [ ] Chủ nhân/sếp duyệt → đề xuất commit `pose_core.py` (dừng trước `git`). 529 ảnh Pose còn lại chưa render lại.
