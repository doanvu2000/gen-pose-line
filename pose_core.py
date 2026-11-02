import hashlib
import io
import os
import re
import threading
from dataclasses import dataclass, asdict, field

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter1d
from skimage.morphology import skeletonize

ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(ROOT, ".cache", "masks")
# rembg defaults to ~/.rembg (or ~/.u2net) on the system drive; keep the large models next to the tool instead.
os.environ.setdefault("U2NET_HOME", os.path.join(ROOT, ".cache", "models"))
MODEL_DIR = os.environ["U2NET_HOME"]
MODELS = ["auto", "isnet-general-use", "u2net_human_seg", "u2net", "birefnet-portrait"]
SOLO_MODEL, GROUP_MODEL = "u2net_human_seg", "isnet-general-use"
FACE_MODEL = os.path.join(MODEL_DIR, "face", "face_detection_yunet_2023mar.onnx")
FACE_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
DET_MODEL = os.path.join(MODEL_DIR, "detect", "object_detection_yolox_2022nov.onnx")
DET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/object_detection_yolox/object_detection_yolox_2022nov.onnx"
POSE_MODEL = os.path.join(MODEL_DIR, "pose", "rtmpose-m-body7-256x192.onnx")
POSE_URL = "https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/onnx_sdk/rtmpose-m_simcc-body7_pt-body7_420e-256x192-e48f03d0_20230504.zip"
STROKES = ["none", "solid", "dash", "dots"]
SOURCES = ["photo", "lineart"]

_sessions = {}
_aux = {}
_session_lock = threading.RLock()
_face = None
_face_lock = threading.Lock()


@dataclass
class Style:
    source: str = "photo"
    outline: str = "dash"
    width: float = 4.0
    dash: float = 16.0
    gap: float = 10.0
    inner: str = "solid"
    inner_width: float = 2.0
    inner_opacity: float = 0.6
    inner_dash: float = 9.0
    inner_gap: float = 7.0
    major_len: float = 220.0
    min_len: float = 25.0
    detail: float = 0.5
    color: str = "#FFFFFF"
    opacity: float = 1.0
    holes: bool = True
    split: bool = True
    smooth: float = 2.5
    edge_margin: float = 4.0
    fill: bool = False
    fill_opacity: float = 0.15
    shadow: bool = True
    shadow_opacity: float = 0.45
    shadow_blur: float = 3.0
    model: str = "isnet-general-use"

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        st = cls()
        for k, v in (d if isinstance(d, dict) else {}).items():
            if k not in cls.__dataclass_fields__:
                continue
            cur = getattr(st, k)
            try:
                if isinstance(cur, bool):
                    v = bool(v)
                elif isinstance(cur, float):
                    lo, hi = _LIMITS.get(k, (0.0, 1.0))
                    v = min(hi, max(lo, float(v)))
                elif k in _CHOICES:
                    if v not in _CHOICES[k]:
                        continue
                elif k == "color":
                    if not isinstance(v, str) or not _HEX.match(v):
                        continue
                else:
                    continue
            except (TypeError, ValueError):
                continue
            setattr(st, k, v)
        return st


# Upper bounds are ~2x the UI sliders; tiny dash/gap or huge widths make rendering loop for minutes inside work_lock.
_LIMITS = {
    "width": (0.5, 30), "dash": (1, 200), "gap": (1, 200), "inner_width": (0.5, 30), "inner_opacity": (0, 1),
    "inner_dash": (1, 200), "inner_gap": (1, 200), "major_len": (0, 3000), "min_len": (0, 1000), "detail": (0, 1),
    "opacity": (0, 1), "smooth": (0, 20), "edge_margin": (0, 100), "fill_opacity": (0, 1), "shadow_opacity": (0, 1),
    "shadow_blur": (0, 30),
}
_CHOICES = {"source": SOURCES, "outline": STROKES, "inner": STROKES, "model": MODELS}
_HEX = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

PRESETS = {
    "1. Dash viền ngoài": Style(source="photo", outline="dash", inner="none"),
    "2. Dash ngoài + nét trong mảnh": Style(source="photo", outline="dash", inner="solid"),
    "3. Chấm tròn + phủ mờ": Style(source="photo", outline="dots", width=5.0, gap=9.0, inner="none", fill=True),
    "4. Liền + glow + phủ mờ": Style(source="photo", outline="solid", width=3.5, inner="solid", inner_opacity=0.45, fill=True, fill_opacity=0.12, shadow_opacity=0.6, shadow_blur=5.0),
    "5. Restyle line-art: dash chính + liền phụ": Style(source="lineart", outline="dash", width=3.5, dash=14.0, gap=9.0, inner="solid", inner_width=2.0, inner_opacity=0.7),
    "6. Restyle line-art: dash toàn phần": Style(source="lineart", outline="dash", width=3.0, dash=12.0, gap=8.0, inner="dash", inner_width=2.4, inner_opacity=0.85),
}


def _session(model):
    with _session_lock:
        if model not in _sessions:
            from rembg import new_session
            _sessions[model] = new_session(model, providers=_providers())
        return _sessions[model]


DEVICES = ["auto", "cuda", "coreml", "cpu"]
_PROVIDER = {"cuda": "CUDAExecutionProvider", "coreml": "CoreMLExecutionProvider", "cpu": "CPUExecutionProvider"}


def _providers(want=None):
    import onnxruntime as ort
    av = ort.get_available_providers()
    want = (want or os.environ.get("POSE_TOOL_DEVICE", "auto")).lower()
    order = []
    if want in ("auto", "cuda") and "CUDAExecutionProvider" in av:
        if hasattr(ort, "preload_dlls"):
            try:
                ort.preload_dlls()
            except Exception:
                pass
        order.append("CUDAExecutionProvider")
    if want == "coreml" and "CoreMLExecutionProvider" in av:
        order.append("CoreMLExecutionProvider")
    order.append("CPUExecutionProvider")
    return order


def set_device(want):
    want = (want or "auto").lower()
    if want not in DEVICES:
        raise ValueError(f"Thiết bị không hợp lệ: {want}")
    with _session_lock:
        if want == os.environ.get("POSE_TOOL_DEVICE", "auto").lower() and _sessions:
            return
        os.environ["POSE_TOOL_DEVICE"] = want
        _sessions.clear()
        _aux.clear()


def active_provider(model="isnet-general-use"):
    # ORT silently falls back to CPU when CUDA/CoreML fail to initialise, so ask the live session; never load one just to answer.
    with _session_lock:
        sess = _sessions.get(model) or next(iter(_sessions.values()), None)
    try:
        return sess.inner_session.get_providers()[0] if sess else None
    except Exception:
        return None


