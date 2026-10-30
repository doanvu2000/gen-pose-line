import base64
import glob
import io
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
import uuid
import webbrowser

from flask import Flask, jsonify, request, send_from_directory
from PIL import Image, ImageOps

import pose_core as pc

ROOT = pc.ROOT
DL_DIR = os.path.join(ROOT, ".cache", "download")
STYLE_DIR = os.path.join(ROOT, "styles")
INPUT_DIR = os.path.join(ROOT, ".cache", "inputs")
OUTPUT_DIR = os.path.join(ROOT, "output")
IMG_EXT = (".png", ".jpg", ".jpeg", ".webp")
UA = {"User-Agent": "Mozilla/5.0 PoseLineTool"}

app = Flask(__name__, static_folder=os.path.join(ROOT, "static"), static_url_path="/static")
app.config["MAX_FORM_PARTS"] = 20000
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 ** 3
work_lock = threading.Lock()
pick_lock = threading.Lock()
uploads = {}
SCAN_CAP = 50000


@app.before_request
def same_origin_only():
    # Any web page can POST to 127.0.0.1 without preflight; only accept writes from this app's own pages.
    origin = request.headers.get("Origin")
    if request.method == "POST" and origin and origin.split("://", 1)[-1] != request.host:
        return jsonify(error="Yêu cầu bị chặn (khác nguồn)"), 403


def _b64(img, fmt="PNG", max_side=None):
    if max_side and max(img.size) > max_side:
        s = max_side / max(img.size)
        img = img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS)
    buf = io.BytesIO()
    if fmt == "JPEG":
        img.convert("RGB").save(buf, "JPEG", quality=88)
    else:
        img.save(buf, "PNG")
    return f"data:image/{fmt.lower()};base64," + base64.b64encode(buf.getvalue()).decode()


def _fetch(url):
    os.makedirs(DL_DIR, exist_ok=True)
    name = url.split("?")[0].rstrip("/").rsplit("/", 1)[-1] or uuid.uuid4().hex
    path = os.path.join(DL_DIR, name)
    if not os.path.exists(path):
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            data = r.read()
        tmp = f"{path}.{uuid.uuid4().hex[:6]}.part"
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    return path


def _load(path):
    if path.startswith("http://") or path.startswith("https://"):
        path = _fetch(path)
    im = Image.open(path)
    im.load()
    return ImageOps.exif_transpose(im)


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/meta")
def meta():
    os.makedirs(STYLE_DIR, exist_ok=True)
    saved = {}
    for f in sorted(glob.glob(os.path.join(STYLE_DIR, "*.json"))):
        try:
            saved[os.path.splitext(os.path.basename(f))[0]] = json.load(open(f, encoding="utf-8"))
        except Exception:
            pass
    return jsonify(
        presets={k: v.to_dict() for k, v in pc.PRESETS.items()},
        saved=saved,
        defaults=pc.Style().to_dict(),
        models=pc.MODELS,
        strokes=pc.STROKES,
        sources=pc.SOURCES,
        device=pc.device_info(),
        root=ROOT,
    )


@app.post("/api/upload")
def upload():
    out = []
    for f in request.files.getlist("files"):
        im = Image.open(f.stream)
        im.load()
        im = ImageOps.exif_transpose(im)
        uid = uuid.uuid4().hex[:10]
        uploads[uid] = (f.filename, im)
        out.append({"id": uid, "name": f.filename, "thumb": _b64(im.convert("RGB"), "JPEG", 240), "hasAlpha": im.mode in ("RGBA", "LA", "P") and _has_alpha(im)})
    return jsonify(items=out)


def _has_alpha(im):
    a = im.convert("RGBA").getchannel("A")
    return a.getextrema()[0] < 250


