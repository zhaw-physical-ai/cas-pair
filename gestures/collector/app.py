"""Gesture collector: phones post ~2.5 s IMU takes, one JSON file per take.

Run:
    CLASS_TOKEN=xyz DATA_DIR=~/gestures-data uv run uvicorn app:app --port 8000
"""
import csv
import html
import io
import json
import os
import re
import time
import zipfile
from pathlib import Path

import segno
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response

GESTURES = ["left", "right", "up", "down", "circle", "idle"]
TARGET_REPS = 15
MAX_BODY = 2_000_000          # bytes per take
MIN_SAMPLES = 20

TOKEN = os.environ.get("CLASS_TOKEN", "")
if not TOKEN:
    raise SystemExit("set CLASS_TOKEN")
DATA_DIR = Path(os.environ.get("DATA_DIR", "~/gestures-data")).expanduser()
DATA_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "deleted").mkdir(exist_ok=True)
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")
STATIC = Path(__file__).parent / "static"

app = FastAPI(docs_url=None, redoc_url=None)


# ---------- helpers ----------
def check_token(t: str | None):
    if t != TOKEN:
        raise HTTPException(403, "wrong class token")


def clean_person(p: str | None) -> str:
    p = re.sub(r"\s+", " ", (p or "").strip())[:40]
    if not p:
        raise HTTPException(400, "name missing")
    return p


