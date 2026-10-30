import hashlib
import io
import os
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
MODELS = ["isnet-general-use", "u2net_human_seg", "u2net", "birefnet-portrait"]
STROKES = ["none", "solid", "dash", "dots"]
SOURCES = ["photo", "lineart"]

_sessions = {}


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
        known = {k: v for k, v in (d or {}).items() if k in cls.__dataclass_fields__}
        return cls(**known)


PRESETS = {
    "1. Dash viền ngoài": Style(source="photo", outline="dash", inner="none"),
    "2. Dash ngoài + nét trong mảnh": Style(source="photo", outline="dash", inner="solid"),
    "3. Chấm tròn + phủ mờ": Style(source="photo", outline="dots", width=5.0, gap=9.0, inner="none", fill=True),
    "4. Liền + glow + phủ mờ": Style(source="photo", outline="solid", width=3.5, inner="solid", inner_opacity=0.45, fill=True, fill_opacity=0.12, shadow_opacity=0.6, shadow_blur=5.0),
    "5. Restyle line-art: dash chính + liền phụ": Style(source="lineart", outline="dash", width=3.5, dash=14.0, gap=9.0, inner="solid", inner_width=2.0, inner_opacity=0.7),
    "6. Restyle line-art: dash toàn phần": Style(source="lineart", outline="dash", width=3.0, dash=12.0, gap=8.0, inner="dash", inner_width=2.4, inner_opacity=0.85),
}


def _session(model):
    if model not in _sessions:
        from rembg import new_session
        _sessions[model] = new_session(model, providers=_providers())
    return _sessions[model]


def _providers():
    import onnxruntime as ort
    av = ort.get_available_providers()
    want = os.environ.get("POSE_TOOL_DEVICE", "auto").lower()
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


def device_info():
    import onnxruntime as ort
    return ", ".join(p.replace("ExecutionProvider", "") for p in _providers()) + f" (ORT {ort.__version__})"


def person_mask(img: Image.Image, model: str) -> np.ndarray:
    os.makedirs(CACHE_DIR, exist_ok=True)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    key = hashlib.sha1(buf.getvalue() + model.encode()).hexdigest()
    path = os.path.join(CACHE_DIR, key + ".png")
    if os.path.exists(path):
        return np.array(Image.open(path).convert("L"))
    from rembg import remove
    out = remove(img.convert("RGB"), session=_session(model), only_mask=True)
    m = np.array(out.convert("L"))
    Image.fromarray(m).save(path)
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


def render_photo(img: Image.Image, st: Style, mask: np.ndarray = None) -> Image.Image:
    img = img.convert("RGB")
    W, H = img.size
    unit = H / 1000.0
    if mask is None:
        mask = person_mask(img, st.model)
    body = clean_mask(mask)
    outer = outline_paths(body, st, unit) if st.outline != "none" else []
    a = _draw((W, H), outer, st.outline, st.width * unit, st.dash * unit, st.gap * unit) * st.opacity
    line_a = a.copy()
    if st.inner != "none":
        inner = photo_inner(img, body, st, unit)
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