def device_info():
    import onnxruntime as ort
    return ", ".join(p.replace("ExecutionProvider", "") for p in _providers()) + f" (ORT {ort.__version__})"


def _run(cmd):
    import subprocess
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


def _cpu_name():
    import platform
    if os.name == "nt":
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            return winreg.QueryValueEx(k, "ProcessorNameString")[0].strip()
        except Exception:
            pass
    if platform.system() == "Darwin":
        return _run(["sysctl", "-n", "machdep.cpu.brand_string"]) or platform.machine()
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return platform.processor() or platform.machine()


def _gpus():
    import platform
    out = _run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"])
    gpus = []
    for line in out.splitlines():
        parts = [x.strip() for x in line.split(",")]
        if len(parts) == 3:
            gpus.append({"vendor": "nvidia", "name": parts[0], "vram_mb": int(float(parts[1] or 0)), "driver": parts[2]})
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        gpus.append({"vendor": "apple", "name": "GPU + Neural Engine tích hợp (Apple Silicon)", "vram_mb": 0, "driver": ""})
    return gpus


def hardware_info():
    import platform
    import onnxruntime as ort
    from importlib import metadata
    pkgs = []
    for name in ("onnxruntime-gpu", "onnxruntime", "onnxruntime-silicon"):
        try:
            pkgs.append(f"{name} {metadata.version(name)}")
        except Exception:
            pass
    av = ort.get_available_providers()
    gpus = _gpus()
    want = os.environ.get("POSE_TOOL_DEVICE", "auto").lower()
    avail = {"auto": True, "cpu": True, "cuda": "CUDAExecutionProvider" in av, "coreml": "CoreMLExecutionProvider" in av}
    hints = []
    is_mac = platform.system() == "Darwin"
    if any(g["vendor"] == "nvidia" for g in gpus) and not avail["cuda"]:
        hints.append({"level": "warn", "text": "Máy có GPU NVIDIA nhưng đang cài onnxruntime bản CPU. Chạy run_win_gpu.bat (Windows) để dùng GPU."})
    if is_mac and avail["coreml"] and want != "coreml":
        hints.append({"level": "info", "text": "Mac có thể thử CoreML (GPU/Neural Engine). Bấm Kiểm tra tốc độ để so với CPU trước khi chọn."})
    if not gpus and not is_mac:
        hints.append({"level": "info", "text": "Không thấy GPU NVIDIA. Xử lý bằng CPU."})
    return {
        "os": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "cpu": _cpu_name(),
        "cores": os.cpu_count(),
        "gpus": gpus,
        "ort": ort.__version__,
        "packages": pkgs,
        "providers": [p.replace("ExecutionProvider", "") for p in av],
        "available": avail,
        "selected": want,
        "active": (active_provider() or _providers()[0]).replace("ExecutionProvider", ""),
        "loaded": active_provider() is not None,
        "hints": hints,
        "model_dir": MODEL_DIR,
        "models": _model_sizes(),
    }


def _model_sizes():
    out = []
    base = os.path.join(MODEL_DIR, "models")
    for name in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        d = os.path.join(base, name)
        size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(d) for f in fs)
        out.append({"name": name, "mb": round(size / 1024 ** 2, 1)})
    return out