@app.post("/api/add_path")
def add_path():
    p = (request.json or {}).get("path", "").strip().strip('"')
    files = []
    if p.startswith("http") and p.lower().endswith(".json"):
        files = [u for u, _ in _json_items(p, (request.json or {}).get("field", "previewUrl"))][:20]
    elif os.path.isdir(p):
        files = _scan(p)[:20]
    elif p:
        files = [p]
    out = []
    for fp in files:
        try:
            im = _load(fp)
        except Exception as e:
            return jsonify(error=f"{fp}: {e}"), 400
        uid = uuid.uuid4().hex[:10]
        name = os.path.basename(fp.split("?")[0])
        uploads[uid] = (name, im)
        out.append({"id": uid, "name": name, "thumb": _b64(im.convert("RGB"), "JPEG", 240), "hasAlpha": _has_alpha(im)})
    return jsonify(items=out)


@app.post("/api/preview")
def preview():
    body = request.json or {}
    uid = body.get("id")
    if uid not in uploads:
        return jsonify(error="Ảnh không còn, thêm lại ảnh"), 404
    st = pc.Style.from_dict(body.get("style"))
    name, im = uploads[uid]
    t = time.time()
    try:
        with work_lock:
            ov = pc.render(im, st)
    except Exception as e:
        traceback.print_exc()
        return jsonify(error=str(e)), 500
    dt = time.time() - t
    bg = body.get("bg", "photo")
    ref = body.get("ref")
    if bg == "photo" and st.source == "photo":
        view = pc.composite(im, ov, float(body.get("dim", 0.2)))
    elif bg == "photo" and ref in uploads:
        view = pc.composite(uploads[ref][1], ov, float(body.get("dim", 0.2)))
    elif bg == "dark":
        view = Image.new("RGBA", ov.size, (28, 28, 30, 255))
        view.alpha_composite(ov)
    elif bg == "light":
        view = Image.new("RGBA", ov.size, (235, 235, 235, 255))
        view.alpha_composite(ov)
    else:
        view = pc.checker(ov.size, ov)
    return jsonify(view=_b64(view, "JPEG", 1400), overlay=_b64(ov), size=list(ov.size), ms=int(dt * 1000))


@app.get("/api/device")
def device():
    return jsonify(pc.hardware_info())


@app.post("/api/device")
def device_set():
    try:
        with work_lock:
            pc.set_device((request.json or {}).get("device"))
            info = pc.hardware_info()
    except ValueError as e:
        return jsonify(error=str(e)), 400
    return jsonify(info)


@app.post("/api/device/test")
def device_test():
    want = (request.json or {}).get("device", "auto")
    if want not in pc.DEVICES:
        return jsonify(error="Thiết bị không hợp lệ"), 400
    with work_lock:
        return jsonify(pc.benchmark(want))