def slug(p: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", p.lower()).strip("-") or "x"


def check_gesture(g: str | None) -> str:
    if g not in GESTURES:
        raise HTTPException(400, f"gesture must be one of {GESTURES}")
    return g


def save(rec: dict) -> str:
    ts = time.strftime("%Y%m%d-%H%M%S") + f"-{time.time_ns() % 1_000_000:06d}"
    name = f"{ts}_{slug(rec['person'])}_{rec['gesture']}.json"
    rec["id"] = name[:-5]
    rec["server_time"] = time.time()
    tmp = DATA_DIR / (name + ".tmp")
    tmp.write_text(json.dumps(rec, separators=(",", ":")))
    tmp.rename(DATA_DIR / name)
    return rec["id"]


def takes():
    return sorted(DATA_DIR.glob("*.json"))


_index_cache: dict = {"key": None, "data": []}


def take_index() -> list:
    """[(path, person, gesture)] - reads only the small header of each file; cached."""
    files = takes()
    key = (len(files), files[-1].name if files else "")
    if _index_cache["key"] == key:
        return _index_cache["data"]
    out = []
    for p in files:
        try:
            with p.open() as f:
                head = f.read(400)
            person = json.loads(re.search(r'"person":("(?:[^"\\]|\\.)*")', head).group(1))
            gesture = re.search(r'"gesture":"(\w+)"', head).group(1)
        except Exception:
            continue
        out.append((p, person, gesture))
    _index_cache.update(key=key, data=out)
    return out


def counts() -> dict:
    """{person: {gesture: n}}"""
    out: dict = {}
    for _, person, gesture in take_index():
        out.setdefault(person, {g: 0 for g in GESTURES})[gesture] += 1
    return out


HOLDOUT_FILE = DATA_DIR / "holdout.txt"


def holdout_people() -> set:
    """People whose takes are hidden from the export and used to score uploaded models.
    One name per line in DATA_DIR/holdout.txt, exactly as typed on the phone."""
    if not HOLDOUT_FILE.exists():
        return set()
    return {ln.strip() for ln in HOLDOUT_FILE.read_text().splitlines()
            if ln.strip() and not ln.startswith("#")}


# ---------- phone page ----------
@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/pages", response_class=HTMLResponse)
def pages(request: Request, t: str = ""):
    """Overview of every page, for trying things out. Phone pages need HTTPS (motion sensors)."""
    q = f"?t={html.escape(t)}" if t else ""
    rows = [
        ("Phone", f"./{q}", "record gestures (needs HTTPS)"),
        ("Phone", f"live{q}", "run an uploaded model live, send gestures to the sim (needs HTTPS)"),
        ("Laptop", "sim/?channel=me", "SO-101 sim; ?channel= must match the live page; keys: arrows, c, r"),
        ("Laptop", f"upload{q}", "upload an ONNX model, see its hold-out score"),
        ("Projector", "dashboard", "takes per person and gesture, QR of the phone link"),
        ("Projector", "leaderboard", "best model per team on the hidden people"),
        ("Data", f"api/export{q}", "zip of all takes (without hold-out people)"),
    ]
    body = "".join(f"<tr><td>{w}</td><td><a href='{u}'>{html.escape(u.split('?')[0] or '/')}</a></td>"
                   f"<td>{d}</td></tr>" for w, u, d in rows)
    https = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
    note = "" if https else "<p><b>Plain HTTP:</b> phone motion sensors only work over HTTPS.</p>"
    return f"""<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:,"><title>Gestures: pages</title>
<style>body{{font-family:system-ui,sans-serif;margin:16px;max-width:760px}} td{{padding:6px 10px;border-bottom:1px solid #ddd}}
table{{border-collapse:collapse}} a{{font-weight:600}}</style>
<h2>Gestures lab: pages</h2>{note}<table>{body}</table>"""


@app.get("/healthz")
def healthz():
    return {"ok": True, "takes": len(takes())}


# ---------- web recording ----------
@app.post("/api/recording")
async def post_recording(request: Request):
    body = await request.body()
    if len(body) > MAX_BODY:
        raise HTTPException(413, "take too large")
    try:
        d = json.loads(body)
    except Exception:
        raise HTTPException(400, "not JSON")
    check_token(d.get("token"))
    person = clean_person(d.get("person"))
    gesture = check_gesture(d.get("gesture"))
    t = d.get("t") or []
    n = len(t)
    if n < MIN_SAMPLES:
        raise HTTPException(400, f"only {n} samples - no sensor data? Use the phyphox fallback.")
    for k in ("accG", "acc", "gyro"):
        v = d.get(k) or []
        if len(v) != n:
            raise HTTPException(400, f"{k} has {len(v)} samples, t has {n}")
    rec = {
        "person": person, "gesture": gesture, "source": "web",
        "ua": str(d.get("ua", ""))[:300], "ios": bool(d.get("ios")),
        "t": t, "accG": d["accG"], "acc": d["acc"], "gyro": d["gyro"],
    }
    rid = save(rec)
    return {"id": rid, "n": n, "counts": counts().get(person, {})}


# ---------- phyphox fallback ----------
def check_phyphox_csv(text: str) -> str:
    """Return 'acc' or 'gyro'; raise on anything else."""
    first = text.splitlines()[0] if text.strip() else ""
    if "Linear Acceleration" in first:
        raise HTTPException(400, "this is 'Acceleration (without g)'. Use 'Acceleration with g'.")
    if "Time" not in first:
        raise HTTPException(400, "not a phyphox CSV (no Time column). Export as CSV, not Excel.")
    kind = "gyro" if ("Gyroscope" in first or "rad/s" in first) else "acc" if "Acceleration" in first else None
    if kind is None:
        raise HTTPException(400, "use 'Acceleration with g' or 'Gyroscope'")
    try:
        dialect = csv.Sniffer().sniff(first, delimiters=",;\t")
        rows = list(csv.reader(io.StringIO(text), dialect))
    except Exception:
        raise HTTPException(400, "could not read CSV")
    if len(rows) < MIN_SAMPLES:
        raise HTTPException(400, f"only {len(rows) - 1} rows - record a bit longer")
    return kind


@app.post("/api/phyphox")
async def post_phyphox(token: str = Form(""), person: str = Form(""), gesture: str = Form(""),
                       file: UploadFile = File(...)):
    check_token(token)
    person = clean_person(person)
    gesture = check_gesture(gesture)
    raw = await file.read(MAX_BODY * 5 + 1)
    if len(raw) > MAX_BODY * 5:
        raise HTTPException(413, "file too large - record ~3 s only")
    if raw[:2] == b"PK":  # phyphox zip export
        try:
            z = zipfile.ZipFile(io.BytesIO(raw))
            names = [n for n in z.namelist() if n.lower().endswith(".csv") and "meta" not in n.lower()]
            raw = z.read(names[0])
        except Exception:
            raise HTTPException(400, "zip without a data CSV")
    text = raw.decode("utf-8-sig", errors="replace")
    kind = check_phyphox_csv(text)
    rid = save({"person": person, "gesture": gesture, "source": "phyphox", "kind": kind,
                "filename": file.filename, "csv": text})
    return {"id": rid, "kind": kind, "counts": counts().get(person, {})}


# ---------- delete / counts / export ----------
@app.delete("/api/recording/last")
def delete_last(person: str, t: str = ""):
    check_token(t)
    person = clean_person(person)
    for p in reversed(takes()):
        if f"_{slug(person)}_" in p.name:
            try:
                if json.loads(p.read_text()).get("person") != person:
                    continue
            except Exception:
                continue
            p.rename(DATA_DIR / "deleted" / p.name)
            return {"deleted": p.stem, "counts": counts().get(person, {})}
    raise HTTPException(404, "no take to delete")


@app.get("/api/counts")
def get_counts(person: str | None = None):
    c = counts()
    if person is not None:
        return c.get(person.strip(), {g: 0 for g in GESTURES})
    return c


_export_cache: dict = {"key": None, "data": b""}


@app.get("/api/export")
def export(t: str = ""):
    """All takes except the hold-out people's, without the browser user agent."""
    check_token(t)
    hold = holdout_people()
    files = [p for p, person, _ in take_index() if person not in hold]
    key = (len(files), files[-1].name if files else "", tuple(sorted(hold)))
    if _export_cache["key"] != key:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for p in files:
                d = json.loads(p.read_text())
                if d.get("source") == "web":
                    d["ios"] = gload._is_ios(d)     # decided from the UA, which is dropped next
                d.pop("ua", None)
                z.writestr(f"gestures/{p.name}", json.dumps(d, separators=(",", ":")))
        _export_cache.update(key=key, data=buf.getvalue())
    return Response(_export_cache["data"], media_type="application/zip",
                    headers={"Content-Disposition": "attachment; filename=gestures.zip"})


# ---------- projector dashboard ----------
def public_base(request: Request) -> str:
    if PUBLIC_URL:
        return PUBLIC_URL
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", "localhost"))
    return f"{proto}://{host}"


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    phone_url = f"{public_base(request)}/?t={TOKEN}"
    qr = segno.make(phone_url, error="m").svg_inline(scale=8, dark="#000", light="#fff")
    c = counts()
    hold = holdout_people()
    rows = []
    tot = {g: 0 for g in GESTURES}
    for person in sorted(c, key=lambda p: (p in hold, p.lower())):
        cells = []
        for g in GESTURES:
            n = c[person][g]
            tot[g] += n
            cls = "ok" if n >= TARGET_REPS else ("some" if n else "none")
            cells.append(f'<td class="{cls}">{n}</td>')
        tag = ' <small>(hold-out)</small>' if person in hold else ""
        rows.append(f"<tr><th>{html.escape(person)}{tag}</th>{''.join(cells)}<td>{sum(c[person].values())}</td></tr>")
    head = "".join(f"<th>{g}</th>" for g in GESTURES)
    totals = "".join(f"<td>{tot[g]}</td>" for g in GESTURES)
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="refresh" content="5"><title>Gestures dashboard</title>
<style>
body{{font-family:system-ui,sans-serif;margin:24px;background:#fff;color:#111}}
.wrap{{display:flex;gap:40px;align-items:flex-start;flex-wrap:wrap}}
table{{border-collapse:collapse;font-size:20px}} td,th{{padding:6px 14px;border:1px solid #ccc;text-align:center}}
th:first-child{{text-align:left}} .ok{{background:#b7e4b0}} .some{{background:#ffd8a8}} .none{{color:#bbb}}
tfoot td{{font-weight:bold}} .url{{font-size:22px;word-break:break-all;max-width:420px}}
</style></head><body>
<div class="wrap">
<div><div>{qr}</div><p class="url">{html.escape(phone_url)}</p></div>
<div><h2>Takes per person (target {TARGET_REPS} per gesture) - {len(c)} people, {sum(tot.values())} takes</h2>
<table><thead><tr><th>person</th>{head}<th>all</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
<tfoot><tr><td>total</td>{totals}<td>{sum(tot.values())}</td></tr></tfoot></table></div>
</div></body></html>"""


# ---------- models: ONNX upload, hold-out scoring, leaderboard ----------
import asyncio  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402

from fastapi.staticfiles import StaticFiles  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import load as gload  # noqa: E402  (the student load.py: same preprocessing for scoring)

MODELS = DATA_DIR / "models"
MODELS.mkdir(exist_ok=True)
MAX_MODEL = 20_000_000


def holdout_npz() -> Path | None:
    """Hold-out takes preprocessed exactly like load.py; rebuilt when they change."""
    hold = holdout_people()
    files = [p for p, person, _ in take_index() if person in hold]
    if not files:
        return None
    key = f"{len(files)}-{files[-1].name}-{'|'.join(sorted(hold))}"
    path = MODELS / "holdout.npz"
    keyfile = MODELS / "holdout.key"
    if not path.exists() or not keyfile.exists() or keyfile.read_text() != key:
        X, y, _ = gload.load(files, verbose=False)
        np = gload.np
        np.savez(path, X=X, y=np.array([GESTURES.index(g) for g in y]))
        keyfile.write_text(key)
    return path


def check_npz() -> Path | None:
    """A few class takes, only to check that an uploaded model runs (no score: they may be training data)."""
    files = [p for p, _, _ in take_index()][:12]
    if not files:
        return None
    path = MODELS / "check.npz"
    if not path.exists():
        X, y, _ = gload.load(files, verbose=False)
        gload.np.savez(path, X=X, y=gload.np.array([GESTURES.index(g) for g in y]))
    return path


def score_model(mid: str) -> dict:
    """Score on the hold-out people if there are any; otherwise only check that the model runs."""
    meta_path = MODELS / f"{mid}.json"
    meta = json.loads(meta_path.read_text())
    hp = holdout_npz()
    check_only = hp is None
    if check_only:
        hp = check_npz()
    if hp is None:
        meta["score"] = {"error": "no takes on the server yet to check the model with"}
    else:
        try:
            r = subprocess.run([sys.executable, str(Path(__file__).parent / "score.py"),
                                str(MODELS / f"{mid}.onnx"), str(hp)],
                               capture_output=True, text=True, timeout=120)
            meta["score"] = json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() \
                else {"error": (r.stderr or "scoring failed")[-300:]}
        except subprocess.TimeoutExpired:
            meta["score"] = {"error": "scoring took > 120 s"}
        if check_only and "error" not in meta["score"]:
            meta["score"] = {"check": "ok", "ms": meta["score"]["ms"]}
    meta["scored_at"] = time.time()
    meta_path.write_text(json.dumps(meta))
    return meta


def all_models() -> list:
    out = []
    for p in sorted(MODELS.glob("*.json")):
        try:
            out.append(json.loads(p.read_text()))
        except Exception:
            pass
    return out


@app.post("/api/models")
async def upload_model(token: str = Form(""), team: str = Form(""), name: str = Form(""),
                       notes: str = Form(""), file: UploadFile = File(...)):
    check_token(token)
    team = clean_person(team)
    raw = await file.read(MAX_MODEL + 1)
    if len(raw) > MAX_MODEL:
        raise HTTPException(413, "model larger than 20 MB")
    ts = time.strftime("%Y%m%d-%H%M%S")
    mid = f"{ts}_{slug(team)}_{time.time_ns() % 1000000:06d}"
    (MODELS / f"{mid}.onnx").write_bytes(raw)
    (MODELS / f"{mid}.json").write_text(json.dumps({
        "id": mid, "team": team, "name": (name or file.filename or "model")[:60],
        "notes": notes[:200], "size_kb": round(len(raw) / 1024, 1), "uploaded": time.time()}))
    meta = await asyncio.to_thread(score_model, mid)
    return meta


@app.get("/upload")
def upload_page():
    return FileResponse(STATIC / "upload.html", headers={"Cache-Control": "no-cache"})


@app.get("/api/models")
def list_models(t: str = ""):
    check_token(t)
    return all_models()


@app.get("/api/models/{mid}.onnx")
def get_model(mid: str, t: str = ""):
    check_token(t)
    if not re.fullmatch(r"[\w-]+", mid) or not (MODELS / f"{mid}.onnx").exists():
        raise HTTPException(404, "no such model")
    return FileResponse(MODELS / f"{mid}.onnx", media_type="application/octet-stream")


@app.post("/api/models/rescore")
def rescore(t: str = ""):
    """Instructor: re-score every model, e.g. after changing holdout.txt."""
    check_token(t)
    return [score_model(m["id"]) for m in all_models()]


@app.get("/leaderboard", response_class=HTMLResponse)
def leaderboard():
    models = all_models()
    best: dict = {}
    for m in models:
        acc = (m.get("score") or {}).get("acc")
        if acc is not None and (m["team"] not in best or acc > best[m["team"]]["score"]["acc"]):
            best[m["team"]] = m
    ranked = sorted(best.values(), key=lambda m: -m["score"]["acc"])
    rows = []
    for i, m in enumerate(ranked, 1):
        s = m["score"]
        pc = " ".join(f"{g[:2]}&nbsp;{s['per_class'][g]:.2f}" if s["per_class"].get(g) is not None
                      else f"{g[:2]}&nbsp;-" for g in GESTURES)
        n_up = sum(1 for x in models if x["team"] == m["team"])
        rows.append(f"<tr><td>{i}</td><th>{html.escape(m['team'])}</th><td>{html.escape(m['name'])}</td>"
                    f"<td class=acc>{s['acc']:.3f}</td><td class=pc>{pc}</td><td>{s['ms']:.2f}</td>"
                    f"<td>{m['size_kb']:.0f}</td><td>{n_up}</td></tr>")
    errors = [m for m in models[-8:] if "error" in (m.get("score") or {})]
    err_html = "".join(f"<li>{html.escape(m['team'])} / {html.escape(m['name'])}: "
                       f"{html.escape(m['score']['error'])}</li>" for m in errors)
    n_hold = len(holdout_people())
    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta http-equiv="refresh" content="10"><title>Gestures leaderboard</title>
<style>
body{{font-family:system-ui,sans-serif;margin:24px;background:#fff;color:#111}}
table{{border-collapse:collapse;font-size:20px}} td,th{{padding:6px 14px;border:1px solid #ccc;text-align:left}}
.acc{{font-weight:bold;font-size:24px}} .pc{{font-size:14px;color:#555}} .err{{color:#c62828;font-size:14px}}
</style></head><body>
<h2>Leaderboard: accuracy on {n_hold} hidden people (best model per team)</h2>
<table><thead><tr><th>#</th><th>team</th><th>model</th><th>accuracy</th><th>per gesture</th>
<th>ms/take</th><th>kB</th><th>uploads</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
{f'<h3>Recent failed uploads</h3><ul class=err>{err_html}</ul>' if err_html else ''}
</body></html>"""


# ---------- live: phone runs the model, predictions relayed to the sim (long-polling) ----------
# Long-polling rather than SSE: Cloudflare tunnels (and other proxies) buffer event streams.
_live: dict = {}   # channel -> {"seq": int, "events": deque, "cond": Condition, "polled": time}


def live_channel(name: str) -> dict:
    from collections import deque
    return _live.setdefault(slug(name), {"seq": 0, "events": deque(maxlen=50),
                                         "cond": asyncio.Condition(), "polled": 0.0})


@app.get("/live")
def live_page():
    return FileResponse(STATIC / "live.html", headers={"Cache-Control": "no-cache"})


@app.post("/api/live/{channel}")
async def live_post(channel: str, request: Request):
    d = await request.json()
    check_token(d.get("token"))
    if d.get("label") not in GESTURES:
        raise HTTPException(400, "bad label")
    ch = live_channel(channel)
    async with ch["cond"]:
        ch["seq"] += 1
        ch["events"].append({"seq": ch["seq"], "label": d["label"], "p": float(d.get("p", 1.0)),
                             "t": time.time()})
        ch["cond"].notify_all()
    return {"listeners": int(time.time() - ch["polled"] < 30)}


@app.get("/api/live/{channel}/next")
async def live_next(channel: str, after: int = -1):
    """Events with seq > after; waits up to 20 s for one. after=-1: start from now."""
    ch = live_channel(channel)
    ch["polled"] = time.time()
    if after < 0:
        return {"seq": ch["seq"], "events": []}
    if after > ch["seq"]:      # the server restarted: the counter began again
        after = 0

    def new():
        return [e for e in ch["events"] if e["seq"] > after]
    async with ch["cond"]:
        try:
            await asyncio.wait_for(ch["cond"].wait_for(lambda: bool(new())), timeout=20)
        except asyncio.TimeoutError:
            pass
        ch["polled"] = time.time()
        return {"seq": ch["seq"], "events": new()}


SIM_DIR = Path(__file__).resolve().parent.parent / "sim"
if SIM_DIR.is_dir():
    app.mount("/sim", StaticFiles(directory=SIM_DIR, html=True), name="sim")
