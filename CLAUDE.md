# CLAUDE.md — setup & chạy Pose Line Tool

Hướng dẫn cho Claude Code khi được nhờ "setup / chạy tool này trên máy". Tool là web Flask chạy local
(`app.py` + `pose_core.py`, UI ở `static/index.html`), cổng mặc định `7860`.

## Yêu cầu

- Python **3.10–3.13** (3.12 khuyên dùng). Không dùng Python của Microsoft Store nếu `py -3` có sẵn.
- ~2 GB trống cho venv + model. Model tách nền tải về `.cache/models` trong repo (đã set
  `U2NET_HOME` trong `pose_core.py`), **không** về ổ hệ thống. Nếu repo nằm ở ổ C mà máy còn ổ khác
  rộng hơn, hỏi chủ máy có muốn clone sang ổ đó không.
- Git LFS không cần. Mạng cần để `pip install` và tải model lần đầu (~170 MB, birefnet ~1 GB).
  Tách nét từng người (ảnh nhóm) tải thêm YOLOX 34 MB + RTMPose 48 MB + SAM (GPU: ViT-L ~1,2 GB,
  CPU: ViT-B ~360 MB) ở lần render ảnh nhóm đầu tiên.

## Windows

1. Kiểm tra Python: `py -3 --version` (hoặc `python --version`). Thiếu thì cài từ python.org
   (tick "Add python.exe to PATH") hoặc `winget install Python.Python.3.12`.
2. Có GPU NVIDIA? Kiểm tra `nvidia-smi`.
   - Có → dùng `run_win_gpu.bat` (venv `.venv-gpu`, `requirements-gpu.txt`, `onnxruntime-gpu`
     kèm CUDA/cuDNN qua pip — không cần cài CUDA Toolkit, chỉ cần driver mới).
   - Không → `run_win.bat` (venv `.venv`, `requirements.txt`).
3. Setup thủ công (khi muốn chạy từ terminal thay vì double-click), PowerShell:
   ```powershell
   py -3.12 -m venv .venv
   .venv\Scripts\python -m pip install -U pip
   .venv\Scripts\python -m pip install -r requirements.txt   # GPU: venv .venv-gpu + requirements-gpu.txt
   Copy-Item requirements.txt .venv\.req_stamp               # để .bat không cài lại
   .venv\Scripts\python app.py
   ```
4. Script `.bat` dùng `chcp 65001`; nếu console hiện ký tự lạ thì bỏ qua, không ảnh hưởng tool.

## macOS

1. Kiểm tra: `python3 --version` (cần ≥ 3.10; Python 3.9 của Xcode CLT không đủ). Thiếu thì
   `brew install python@3.12` (cần Homebrew) hoặc cài từ python.org.
2. Lần đầu: `chmod +x run_mac.command`, rồi double-click hoặc `./run_mac.command`.
   Nếu Gatekeeper chặn: `xattr -d com.apple.quarantine run_mac.command`.
3. Setup thủ công:
   ```bash
   python3.12 -m venv .venv
   .venv/bin/python -m pip install -U pip
   .venv/bin/python -m pip install -r requirements.txt
   cp requirements.txt .venv/.req_stamp
   .venv/bin/python app.py
   ```
4. Mac không có CUDA → chạy CPU. `POSE_TOOL_DEVICE=coreml` là thử nghiệm, chỉ bật khi chủ máy muốn.

## Kiểm tra sau setup

- Chạy nền không mở trình duyệt: `POSE_TOOL_NO_BROWSER=1` (PowerShell: `$env:POSE_TOOL_NO_BROWSER="1"`).
- Mở `http://127.0.0.1:7860` thấy UI là đạt. Panel thiết bị trong UI cho biết đang chạy CPU hay CUDA.
- Cổng bận → đặt `POSE_TOOL_PORT` khác.
- Lỗi thường gặp:
  - `onnxruntime` và `onnxruntime-gpu` cùng cài trong một venv → xung đột; GPU luôn dùng `.venv-gpu` riêng.
  - CUDA không nhận dù có GPU → cập nhật driver NVIDIA; tool tự fallback CPU khi `auto`.
  - Tải model lỗi giữa chừng → xoá file dở trong `.cache/models` rồi chạy lại.

## Quy ước khi sửa code

- Không commit `.venv*/`, `.cache/`, `workspace/`, `output/` (đã có trong `.gitignore`).
- Style dùng chung lưu ở `styles/*.json` — được commit.
- Model mặc định cho ảnh có động vật/nhóm là `isnet-general-use`; `u2net_human_seg` chỉ cho ảnh 1 người.
- Tiến độ / handoff ở `.planning/`.