@app.post("/api/style/save")
def style_save():
    body = request.json or {}
    name = "".join(c for c in body.get("name", "").strip() if c.isalnum() or c in "-_ ").strip()
    if not name:
        return jsonify(error="Thiếu tên style"), 400
    os.makedirs(STYLE_DIR, exist_ok=True)
    with open(os.path.join(STYLE_DIR, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(pc.Style.from_dict(body.get("style")).to_dict(), f, ensure_ascii=False, indent=2)
    return jsonify(ok=True, name=name)


def _scan(folder, cap=None):
    out = []
    for dp, _, fs in os.walk(folder):
        for f in sorted(fs):
            if f.lower().endswith(IMG_EXT):
                out.append(os.path.join(dp, f))
                if cap and len(out) >= cap:
                    return sorted(out)
    return sorted(out)


def _json_items(url, field):
    if url.startswith("http"):
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            data = json.loads(r.read().decode("utf-8"))
    else:
        data = json.load(open(url, encoding="utf-8"))
    items = []

    def walk(g):
        for p in g.get("content") or []:
            items.append(p)
        for s in g.get("subCates") or []:
            walk(s)

    for key in ("poses", "photobooth"):
        for g in data.get(key) or []:
            walk(g)
    seen = set()
    out = []
    for p in items:
        u = p.get(field)
        if not u or u in seen:
            continue
        seen.add(u)
        stem = p.get("id") if field == "previewUrl" else os.path.splitext(u.rsplit("/", 1)[-1])[0]
        out.append((u, stem))
    return out


class Batch:
    def __init__(self):
        self.state = {"running": False, "stopped": False, "done": 0, "total": 0, "ok": 0, "skip": 0, "errors": [], "current": "", "last": None, "out": "", "started": 0, "finished": 0}
        self.error_items = []
        self.results = []
        self.cfg = {}
        self.stop = threading.Event()
        self.thread = None
        self.start_lock = threading.Lock()

    def start(self, cfg):
        with self.start_lock:
            if self.state["running"]:
                return "Đang có một lượt chạy hàng loạt khác"
            try:
                return self._start(cfg)
            except Exception as e:
                traceback.print_exc()
                return f"Không bắt đầu được: {e}"

    def _start(self, cfg):
        src = cfg.get("input", "").strip().strip('"')
        out = cfg.get("output", "").strip().strip('"')
        if not src or not out:
            return "Thiếu thư mục vào / ra"
        st = pc.Style.from_dict(cfg.get("style"))
        jobs = []
        if src.lower().endswith(".json"):
            field = "poseUrl" if st.source == "lineart" else "previewUrl"
            jobs = [(u, s + ".png") for u, s in _json_items(src, field)]
        elif os.path.isdir(src):
            for f in _scan(src):
                rel = os.path.relpath(f, src)
                stem = os.path.splitext(rel)[0]
                suf = cfg.get("strip_suffix", "")
                if suf and stem.endswith(suf):
                    stem = stem[: -len(suf)]
                jobs.append((f, stem + ".png"))
        else:
            return "Đầu vào phải là thư mục ảnh hoặc file/URL .json"
        flt = cfg.get("filter", "").strip()
        if flt:
            jobs = [j for j in jobs if flt in os.path.basename(j[0])]
        lim = int(cfg.get("limit") or 0)
        if lim > 0:
            jobs = jobs[:lim]
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "_style.json"), "w", encoding="utf-8") as f:
            json.dump(st.to_dict(), f, ensure_ascii=False, indent=2)
        self.stop.clear()
        self.error_items = []
        self.results = []
        self.cfg = {k: v for k, v in cfg.items() if k != "style"} | {"style": st.to_dict(), "jobs": len(jobs)}
        self.state = {"running": True, "stopped": False, "done": 0, "total": len(jobs), "ok": 0, "skip": 0, "errors": [], "current": "", "last": None, "out": out, "started": time.time(), "finished": 0}
        self.thread = threading.Thread(target=self._run, args=(jobs, out, st, cfg), daemon=True)
        self.thread.start()
        return None

    def _run(self, jobs, out, st, cfg):
        try:
            self._loop(jobs, out, st, cfg)
        finally:
            self.state["stopped"] = self.stop.is_set() and self.state["done"] < self.state["total"]
            self.state["running"] = False
            self.state["finished"] = time.time()

    def _loop(self, jobs, out, st, cfg):
        skip = bool(cfg.get("skip_existing", True))
        max_h = int(cfg.get("max_height") or 0)
        for src, rel in jobs:
            if self.stop.is_set():
                break
            dst = os.path.join(out, rel)
            self.state["current"] = rel
            t0 = time.time()
            status, err = "ok", ""
            try:
                if skip and os.path.exists(dst):
                    self.state["skip"] += 1
                    status = "skip"
                else:
                    im = _load(src)
                    if max_h and im.height > max_h:
                        im = im.resize((int(im.width * max_h / im.height), max_h), Image.LANCZOS)
                    with work_lock:
                        ov = pc.render(im, st)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    ov.save(dst, optimize=True)
                    self.state["ok"] += 1
                    if self.state["ok"] % 3 == 1:
                        self.state["last"] = _b64(pc.checker(ov.size, ov), "JPEG", 420)
            except Exception as e:
                status, err = "err", str(e)
                self.state["errors"].append(f"{rel}: {e}")
                self.error_items.append({"file": rel, "src": src, "error": err, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
            self.results.append({"i": len(self.results), "file": rel.replace(os.sep, "/"), "src": src, "status": status, "error": err, "ms": int((time.time() - t0) * 1000)})
            self.state["done"] += 1


batch = Batch()


@app.post("/api/batch/start")
def batch_start():
    err = batch.start(request.json or {})
    if err:
        return jsonify(error=err), 400
    return jsonify(ok=True, total=batch.state["total"])


@app.get("/api/batch/status")
def batch_status():
    s = dict(batch.state)
    s["errors"] = s["errors"][-30:]
    s["error_count"] = len(batch.state["errors"])
    end = s["finished"] or time.time()
    s["elapsed"] = round(end - s["started"], 1) if s["started"] else 0
    return jsonify(s)


@app.get("/api/batch/log")
def batch_log():
    s = {k: v for k, v in batch.state.items() if k not in ("last", "errors")}
    return jsonify(state=s, config=batch.cfg, errors=batch.error_items, device=pc.device_info(), time=time.strftime("%Y-%m-%d %H:%M:%S"))


@app.get("/api/batch/results")
def batch_results():
    since = max(0, request.args.get("since", 0, type=int))
    return jsonify(items=batch.results[since:since + 1000], total=len(batch.results), out=batch.state["out"], started=batch.state["started"])


@app.get("/api/batch/file")
def batch_file():
    out = batch.state["out"]
    rel = request.args.get("f", "")
    if not out or not rel:
        return jsonify(error="Không tìm thấy file"), 404
    root = os.path.realpath(out)
    path = os.path.realpath(os.path.join(root, rel))
    # Only serve files inside the current batch output folder (commonpath raises across drives).
    try:
        inside = os.path.commonpath([path, root]) == root
    except ValueError:
        inside = False
    if not inside or not os.path.isfile(path):
        return jsonify(error="Không tìm thấy file"), 404
    return send_from_directory(os.path.dirname(path), os.path.basename(path), max_age=0)


@app.post("/api/batch/stop")
def batch_stop():
    batch.stop.set()
    return jsonify(ok=True)


@app.get("/api/batch/src")
def batch_src():
    i = request.args.get("i", -1, type=int)
    results = batch.results
    if not 0 <= i < len(results):
        return jsonify(error="Không tìm thấy ảnh gốc"), 404
    src = results[i]["src"]
    if src.startswith("http://") or src.startswith("https://"):
        src = _fetch(src)
    if not src.lower().endswith(IMG_EXT) or not os.path.isfile(src):
        return jsonify(error="Không tìm thấy ảnh gốc"), 404
    return send_from_directory(os.path.dirname(os.path.abspath(src)), os.path.basename(src), max_age=0)


def _stamp():
    return time.strftime("%Y%m%d-%H%M%S")


def _folder_info(path):
    files = _scan(path, SCAN_CAP)
    name = os.path.basename(os.path.normpath(path)) or "anh"
    return {"input": path, "name": name, "count": len(files), "capped": len(files) >= SCAN_CAP, "sample": [os.path.relpath(f, path).replace(os.sep, "/") for f in files[:6]]}


def _json_path():
    body = request.get_json(silent=True) or {}
    p = body.get("path", "")
    return p.strip().strip('"') if isinstance(p, str) else ""


@app.post("/api/folder/info")
def folder_info():
    p = _json_path()
    if not p or not os.path.isdir(p):
        return jsonify(error="Thư mục không tồn tại"), 404
    info = _folder_info(p)
    info["output"] = os.path.join(os.path.dirname(os.path.normpath(p)), info["name"] + "-line")
    return jsonify(info)


@app.post("/api/folder/pick")
def folder_pick():
    # The page cannot read real paths from the browser, so ask a native dialog in a child process (Tk needs its own main thread).
    code = (
        "import tkinter as tk\n"
        "from tkinter import filedialog\n"
        "r = tk.Tk(); r.withdraw(); r.attributes('-topmost', True); r.lift(); r.focus_force()\n"
        "print(filedialog.askdirectory(parent=r, title='Chọn thư mục ảnh đầu vào') or '', end='')"
    )
    if not pick_lock.acquire(blocking=False):
        return jsonify(error="Hộp chọn thư mục đang mở"), 409
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=600, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"}, creationflags=flags)
    except Exception as e:
        return jsonify(error=f"Không mở được hộp chọn thư mục: {e}"), 500
    finally:
        pick_lock.release()
    if out.returncode:
        return jsonify(error="Không mở được hộp chọn thư mục: " + (out.stderr.strip().splitlines() or ["lỗi không rõ"])[-1]), 500
    p = out.stdout.strip()
    if not p:
        return jsonify(cancelled=True)
    info = _folder_info(os.path.normpath(p))
    info["output"] = os.path.join(os.path.dirname(os.path.normpath(p)), info["name"] + "-line")
    return jsonify(info)


WIN_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(10)), *(f"lpt{i}" for i in range(10))}


