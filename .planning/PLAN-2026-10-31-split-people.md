# PLAN — tách nét từng nhân vật (ảnh nhóm chồng nhau)

Vấn đề: ảnh nhóm, mask isnet gộp cả nhóm thành 1 khối → chỉ có viền ngoài, nét trong (DoG) yếu → không phân biệt được từng người.

## Pipeline đã prototype (scratchpad/proto4.py, kết quả `workspace/split-people-proto.jpg`)
1. YOLOX (opencv_zoo, 34 MB, `.cache/models/detect/`) → box người, score > 0.3, NMS 0.45.
2. RTMPose-m body7 (openmmlab, 48 MB, `.cache/models/pose/`) → 17 keypoint/box.
   - Bỏ box: < 5 keypoint tin cậy (> 0.3), keypoint không nằm trên mask isnet, cao < 30% box lớn nhất (người nền).
   - Gộp box trùng: median khoảng cách keypoint < 3% H.
3. SAM (rembg `sam`, encode 1 lần/ảnh): prompt = box + keypoint mình (dương) + keypoint người khác trong box (âm); refine 2 pass với `mask_input`.
   - ViT-L (1.2 GB) sạch hơn rõ so với ViT-B (360 MB).
4. Gán nhãn theo thứ tự trước/sau: chân thấp hơn = đứng trước, vẽ đè sau. Chỉ trong mask isnet; vùng trống lấp theo nhãn gần nhất (EDT), medianBlur 7.
5. Nét phân cách = biên giữa 2 nhãn khác nhau → skeleton → `trace_skeleton` → vẽ cùng style viền ngoài.

## Đã thử, loại
- SAM chỉ box + argmax logit: logit không so được giữa các người → gộp nhầm.
- Mask R-CNN ONNX (model zoo): mask 28×28 quá thô.

## Đã làm (2026-10-31)
- Chủ nhân chốt: nét phân cách mảnh theo style nét trong (`inner_width/inner_opacity/inner_dash/gap`; inner=none thì mượn kiểu nét chính).
- `pose_core`: `Style.split=True`, `detect_people`, `keypoints`, `_people`, `person_labels`, `_labels_cached` (`.cache/masks/*.lab.png`), `split_paths`; model tự tải; `set_device` xoá `_aux`.
- SAM tự tạo ORT session (SamSession của rembg bỏ qua providers → chạy CPU).
- UI: checkbox "Tách nét từng người (ảnh nhóm)" trong Nét phụ.
- Đo GPU: +0,6–0,8 s/ảnh nhóm khi model đã nạp; lần đầu nạp model ~20 s.

## Việc tiếp
- Chủ nhân test trên UI + batch ảnh nhóm thật; chưa đo batch CPU (ViT-B ước ~5–8 s/ảnh nhóm).
- Còn lỗi: người trái và cô gái trái (ảnh mẫu) vẫn lẫn một phần thân trên.

## Đợt 2 (2026-11-01) — nét chi tiết + bù đầu bị mất
- Chủ nhân: viền ngoài ổn nhưng bên trong chưa rõ dáng → muốn chi tiết hơn; đầu cậu bên phải bị mất.
- `person_parts`: crop từng người, SAM encode riêng, lưới điểm 3% chiều cao crop, lọc iou ≥ 0.75 + ổn định ≥ 0.8, NMS IoU 0.8, vẽ lớn trước nhỏ sau. Biên mảnh = nét trong (thay DoG khi `split` bật).
- `person_labels` giờ full-res, chạy cả ảnh 1 người; mask isnet được nới bằng mask SAM trong phạm vi 4% H quanh thân (isnet bỏ tóc đen trên nền tối).
- Mảnh rời của 1 người (đầu bị tay người trước cắt) giữ lại nếu chứa keypoint của chính người đó.
- Cache: `.cache/masks/*.split.npz` (lab + seg).
- Đã thử, loại: tách bộ phận theo nhóm keypoint (đầu/thân/tay/chân) → quá ít nét.
- Tốc độ GPU: ~18 s/ảnh nhóm 7 người cho nét chi tiết (decoder chạy từng điểm). Cần tối ưu (bỏ điểm đã phủ, giảm lưới) nếu chạy batch.
- Tay cùng màu áo bị gộp vào thân → `_limb_mask`: SAM trong crop với điểm dương khuỷu/cổ tay/giữa cẳng tay/gần vai, âm mũi+hông+vai kia (bỏ điểm âm sát tay), vẽ đè lên mảnh lưới. `person_labels` trả thêm keypoints; cache key `split3`.
