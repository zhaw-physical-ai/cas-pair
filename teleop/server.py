"""Phone teleoperation of a simulated SO-101 arm, with demonstration recording.

The laptop page (/) runs the MuJoCo sim and shows a QR code; the phone page (/phone?room=CODE)
is the controller. The server only relays messages between them (WebSocket) and stores the
episodes the laptop uploads.

    TOKEN=<word> DATA_DIR=~/teleop-data uv run uvicorn server:app --port 8000
"""
import io
import json
import os
import re
import time
import zipfile
from pathlib import Path

import segno
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"
MODEL = HERE.parent / "gestures" / "sim" / "model"     # the same SO-101 scene as the gestures sim
TOKEN = os.environ.get("TOKEN", "")
if not TOKEN:
    raise SystemExit("set TOKEN to a word of your choice (needed to download the data)")
EPISODES = Path(os.environ.get("DATA_DIR", "~/teleop-data")).expanduser() / "episodes"
EPISODES.mkdir(parents=True, exist_ok=True)

app = FastAPI()
app.mount("/static", StaticFiles(directory=STATIC), name="static")
app.mount("/model", StaticFiles(directory=MODEL), name="model")
NO_CACHE = {"Cache-Control": "no-cache"}


def slug(s: str, n: int = 32) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", s.lower()).strip("-")[:n] or "anon"


@app.get("/")
def view_page():
    return FileResponse(STATIC / "view.html", headers=NO_CACHE)


@app.get("/phone")
def phone_page():
    return FileResponse(STATIC / "phone.html", headers=NO_CACHE)


@app.get("/qr.svg")
def qr(data: str):
    buf = io.BytesIO()
    segno.make(data, error="m").save(buf, kind="svg", scale=8, border=2)
    return Response(buf.getvalue(), media_type="image/svg+xml")


@app.get("/healthz")
def healthz():
    return {"ok": True, "episodes": len(list(EPISODES.glob("*.json")))}


# ---------- relay: phone <-> laptop, per room ----------
# One phone per room steers (the "controller"); the server drops commands from the others.
# Any phone can send {"type": "takeover"} to become the controller.
rooms: dict[str, dict] = {}


async def send_all(sockets, msg: str):
    for ws in list(sockets):
        try:
            await ws.send_text(msg)
        except Exception:
            pass


async def presence(room: dict):
    ctrl = room["ctrl"]
    info = {"type": "presence", "phones": len(room["phone"]), "views": len(room["view"]),
            "controller": room["names"].get(ctrl) if ctrl else None}
    await send_all(room["view"], json.dumps(info))
    for ws in list(room["phone"]):
        await send_all([ws], json.dumps({**info, "you_steer": ws is ctrl}))


@app.websocket("/ws/{code}/{role}")
async def relay(ws: WebSocket, code: str, role: str):
    if role not in ("phone", "view"):
        await ws.close(code=1008)
        return
    await ws.accept()
    room = rooms.setdefault(slug(code), {"phone": set(), "view": set(), "ctrl": None, "names": {}})
    room[role].add(ws)
    if role == "phone" and room["ctrl"] is None:
        room["ctrl"] = ws                      # the first phone in an empty room steers
    await presence(room)
    try:
        while True:
            msg = await ws.receive_text()
            if role == "view":
                await send_all(room["phone"], msg)
                continue
            kind = json.loads(msg).get("type")
            if kind == "hello":
                room["names"][ws] = str(json.loads(msg).get("name", ""))[:30] or "someone"
                await presence(room)
            elif kind == "takeover":
                room["ctrl"] = ws
                await send_all(room["view"], json.dumps({"type": "cmd", "vp": 0, "vr": 0, "vz": 0}))
                await presence(room)
            elif ws is room["ctrl"]:
                await send_all(room["view"], msg)
    except WebSocketDisconnect:
        pass
    finally:
        room[role].discard(ws)
        room["names"].pop(ws, None)
        if room["ctrl"] is ws:
            room["ctrl"] = None
        await presence(room)


# ---------- episodes ----------
@app.post("/api/episodes")
async def save_episode(request: Request):
    ep = await request.json()
    if not isinstance(ep.get("frames"), dict) or not ep["frames"].get("t"):
        raise HTTPException(400, "empty episode")
    ep["server_time"] = time.time()
    name = f"{time.strftime('%Y%m%d-%H%M%S')}_{slug(ep.get('room', ''))}_{slug(ep.get('name', ''))}.json"
    (EPISODES / name).write_text(json.dumps(ep))
    return {"saved": name, "episodes": len(list(EPISODES.glob("*.json")))}


@app.get("/api/episodes")
def list_episodes():
    out = []
    for p in sorted(EPISODES.glob("*.json")):
        ep = json.loads(p.read_text())
        out.append({"file": p.name, "name": ep.get("name"), "room": ep.get("room"),
                    "seconds": round(ep["frames"]["t"][-1], 1), "success": ep.get("success")})
    return out


@app.get("/api/export")
def export(t: str = ""):
    if t != TOKEN:
        raise HTTPException(403, "wrong token")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(EPISODES.glob("*.json")):
            zf.write(p, p.name)
    buf.seek(0)
    return StreamingResponse(buf, media_type="application/zip",
                             headers={"Content-Disposition": "attachment; filename=so101-episodes.zip"})