def benchmark(want, model="isnet-general-use", runs=3):
    import time
    import onnxruntime as ort
    if want != "auto" and _PROVIDER[want] not in ort.get_available_providers():
        return {"device": want, "ok": False, "error": "Không khả dụng trên máy này"}
    from rembg import new_session, remove
    img = Image.new("RGB", (768, 1024), (180, 160, 140))
    ImageDraw.Draw(img).ellipse((250, 150, 520, 900), fill=(60, 50, 45))
    t = time.time()
    try:
        sess = new_session(model, providers=_providers(want))
        remove(img, session=sess, only_mask=True)
        first = time.time() - t
        times = []
        for _ in range(runs):
            t = time.time()
            remove(img, session=sess, only_mask=True)
            times.append(time.time() - t)
        used = sess.inner_session.get_providers()[0].replace("ExecutionProvider", "")
    except Exception as e:
        return {"device": want, "ok": False, "error": str(e)}
    return {"device": want, "ok": True, "used": used, "first_ms": int(first * 1000), "ms": int(sorted(times)[len(times) // 2] * 1000)}


def person_mask(img: Image.Image, model: str) -> np.ndarray:
    os.makedirs(CACHE_DIR, exist_ok=True)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    key = hashlib.sha1(buf.getvalue() + model.encode()).hexdigest()
    path = os.path.join(CACHE_DIR, key + ".png")
    if os.path.exists(path):
        try:
            return np.array(Image.open(path).convert("L"))
        except Exception:
            pass
    from rembg import remove
    out = remove(img.convert("RGB"), session=_session(model), only_mask=True)
    m = np.array(out.convert("L"))
    tmp = f"{path}.{os.getpid()}.part"
    Image.fromarray(m).save(tmp, format="PNG")
    os.replace(tmp, path)
    return m


def clean_mask(m: np.ndarray) -> np.ndarray:
    h, w = m.shape
    b = (cv2.GaussianBlur(m, (0, 0), max(1.0, h / 600)) > 127).astype(np.uint8)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (max(3, h // 250) | 1,) * 2)
    b = cv2.morphologyEx(b, cv2.MORPH_CLOSE, k)
    b = cv2.morphologyEx(b, cv2.MORPH_OPEN, k)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(b, 8)
    keep = np.zeros_like(b)
    if n > 1:
        big = stats[1:, cv2.CC_STAT_AREA].max()
        for i in range(1, n):
            if stats[i, cv2.CC_STAT_AREA] >= big * 0.03:
                keep[lab == i] = 1
    return keep


def _resample(pts, step, closed):
    if closed:
        pts = np.vstack([pts, pts[:1]])
    if len(pts) < 2:
        return pts
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    if s[-1] < step * 2:
        return pts[:-1] if closed else pts
    t = np.arange(0, s[-1] + (0 if closed else step * 0.5), step)
    if not closed:
        t = np.append(t[t < s[-1]], s[-1])
    res = np.stack([np.interp(t, s, pts[:, 0]), np.interp(t, s, pts[:, 1])], 1)
    return res[:-1] if closed and len(res) > 2 else res


def _smooth(pts, sigma, closed):
    if sigma <= 0 or len(pts) < 5:
        return pts
    mode = "wrap" if closed else "nearest"
    out = np.stack([gaussian_filter1d(pts[:, 0], sigma, mode=mode), gaussian_filter1d(pts[:, 1], sigma, mode=mode)], 1)
    if not closed:
        out[0], out[-1] = pts[0], pts[-1]
    return out


def _length(p, closed=False):
    if len(p) < 2:
        return 0.0
    q = np.vstack([p, p[:1]]) if closed else p
    return float(np.linalg.norm(np.diff(q, axis=0), axis=1).sum())


def _split_border(p, closed, W, H, margin):
    if margin <= 0:
        return [(p, closed)]
    inside = (p[:, 0] > margin) & (p[:, 0] < W - 1 - margin) & (p[:, 1] > margin) & (p[:, 1] < H - 1 - margin)
    if inside.all():
        return [(p, closed)]
    if not inside.any():
        return []
    if closed:
        start = int(np.argmin(inside))
        p = np.roll(p, -start, axis=0)
        inside = np.roll(inside, -start)
    out = []
    cur = []
    for q, ok in zip(p, inside):
        if ok:
            cur.append(q)
        elif cur:
            out.append((np.array(cur), False))
            cur = []
    if cur:
        out.append((np.array(cur), False))
    return out


def outline_paths(body, st, unit):
    H, W = body.shape
    cs, hier = cv2.findContours(body, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    area = H * W
    paths = []
    if hier is None:
        return paths
    for c, hh in zip(cs, hier[0]):
        is_hole = hh[3] != -1
        a = cv2.contourArea(c)
        if is_hole and (not st.holes or a < 0.004 * area):
            continue
        if not is_hole and a < 0.002 * area:
            continue
        p = c[:, 0, :].astype(np.float64)
        p = _resample(p, max(1.0, unit), True)
        p = _smooth(p, st.smooth, True)
        paths.extend(_split_border(p, True, W, H, st.edge_margin * unit))
    return [(p, c) for p, c in paths if _length(p, c) > st.min_len * unit]


_N8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def trace_skeleton(sk: np.ndarray):
    sk = sk.astype(np.uint8)
    H, W = sk.shape
    deg = cv2.filter2D(sk, -1, np.ones((3, 3), np.float32), borderType=cv2.BORDER_CONSTANT).astype(np.int32) - 1
    deg[sk == 0] = 0
    jmask = ((deg >= 3) & (sk > 0)).astype(np.uint8)
    _, jlab = cv2.connectedComponents(jmask, connectivity=8)

    def nbrs(y, x):
        for dy, dx in _N8:
            yy, xx = y + dy, x + dx
            if 0 <= yy < H and 0 <= xx < W and sk[yy, xx]:
                yield yy, xx

    seen = np.zeros_like(sk, bool)
    paths = []
    ys, xs = np.nonzero((sk > 0) & ((deg != 2)))
    starts = list(zip(ys.tolist(), xs.tolist()))
    for sy, sx in starts:
        for ny, nx in nbrs(sy, sx):
            if seen[ny, nx] and not jmask[ny, nx]:
                continue
            if jmask[sy, sx] and jmask[ny, nx]:
                continue
            path = [(sy, sx)]
            prev, cur = (sy, sx), (ny, nx)
            while True:
                path.append(cur)
                if deg[cur] != 2:
                    break
                seen[cur] = True
                nxt = [q for q in nbrs(*cur) if q != prev and q not in path[-3:]]
                if not nxt:
                    break
                free = [q for q in nxt if not seen[q]] or nxt
                prev, cur = cur, free[0]
                if seen[cur] and deg[cur] == 2:
                    path.append(cur)
                    break
            if len(path) >= 2:
                paths.append(path)
    rest = (sk > 0) & (~seen) & (deg == 2)
    ys, xs = np.nonzero(rest)
    for sy, sx in zip(ys.tolist(), xs.tolist()):
        if seen[sy, sx]:
            continue
        path = [(sy, sx)]
        seen[sy, sx] = True
        prev, cur = None, (sy, sx)
        while True:
            nxt = [q for q in nbrs(*cur) if q != prev and not seen[q]]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            seen[cur] = True
            path.append(cur)
        if len(path) >= 3:
            paths.append(path)
    polys = []
    for p in paths:
        a = np.array([(x, y) for y, x in p], np.float64)
        ends = (int(jlab[p[0]]), int(jlab[p[-1]]))
        polys.append([a, ends])
    return _link(polys)


def _dir(a, at_end, k=6):
    if at_end:
        v = a[-1] - a[max(0, len(a) - 1 - k)]
    else:
        v = a[0] - a[min(len(a) - 1, k)]
    n = np.linalg.norm(v)
    return v / n if n else v


def _link(polys):
    polys = [p for p in polys if not (p[1][0] and p[1][0] == p[1][1] and len(p[0]) < 6)]
    by_j = {}
    for i, (a, (j0, j1)) in enumerate(polys):
        if j0:
            by_j.setdefault(j0, []).append((i, 0))
        if j1:
            by_j.setdefault(j1, []).append((i, 1))
    link = {}
    for j, ends in by_j.items():
        cand = []
        for x in range(len(ends)):
            for y in range(x + 1, len(ends)):
                (i, e), (k, f) = ends[x], ends[y]
                if i == k:
                    continue
                d1 = _dir(polys[i][0], e == 1)
                d2 = _dir(polys[k][0], f == 1)
                c = float(np.dot(d1, d2))
                if c < -0.6:
                    cand.append((c, ends[x], ends[y]))
        cand.sort()
        used = set()
        for c, u, v in cand:
            if u in used or v in used:
                continue
            used.add(u)
            used.add(v)
            link[u] = v
            link[v] = u
    done = [False] * len(polys)
    chains = []

    def walk(i, e):
        pts = []
        while True:
            done[i] = True
            a = polys[i][0]
            seg = a if e == 0 else a[::-1]
            pts.append(seg if not pts else seg[1:])
            out_end = (i, 1 - e)
            if out_end not in link:
                break
            i, e = link[out_end]
            if done[i]:
                break
        return np.vstack(pts)

    for i in range(len(polys)):
        if done[i]:
            continue
        if (i, 0) not in link:
            chains.append(walk(i, 0))
        elif (i, 1) not in link:
            chains.append(walk(i, 1))
    for i in range(len(polys)):
        if not done[i]:
            chains.append(walk(i, 0))
    return chains


def _postprocess(chains, scale, st, unit, W, H):
    out = []
    for c in chains:
        p = c / scale
        if _length(p) < st.min_len * unit:
            continue
        p = _resample(p, max(1.0, unit), False)
        p = _smooth(p, st.smooth, False)
        out.extend(_split_border(p, False, W, H, st.edge_margin * unit))
    return out


def photo_inner(img, body, st, unit):
    W, H = img.size
    scale = 1000 / H
    g = np.array(img.convert("L")).astype(np.float32) / 255
    g = cv2.resize(g, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    b = cv2.resize(body, g.shape[::-1], interpolation=cv2.INTER_NEAREST)
    g = cv2.bilateralFilter(g, 9, 0.1, 6)
    sig = 3.0 - 1.6 * st.detail
    t = 0.022 - 0.012 * st.detail
    d = cv2.GaussianBlur(g, (0, 0), sig) - cv2.GaussianBlur(g, (0, 0), sig * 1.6)
    e = (d < -t).astype(np.uint8)
    e[cv2.erode(b, np.ones((9, 9), np.uint8)) == 0] = 0
    n, lab, stt, _ = cv2.connectedComponentsWithStats(e, 8)
    keep = np.isin(lab, np.where(stt[:, cv2.CC_STAT_AREA] >= 120)[0][1:])
    chains = trace_skeleton(skeletonize(keep))
    return _postprocess(chains, scale, st, unit, W, H)


def lineart_chains(art: Image.Image, st, unit):
    a = np.array(art.convert("RGBA"))
    H, W = a.shape[:2]
    alpha = a[..., 3].astype(np.float32)
    if alpha.min() > 250:
        lum = cv2.cvtColor(a[..., :3], cv2.COLOR_RGB2GRAY).astype(np.float32)
        alpha = 255 - lum if lum.mean() > 127 else lum
    scale = min(1.0, 1400 / H)
    al = cv2.resize(alpha, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else alpha
    b = (al > 50).astype(np.uint8)
    b = cv2.morphologyEx(b, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    chains = trace_skeleton(skeletonize(b > 0))
    return _postprocess(chains, scale, st, unit, W, H)


def _dash_segments(p, closed, dash, gap):
    if closed:
        p = np.vstack([p, p[:1]])
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    total = s[-1]
    if total <= 0:
        return []
    period = dash + gap
    n = max(1, round((total + (0 if closed else gap)) / period))
    k = (total + (0 if closed else gap)) / (n * period)
    dash, period = dash * k, period * k
    out = []
    for i in range(n):
        t0 = i * period
        t1 = min(total, t0 + dash)
        if t1 <= t0:
            continue
        idx = (s > t0) & (s < t1)
        a = [np.interp(t0, s, p[:, 0]), np.interp(t0, s, p[:, 1])]
        b = [np.interp(t1, s, p[:, 0]), np.interp(t1, s, p[:, 1])]
        out.append(np.vstack([a, p[idx], b]))
    return out


def _dots(p, closed, spacing):
    if closed:
        p = np.vstack([p, p[:1]])
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    total = s[-1]
    if total <= 0:
        return []
    n = max(1, round(total / spacing))
    t = np.linspace(0, total, n + (0 if closed else 1), endpoint=not closed)
    return list(zip(np.interp(t, s, p[:, 0]), np.interp(t, s, p[:, 1])))


def _stroke(draw, pts, width):
    xy = [tuple(q) for q in pts]
    if len(xy) >= 2:
        draw.line(xy, fill=255, width=max(1, int(round(width))), joint="curve")
    r = width / 2
    for q in (xy[0], xy[-1]):
        draw.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=255)


def _draw(size, paths, kind, width, dash, gap, ss=2):
    W, H = size
    layer = Image.new("L", (W * ss, H * ss), 0)
    if kind == "none" or not paths:
        return np.zeros((H, W), np.float32)
    d = ImageDraw.Draw(layer)
    for p, closed in paths:
        q = p * ss
        if kind == "solid":
            _stroke(d, np.vstack([q, q[:1]]) if closed else q, width * ss)
        elif kind == "dash":
            for seg in _dash_segments(q, closed, dash * ss, gap * ss):
                _stroke(d, seg, width * ss)
        elif kind == "dots":
            r = width * ss / 2
            for x, y in _dots(q, closed, (width + gap) * ss):
                d.ellipse([x - r, y - r, x + r, y + r], fill=255)
    return np.array(layer.resize((W, H), Image.LANCZOS), np.float32) / 255


def _hex(c):
    c = (c or "#FFFFFF").lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _compose(W, H, a, line_a, st):
    rgb = _hex(st.color)
    out = np.zeros((H, W, 4), np.uint8)
    out[..., 0], out[..., 1], out[..., 2] = rgb
    out[..., 3] = np.clip(a * 255, 0, 255).astype(np.uint8)
    res = Image.fromarray(out, "RGBA")
    if st.shadow and st.shadow_opacity > 0:
        unit = H / 1000.0
        sa = Image.fromarray(np.clip(line_a * 255 * st.shadow_opacity, 0, 255).astype(np.uint8))
        sa = sa.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(max(0.5, st.shadow_blur * unit)))
        base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        base.putalpha(sa)
        base.alpha_composite(res)
        res = base
    return res


def _face_detector():
    global _face
    if _face is None:
        if not os.path.exists(FACE_MODEL):
            import urllib.request
            os.makedirs(os.path.dirname(FACE_MODEL), exist_ok=True)
            tmp = FACE_MODEL + ".part"
            urllib.request.urlretrieve(FACE_URL, tmp)
            os.replace(tmp, FACE_MODEL)
        _face = cv2.FaceDetectorYN.create(FACE_MODEL, "", (320, 320), 0.5, 0.3, 5000)
    return _face


FACE_SCORE, FACE_MIN_RATIO, BLOB_MIN_RATIO = 0.6, 0.15, 0.2


def face_boxes(img: Image.Image) -> np.ndarray:
    """Foreground faces as rows (x, y, w, h) in image pixels."""
    im = img.convert("RGB")
    s = min(1.0, 960 / max(im.size))
    if s < 1:
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.BILINEAR)
    bgr = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
    with _face_lock:
        det = _face_detector()
        det.setInputSize((bgr.shape[1], bgr.shape[0]))
        _, faces = det.detect(bgr)
    if faces is None:
        return np.zeros((0, 4))
    faces = faces[faces[:, -1] >= FACE_SCORE]
    if not len(faces):
        return np.zeros((0, 4))
    # Faces far smaller than the largest one are usually background passers-by.
    sizes = faces[:, 2] * faces[:, 3]
    return faces[sizes >= sizes.max() * FACE_MIN_RATIO, :4] / s


def count_faces(img: Image.Image) -> int:
    return len(face_boxes(img))


COUNT_DET_SCORE, COUNT_DET_H = 0.4, 0.4


def count_faceless(img: Image.Image) -> int:
    """People in a photo with no visible face: separate cut-out regions, or YOLOX hits when friends touch.
    0 when nobody is detected (pets, objects) so auto picks the general model."""
    rgb = np.array(img.convert("RGB"))
    m = clean_mask(person_mask(img.convert("RGB"), GROUP_MODEL)).astype(np.uint8)
    if not m.any():
        return 0
    b = _detect_zoomed(rgb, m.astype(bool))
    b = b[b[:, 4] >= COUNT_DET_SCORE]
    if not len(b):
        return 0
    h = b[:, 3] - b[:, 1]
    n, _, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    areas = stats[1:, cv2.CC_STAT_AREA]
    return max(int((areas >= areas.max() * BLOB_MIN_RATIO).sum()), int((h >= COUNT_DET_H * h.max()).sum()))


def count_people(img: Image.Image) -> int:
    # Faces first; back views, upside-down and tiny faces have none.
    n = count_faces(img)
    return n if n else count_faceless(img)


def resolve_model(img: Image.Image, model: str, people: int = None):
    if model != "auto":
        return model, people
    if people is None:
        people = count_people(img)
    return (SOLO_MODEL if people == 1 else GROUP_MODEL), people


def _download(url, dst, member=None):
    import urllib.request
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + ".part"
    urllib.request.urlretrieve(url, tmp)
    if member:
        import zipfile
        with zipfile.ZipFile(tmp) as z:
            name = next(n for n in z.namelist() if n.endswith(member))
            with z.open(name) as src, open(dst + ".unz", "wb") as out:
                out.write(src.read())
        os.remove(tmp)
        tmp = dst + ".unz"
    os.replace(tmp, dst)


def _aux_session(key):
    with _session_lock:
        if key not in _aux:
            import onnxruntime as ort
            if key == "sam":
                from types import SimpleNamespace
                from rembg.sessions.sam import SamSession
                # ViT-L separates overlapping people far better, but its encoder is too slow for batches on CPU.
                big = _providers()[0] != "CPUExecutionProvider"
                enc, dec = SamSession.download_models(sam_model="sam_vit_l_0b3195" if big else "sam_vit_b_01ec64")
                # rembg's SamSession ignores providers and would run on CPU even with CUDA available.
                _aux[key] = SimpleNamespace(encoder=ort.InferenceSession(str(enc), providers=_providers()),
                                            decoder=ort.InferenceSession(str(dec), providers=_providers()))
            else:
                path, url, member = (DET_MODEL, DET_URL, None) if key == "det" else (POSE_MODEL, POSE_URL, "end2end.onnx")
                if not os.path.exists(path):
                    _download(url, path, member)
                _aux[key] = ort.InferenceSession(path, providers=_providers())
        return _aux[key]


def detect_people(rgb, score=0.3, nms=0.45):
    H, W = rgb.shape[:2]
    s = _aux_session("det")
    r = min(640 / W, 640 / H)
    pad = np.full((640, 640, 3), 114, np.uint8)
    pad[:int(H * r), :int(W * r)] = cv2.resize(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), (int(W * r), int(H * r)))
    out = s.run(None, {s.get_inputs()[0].name: pad.transpose(2, 0, 1)[None].astype(np.float32)})[0][0]
    grids, strides = [], []
    for st in (8, 16, 32):
        g = 640 // st
        yv, xv = np.meshgrid(np.arange(g), np.arange(g), indexing="ij")
        grids.append(np.stack([xv, yv], -1).reshape(-1, 2))
        strides.append(np.full((g * g, 1), st))
    grids, strides = np.concatenate(grids), np.concatenate(strides)
    xy = (out[:, :2] + grids) * strides
    wh = np.exp(out[:, 2:4]) * strides
    conf = out[:, 4] * out[:, 5]
    ok = conf > score
    b = np.concatenate([xy - wh / 2, xy + wh / 2], 1)[ok] / r
    conf = conf[ok]
    if not len(b):
        return np.zeros((0, 5))
    idx = np.array(cv2.dnn.NMSBoxes(np.concatenate([b[:, :2], b[:, 2:] - b[:, :2]], 1).tolist(), conf.tolist(), score, nms)).flatten()
    return np.concatenate([b[idx], conf[idx, None]], 1)


_POSE_MEAN = np.array([123.675, 116.28, 103.53], np.float32)
_POSE_STD = np.array([58.395, 57.12, 57.375], np.float32)


def keypoints(rgb, box):
    x0, y0, x1, y1 = box[:4]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = (x1 - x0) * 1.25, (y1 - y0) * 1.25
    if w / h > 192 / 256:
        h = w * 256 / 192
    else:
        w = h * 192 / 256
    M = cv2.getAffineTransform(np.float32([[cx - w / 2, cy - h / 2], [cx + w / 2, cy - h / 2], [cx - w / 2, cy + h / 2]]),
                               np.float32([[0, 0], [192, 0], [0, 256]]))
    crop = cv2.warpAffine(rgb, M, (192, 256), flags=cv2.INTER_LINEAR)
    s = _aux_session("pose")
    sx, sy = s.run(None, {s.get_inputs()[0].name: ((crop.astype(np.float32) - _POSE_MEAN) / _POSE_STD).transpose(2, 0, 1)[None]})
    kx, ky = sx[0].argmax(1) / 2.0, sy[0].argmax(1) / 2.0
    conf = np.minimum(sx[0].max(1), sy[0].max(1))
    pts = np.stack([kx, ky, np.ones_like(kx)], 1) @ cv2.invertAffineTransform(M).T
    return np.concatenate([pts, conf[:, None]], 1)


KP_SCORE, PERSON_MIN_H, SAME_PERSON, OFFBODY_CONF, OFFBODY_SIZE = 0.3, 0.3, 0.03, 0.6, 0.6
DET_SCORE, WEAK_SCORE, WEAK_KPS, WEAK_ONBODY = 0.3, 0.1, 12, 0.8


def _detect_zoomed(rgb, body):
    """YOLOX on the whole frame plus on the cut-out's bounding box: small seated people and drawn figures only
    clear the threshold once zoomed in."""
    boxes = detect_people(rgb, score=WEAK_SCORE, nms=0.6)
    H, W = body.shape
    ys, xs = np.nonzero(body)
    if len(ys):
        m = int(0.05 * H)
        x0, y0, x1, y1 = max(0, xs.min() - m), max(0, ys.min() - m), min(W, xs.max() + m), min(H, ys.max() + m)
        if (x1 - x0) * (y1 - y0) < 0.6 * W * H:
            zb = detect_people(rgb[y0:y1, x0:x1], score=WEAK_SCORE, nms=0.6)
            zb[:, [0, 2]] += x0
            zb[:, [1, 3]] += y0
            boxes = np.concatenate([boxes, zb])
    if len(boxes) < 2:
        return boxes
    idx = np.array(cv2.dnn.NMSBoxes(np.concatenate([boxes[:, :2], boxes[:, 2:4] - boxes[:, :2]], 1).tolist(),
                                    boxes[:, 4].tolist(), WEAK_SCORE, 0.6)).flatten()
    return boxes[idx]


def _face_person_box(f, W, H):
    x, y, w, h = f
    cx = x + w / 2
    return np.array([max(0, cx - 2.5 * w), max(0, y - 0.6 * h), min(W, cx + 2.5 * w), min(H, y + 8 * h), 0.0])


def _people(rgb, body, min_people=2, soft=None):
    H, W = body.shape
    # isnet leaves dark shirts and back-of-head half-transparent; they still count as on the cut-out here.
    on = body if soft is None else body | (soft > SOFT_MIN)
    boxes = _detect_zoomed(rgb, body)
    faces = face_boxes(Image.fromarray(rgb))
    strong = boxes[boxes[:, 4] >= DET_SCORE]
    if max(len(strong), len(faces)) < min_people:
        return []
    hmax = (strong[:, 3] - strong[:, 1]).max() if len(strong) else H
    people = []

    def merge(qb, q, k, b):
        # Same body, but its box cut the head off or the head scored too low; take the face-anchored joints.
        better = k[:, 2] > q[:, 2]
        q[better] = k[better]
        qb[:2] = np.minimum(qb[:2], b[:2])
        qb[2:4] = np.maximum(qb[2:4], b[2:4])

    def add(b, k, face=False):
        good = k[:, 2] > KP_SCORE
        if good.sum() < 5:
            return False
        xs = np.clip(k[good, 0].astype(int), 0, W - 1)
        ys = np.clip(k[good, 1].astype(int), 0, H - 1)
        if not face and b[4] < DET_SCORE and (good.sum() < WEAK_KPS or on[ys, xs].mean() < WEAK_ONBODY):
            return False
        # Balcony passers-by and false boxes land mostly off the cut-out; a large confident detection is real even
        # when isnet missed the person (lying on a picnic mat).
        big = b[4] >= OFFBODY_CONF and max(b[2] - b[0], b[3] - b[1]) >= OFFBODY_SIZE * hmax
        if on[ys, xs].mean() < 0.5 and not big:
            return False
        for qb, q in people:
            g = good & (q[:, 2] > KP_SCORE)
            if g.sum() >= 4 and np.median(np.linalg.norm(k[g, :2] - q[g, :2], axis=1)) < SAME_PERSON * H:
                if face:
                    merge(qb, q, k, b)
                return False
        people.append((b, k))
        return True

    for b in boxes[np.argsort(-boxes[:, 4])]:
        if b[3] - b[1] >= PERSON_MIN_H * hmax:
            add(b, keypoints(rgb, b))
    # The detector misses people mostly hidden behind friends; a visible face still anchors them.
    for f in faces:
        x, y, w, h = f

        def in_face(k):
            return ((k[:5, 2] > KP_SCORE) & (k[:5, 0] >= x) & (k[:5, 0] <= x + w) & (k[:5, 1] >= y) & (k[:5, 1] <= y + h)).sum()

        owner = next((p for p in people if in_face(p[1]) >= 2), None)
        if owner is not None and owner[0][1] <= y:
            continue
        fb = _face_person_box(f, W, H)
        k = keypoints(rgb, fb)
        # Pose on a crowded crop can lock onto a neighbour; the head must sit on this face.
        if in_face(k) < 2:
            continue
        k[~((k[:, 0] >= fb[0]) & (k[:, 0] <= fb[2]) & (k[:, 1] >= fb[1]) & (k[:, 1] <= fb[3])), 2] = 0
        p = k[k[:, 2] > KP_SCORE, :2]
        pad = 0.6 * w
        # Box from the keypoints, not the guess, so SAM's box prompt doesn't swallow neighbours.
        b = np.array([max(0, p[:, 0].min() - pad), max(0, min(y, p[:, 1].min()) - 0.3 * h), min(W, p[:, 0].max() + pad), min(H, p[:, 1].max() + pad), 0.0])
        if owner is not None:
            merge(owner[0], owner[1], k, b)
        else:
            add(b, k, face=True)
    return people


def _sam_embed(sam, rgb):
    h0, w0 = rgb.shape[:2]
    s = min(1024 / w0, 684 / h0)
    w, h = round(w0 * s), round(h0 * s)
    pad = np.zeros((684, 1024, 3), np.float32)
    pad[:h, :w] = cv2.resize(rgb, (w, h), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    return sam.encoder.run(None, {sam.encoder.get_inputs()[0].name: pad})[0], s, w, h


def _sam_decode(sam, emb, pts, labels, passes=1):
    mi, has = np.zeros((1, 1, 256, 256), np.float32), np.zeros(1, np.float32)
    for _ in range(passes):
        m, iou, low = sam.decoder.run(None, {
            "image_embeddings": emb, "point_coords": np.asarray(pts, np.float32)[None],
            "point_labels": np.asarray(labels, np.float32)[None], "mask_input": mi, "has_mask_input": has,
            "orig_im_size": np.array([684, 1024], np.float32)})
        mi, has = low.astype(np.float32), np.ones(1, np.float32)
    return m[0, 0], float(iou[0, 0])


BODY_GROW, BODY_KEEP, SOFT_MIN, SAM_TRUST, SAM_EXTRA = 0.04, 0.06, 25, 0.88, 0.6


def person_labels(img: Image.Image, body: np.ndarray, soft: np.ndarray = None):
    """Full-res label map (0 = background, label n+1 = people[n]) plus each person's keypoints; the cut-out is
    extended where SAM finds body parts isnet dropped."""
    from scipy.ndimage import distance_transform_edt
    rgb = np.array(img.convert("RGB"))
    H, W = body.shape
    people = _people(rgb, body.astype(bool), min_people=1, soft=soft)
    if not people:
        return body.astype(np.uint8), np.zeros((0, 17, 3))
    sam = _aux_session("sam")
    emb, s, w, h = _sam_embed(sam, rgb)
    sb = cv2.resize(body, (w, h), interpolation=cv2.INTER_NEAREST).astype(bool)
    # isnet drops dark hair against dark backgrounds; only accept SAM pixels hugging the existing cut-out.
    near = distance_transform_edt(~sb) <= BODY_GROW * h
    if soft is not None:
        # Pale dresses come out of isnet half-transparent and fall under clean_mask's cut; SAM may reclaim them.
        near |= cv2.resize(soft, (w, h), interpolation=cv2.INTER_AREA) > SOFT_MIN
    own_pts = [k[k[:, 2] > KP_SCORE, :2] for _, k in people]
    # Feet lower in frame = closer to camera, so paint back to front and let the front person win overlaps.
    feet = [max([b[3]] + [y for _, y, c in k[15:17] if c > KP_SCORE]) for b, k in people]
    margin = 0.04 * H
    lab = np.zeros((h, w), np.uint8)
    for n in np.argsort(feet):
        b = people[n][0]
        own = own_pts[n]
        neg = [p for j, o in enumerate(own_pts) if j != n for p in o
               if b[0] <= p[0] <= b[2] and b[1] <= p[1] <= b[3] and np.linalg.norm(own - p, axis=1).min() > 0.04 * H]
        neg = np.array(neg).reshape(-1, 2)
        pts = np.concatenate([[b[:2], b[2:4]], own, neg, [[0, 0]]]) * s
        labels = np.concatenate([[2, 3], np.ones(len(own)), np.zeros(len(neg)), [-1]])
        m, iou = _sam_decode(sam, emb, pts, labels, passes=2)
        x0, y0, x1, y1 = [int(v * s) for v in (b[0] - margin, b[1] - margin, b[2] + margin, b[3] + margin)]
        box = np.zeros((h, w), bool)
        box[max(0, y0):y1, max(0, x0):x1] = True
        m = m[:h, :w] > 0
        inside = m & (sb | near)
        extra = m & ~(sb | near) & box
        kp = np.clip((own * s).astype(int), 0, [w - 1, h - 1])
        missed = sb[kp[:, 1], kp[:, 0]].mean() < 0.5
        # isnet sometimes drops whole skirt panels, or the whole person; trust a confident SAM mask to extend it.
        if iou > SAM_TRUST and (missed or extra.sum() < SAM_EXTRA * inside.sum()):
            m = inside | extra
        else:
            m = inside
        lab[m & box] = n + 1
    for v in range(1, len(people) + 1):
        cnt, cc, stats, _ = cv2.connectedComponentsWithStats((lab == v).astype(np.uint8), 8)
        if cnt > 2:
            # A front person's arm can cut someone's head off as a separate island; keep islands holding their own keypoints.
            areas = stats[1:, cv2.CC_STAT_AREA]
            kp = (own_pts[v - 1] * s).astype(int)
            kp = kp[(kp[:, 0] >= 0) & (kp[:, 0] < w) & (kp[:, 1] >= 0) & (kp[:, 1] < h)]
            anchored = set(cc[kp[:, 1], kp[:, 0]].tolist())
            for i in range(1, cnt):
                if areas[i - 1] < 0.15 * areas.max() and i not in anchored:
                    lab[cc == i] = 0
    body = body.astype(bool)
    if lab.any():
        d, (iy, ix) = distance_transform_edt(lab == 0, return_indices=True)
        # Swings, railings and props isnet fuses onto people sit far from every person SAM found.
        far = sb & (d > BODY_KEEP * h)
        sb &= ~far
        body = body & ~(cv2.resize(far.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0)
    ext = sb | (lab > 0)
    if lab.any():
        lab = lab[iy, ix]
    lab[~ext] = 0
    full = cv2.resize(cv2.medianBlur(lab, 7), (W, H), interpolation=cv2.INTER_NEAREST)
    grow = cv2.resize(ext.astype(np.uint8), (W, H), interpolation=cv2.INTER_LINEAR) > 0
    full[~(body | grow)] = 0
    holes = body & (full == 0)
    if holes.any() and full.any():
        _, (iy, ix) = distance_transform_edt(full == 0, return_indices=True)
        full[holes] = full[iy, ix][holes]
    return full, np.stack([k for _, k in people])


PART_STEP, PART_IOU, PART_STABLE = 0.03, 0.75, 0.8
_ARMS = [(5, 7, 9), (6, 8, 10)]
_TORSO = [0, 11, 12]


def _limb_mask(sam, emb, k, sh, el, wr, region):
    ok = k[:, 2] > KP_SCORE
    if not (ok[el] and ok[wr]):
        return None
    pos = [k[el, :2], k[wr, :2], (k[el, :2] + k[wr, :2]) / 2]
    if ok[sh]:
        pos.append(k[sh, :2] * 0.4 + k[el, :2] * 0.6)
    other = sh + 1 if sh == 5 else sh - 1
    neg = [k[i, :2] for i in _TORSO + [other] if ok[i]]
    pos, neg = np.array(pos), np.array(neg).reshape(-1, 2)
    # Torso keypoints right next to the arm would cut the elbow off; drop them.
    neg = neg[[np.linalg.norm(pos - q, axis=1).min() > 0.08 * region.shape[0] for q in neg]] if len(neg) else neg
    pts = np.concatenate([pos, neg, [[0, 0]]])
    labels = [1] * len(pos) + [0] * len(neg) + [-1]
    lg, iou = _sam_decode(sam, emb, pts, labels, passes=2)
    h, w = region.shape
    m = (lg[:h, :w] > 0) & region
    if iou < 0.7 or m.sum() < 40 or m.sum() > 0.4 * region.sum():
        return None
    return m


def person_parts(img: Image.Image, lab: np.ndarray, kps: np.ndarray) -> np.ndarray:
    """Per-person SAM segments (hair, face, sleeves, trousers...) as int labels person*1000+k; each person is
    encoded from its own crop because at whole-group scale a face is only a few pixels."""
    rgb = np.array(img.convert("RGB"))
    H, W = lab.shape
    sam = _aux_session("sam")
    seg = lab.astype(np.int32) * 1000
    for v in range(1, int(lab.max()) + 1):
        region_full = lab == v
        ys, xs = np.nonzero(region_full)
        if len(ys) < 100:
            continue
        m = int(0.02 * H)
        x0, y0, x1, y1 = max(0, xs.min() - m), max(0, ys.min() - m), min(W, xs.max() + m + 1), min(H, ys.max() + m + 1)
        emb, s, w, h = _sam_embed(sam, rgb[y0:y1, x0:x1])
        region = cv2.resize(region_full[y0:y1, x0:x1].astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST).astype(bool)
        step = max(4, int(PART_STEP * h))
        gy, gx = np.mgrid[step // 2:h:step, step // 2:w:step]
        segs = []
        for x, y in zip(gx.ravel(), gy.ravel()):
            if not region[y, x]:
                continue
            lg, iou = _sam_decode(sam, emb, [[x, y], [0, 0]], [1, -1])
            lg = lg[:h, :w]
            mk = (lg > 0) & region
            area = mk.sum()
            hi, lo = ((lg > 1) & region).sum(), ((lg > -1) & region).sum()
            if iou < PART_IOU or area < 40 or lo == 0 or hi / lo < PART_STABLE or area > 0.85 * region.sum():
                continue
            segs.append((area, mk))
        segs.sort(key=lambda q: -q[0])
        keep = []
        for area, mk in segs:
            if all((mk & k).sum() / (mk | k).sum() < 0.8 for k in keep):
                keep.append(mk)
        local = np.zeros((h, w), np.int32)
        for i, mk in enumerate(keep):  # large first, so small parts (face, hands) stay on top
            local[mk] = i + 1
        if v <= len(kps):
            # Sleeves matching the jacket colour merge into the torso on a plain grid; segment arms from the skeleton.
            k = kps[v - 1].copy()
            k[:, 0] = (k[:, 0] - x0) * s
            k[:, 1] = (k[:, 1] - y0) * s
            for j, (sh, el, wr) in enumerate(_ARMS):
                arm = _limb_mask(sam, emb, k, sh, el, wr, region)
                if arm is not None:
                    local[arm] = 900 + j
        local = cv2.resize(local.astype(np.float32), (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST).astype(np.int32)
        sub = seg[y0:y1, x0:x1]
        rf = region_full[y0:y1, x0:x1]
        sub[rf] = v * 1000 + local[rf]
    seg = cv2.medianBlur(seg.astype(np.float32), 5).astype(np.int32)
    seg[lab == 0] = 0
    return seg


def _split_cached(img, body, soft=None):
    os.makedirs(CACHE_DIR, exist_ok=True)
    big = _providers()[0] != "CPUExecutionProvider"
    key = hashlib.sha1(np.ascontiguousarray(body).tobytes() + img.convert("RGB").tobytes() + (b"" if soft is None else np.ascontiguousarray(soft).tobytes()) + (b"split11-L" if big else b"split11-B")).hexdigest()
    path = os.path.join(CACHE_DIR, key + ".split.npz")
    if os.path.exists(path):
        try:
            with np.load(path) as z:
                return z["lab"], z["seg"]
        except Exception:
            pass
    lab, kps = person_labels(img, body, soft)
    seg = person_parts(img, lab, kps)
    tmp = f"{path}.{os.getpid()}.part.npz"
    np.savez_compressed(tmp, lab=lab, seg=seg)
    os.replace(tmp, path)
    return lab, seg


def _label_edges(L):
    e = np.zeros(L.shape, bool)
    a, b = L[:, :-1], L[:, 1:]
    e[:, :-1] |= (a != b) & (a > 0) & (b > 0)
    a, b = L[:-1], L[1:]
    e[:-1] |= (a != b) & (a > 0) & (b > 0)
    return cv2.dilate(e.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0


def _edge_paths(e, st, unit, W, H):
    return _postprocess(trace_skeleton(skeletonize(e)), 1.0, st, unit, W, H) if e.any() else []


def render_photo(img: Image.Image, st: Style, mask: np.ndarray = None) -> Image.Image:
    img = img.convert("RGB")
    W, H = img.size
    unit = H / 1000.0
    if mask is None:
        mask = person_mask(img, resolve_model(img, st.model)[0])
    body = clean_mask(mask)
    lab = seg = None
    if st.split:
        lab, seg = _split_cached(img, body, mask)
        body = (lab > 0).astype(np.uint8)
    outer = outline_paths(body, st, unit) if st.outline != "none" else []
    a = _draw((W, H), outer, st.outline, st.width * unit, st.dash * unit, st.gap * unit) * st.opacity
    line_a = a.copy()
    if st.split:
        between = _label_edges(lab)
        # Separators use the thin inner stroke; presets without inner lines still need them visible, so borrow the outline kind.
        kind = st.inner if st.inner != "none" else st.outline
        sa = _draw((W, H), _edge_paths(between, st, unit, W, H), kind, st.inner_width * unit, st.inner_dash * unit, st.inner_gap * unit) * st.inner_opacity
        a = np.maximum(a, sa)
        line_a = np.maximum(line_a, sa)
    if st.inner != "none":
        inner = _edge_paths(_label_edges(seg) & ~between, st, unit, W, H) if st.split else photo_inner(img, body, st, unit)
        ia = _draw((W, H), inner, st.inner, st.inner_width * unit, st.inner_dash * unit, st.inner_gap * unit) * st.inner_opacity
        a = np.maximum(a, ia)
        line_a = np.maximum(line_a, ia)
    if st.fill:
        fm = cv2.GaussianBlur(body.astype(np.float32), (0, 0), max(0.6, unit))
        a = np.maximum(a, fm * st.fill_opacity)
    return _compose(W, H, a, line_a, st)


def render_lineart(art: Image.Image, st: Style) -> Image.Image:
    W, H = art.size
    unit = H / 1000.0
    chains = lineart_chains(art, st, unit)
    major = [(p, c) for p, c in chains if _length(p) >= st.major_len * unit]
    minor = [(p, c) for p, c in chains if _length(p) < st.major_len * unit]
    a = _draw((W, H), major, st.outline, st.width * unit, st.dash * unit, st.gap * unit) * st.opacity
    ia = _draw((W, H), minor, st.inner, st.inner_width * unit, st.inner_dash * unit, st.inner_gap * unit) * st.inner_opacity
    a = np.maximum(a, ia)
    line_a = a.copy()
    if st.fill:
        al = np.array(art.convert("RGBA"))[..., 3]
        b = cv2.morphologyEx((al > 50).astype(np.uint8), cv2.MORPH_CLOSE, np.ones((int(25 * unit) | 1,) * 2, np.uint8))
        cs, _ = cv2.findContours(b, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        fm = np.zeros_like(b)
        cv2.drawContours(fm, cs, -1, 1, -1)
        fm = cv2.GaussianBlur(fm.astype(np.float32), (0, 0), max(0.6, unit))
        a = np.maximum(a, fm * st.fill_opacity)
    return _compose(W, H, a, line_a, st)


def render(src: Image.Image, st: Style, mask: np.ndarray = None) -> Image.Image:
    if st.source == "lineart":
        return render_lineart(src, st)
    return render_photo(src, st, mask)


def composite(photo: Image.Image, overlay: Image.Image, dim: float = 0.0) -> Image.Image:
    p = photo.convert("RGBA")
    ow, oh = overlay.size
    s = max(ow / p.width, oh / p.height)
    p = p.resize((max(ow, int(p.width * s)), max(oh, int(p.height * s))))
    l, t = (p.width - ow) // 2, (p.height - oh) // 2
    p = p.crop((l, t, l + ow, t + oh))
    if dim:
        p = Image.blend(p, Image.new("RGBA", p.size, (0, 0, 0, 255)), dim)
    p.alpha_composite(overlay)
    return p


def checker(size, overlay):
    W, H = size
    c = 24
    yy, xx = np.mgrid[0:H, 0:W]
    g = np.where(((yy // c) + (xx // c)) % 2 == 0, 70, 50).astype(np.uint8)
    bg = Image.fromarray(np.stack([g, g, g, np.full_like(g, 255)], -1), "RGBA")
    bg.alpha_composite(overlay)
    return bg