def _safe_parts(rel):
    parts = []
    for x in rel.replace("\\", "/").split("/"):
        x = x.strip().rstrip(".")
        if not x or x == ".." or ":" in x or x.split(".")[0].lower() in WIN_RESERVED or any(c in x for c in '<>"|?*') or any(ord(c) < 32 for c in x):
            continue
        parts.append(x)
    return parts


def _inside(path, root):
    try:
        return os.path.commonpath([os.path.realpath(path), os.path.realpath(root)]) == os.path.realpath(root)
    except ValueError:
        return False


def _clean_inputs(keep):
    if not os.path.isdir(INPUT_DIR):
        return
    busy = batch.state["running"] and batch.cfg.get("input", "")
    for d in os.listdir(INPUT_DIR):
        full = os.path.join(INPUT_DIR, d)
        if d != keep and not (busy and _inside(busy, full)):
            shutil.rmtree(full, ignore_errors=True)


@app.post("/api/folder/upload")
def folder_upload():
    files = request.files.getlist("files")
    rels = request.form.getlist("paths")
    if not files or len(files) != len(rels):
        return jsonify(error="Không nhận được ảnh"), 400
    # Big folders arrive in several requests that share one session folder.
    sid = request.form.get("session", "")
    if not sid or not all(c.isalnum() or c == "-" for c in sid) or not os.path.isdir(os.path.join(INPUT_DIR, sid)):
        sid = _stamp() + "-" + uuid.uuid4().hex[:6]
        _clean_inputs(sid)
    root = os.path.join(INPUT_DIR, sid)
    saved = 0
    for f, rel in zip(files, rels):
        parts = _safe_parts(rel)
        if not parts or not parts[-1].lower().endswith(IMG_EXT):
            continue
        dst = os.path.join(root, *parts)
        if not _inside(dst, root):
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        f.save(dst)
        saved += 1
    if not saved and not os.path.isdir(root):
        return jsonify(error="Thư mục không có ảnh (.png .jpg .jpeg .webp)"), 400
    os.makedirs(root, exist_ok=True)
    tops = os.listdir(root)
    base = os.path.join(root, tops[0]) if len(tops) == 1 and os.path.isdir(os.path.join(root, tops[0])) else root
    info = _folder_info(base)
    if base == root:
        info["name"] = "anh-tha"
    if not info["count"]:
        return jsonify(error="Thư mục không có ảnh (.png .jpg .jpeg .webp)"), 400
    info["output"] = os.path.join(OUTPUT_DIR, info["name"] + "-" + sid.split("-", 2)[0] + "-" + sid.split("-", 2)[1])
    info["uploaded"] = True
    info["session"] = sid
    return jsonify(info)


@app.post("/api/open")
def open_folder():
    p = (request.json or {}).get("path", "").strip().strip('"')
    if not os.path.isdir(p):
        return jsonify(error="Thư mục không tồn tại"), 404
    if os.name == "nt":
        os.startfile(p)
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", p])
    return jsonify(ok=True)


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    port = int(os.environ.get("POSE_TOOL_PORT", "7860"))
    url = f"http://127.0.0.1:{port}"
    print(f"Pose Line Tool: {url}  |  thiết bị: {pc.device_info()}")
    if os.environ.get("POSE_TOOL_NO_BROWSER") != "1":
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
