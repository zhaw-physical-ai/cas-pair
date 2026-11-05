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


_counts_cache: dict = {"key": None, "data": {}}


def counts() -> dict:
    """{person: {gesture: n}} - reads only the small header of each file; cached."""
    files = takes()
    key = (len(files), files[-1].name if files else "")
    if _counts_cache["key"] == key:
        return _counts_cache["data"]
    out: dict = {}
    for p in files:
        try:
            with p.open() as f:
                head = f.read(400)
            person = json.loads(re.search(r'"person":("(?:[^"\\]|\\.)*")', head).group(1))
            gesture = re.search(r'"gesture":"(\w+)"', head).group(1)
        except Exception:
            continue
        out.setdefault(person, {g: 0 for g in GESTURES})[gesture] += 1
    _counts_cache.update(key=key, data=out)
    return out


# ---------- phone page ----------
@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


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
    check_token(t)
    files = takes()
    key = (len(files), files[-1].stat().st_mtime_ns if files else 0, files[-1].name if files else "")
    if _export_cache["key"] != key:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for p in files:
                z.write(p, f"gestures/{p.name}")
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
    rows = []
    tot = {g: 0 for g in GESTURES}
    for person in sorted(c, key=str.lower):
        cells = []
        for g in GESTURES:
            n = c[person][g]
            tot[g] += n
            cls = "ok" if n >= TARGET_REPS else ("some" if n else "none")
            cells.append(f'<td class="{cls}">{n}</td>')
        rows.append(f"<tr><th>{html.escape(person)}</th>{''.join(cells)}<td>{sum(c[person].values())}</td></tr>")
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
