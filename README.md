# Pose Line Tool

Tool web chạy local tạo ảnh `poseUrl` (nét trắng, nền trong suốt) hàng loạt. Chạy trên macOS và Windows; trình duyệt tự mở `http://127.0.0.1:7860`.

## Chạy

| Máy | Lệnh |
|-----|------|
| macOS | double-click `run_mac.command` (lần đầu: `chmod +x run_mac.command`; cần Python 3.10+, script gợi ý `brew install python@3.12`) |
| Windows (CPU) | double-click `run_win.bat` |
| Windows + GPU NVIDIA (RTX) | double-click `run_win_gpu.bat` (venv riêng `.venv-gpu`, `onnxruntime-gpu` kèm CUDA/cuDNN qua pip, không cần cài CUDA Toolkit) |

Lần đầu tool tự tạo `.venv`, cài thư viện, rồi tải model tách nền (~170 MB, vào `~/.u2net`). Những lần sau chạy ngay.

## 2 nguồn đầu vào

| Nguồn | Đầu vào | Cách làm |
|-------|---------|----------|
| `photo` | ảnh chụp (previewUrl / thumbnail) | tách người bằng rembg → viền ngoài từ mask, nét trong lấy bằng XDoG (tuỳ chọn) |
| `lineart` | PNG nét trắng cũ (poseUrl / overlay) | skeleton → vector hoá → vẽ lại: nét dài = "nét chính", nét ngắn = "nét phụ" |

## Preset

1. Dash viền ngoài: chỉ silhouette nét đứt, gọn nhất.
2. Dash ngoài + nét trong mảnh: viền đứt, chi tiết bên trong nét liền mờ.
3. Chấm tròn + phủ mờ: viền chấm, thân người phủ trắng ~15%.
4. Liền + glow + phủ mờ: viền liền có bóng đậm, nổi trên mọi nền.
5. Restyle line-art: dash chính + liền phụ (dùng cho bộ nét cũ).
6. Restyle line-art: dash toàn phần.

Kích thước (độ dày, dài đoạn, khoảng hở…) tính theo ảnh cao 1000 px, tự co giãn theo ảnh thật. Style tự chỉnh thì bấm **Lưu**, file nằm ở `styles/<tên>.json`, commit vào repo để dùng chung.

## Chạy hàng loạt

- Đầu vào: thư mục ảnh (quét cả thư mục con, giữ cấu trúc) hoặc URL/đường dẫn `pose_lib.json`.
  - JSON + mode `photo`: lấy `previewUrl`, tên file = `id` pose.
  - JSON + mode `lineart`: lấy `poseUrl`, giữ tên file cũ (vd `ca-tinh-009.png`) để thay thẳng trên R2.
- Bỏ hậu tố: `_o` / `_t` cho bộ offline (`ca-tinh-001_o.webp` → `ca-tinh-001.png`).
- Output: PNG RGBA cùng kích thước ảnh vào, kèm `_style.json` ghi style đã dùng.
- Bỏ qua file đã có: chạy lại sau khi dừng giữa chừng.

## Biến môi trường

| Biến | Mặc định | Ý nghĩa |
|------|----------|---------|
| `POSE_TOOL_PORT` | `7860` | cổng web |
| `POSE_TOOL_DEVICE` | `auto` | `auto` (CUDA nếu có, không thì CPU) · `cuda` · `coreml` (Mac, thử nghiệm) · `cpu` |
| `POSE_TOOL_NO_BROWSER` | – | `1` = không tự mở trình duyệt |

## Tốc độ tham khảo (CPU laptop)

- restyle line-art: ~0.3 s/ảnh
- ảnh chụp: ~3–4 s/ảnh lần đầu (mask cache ở `.cache/masks`, chỉnh style lại thì nhanh)
- GPU RTX: tách nền nhanh hơn nhiều, nên dùng model `birefnet-portrait` (~1 GB, viền tóc đẹp hơn)
