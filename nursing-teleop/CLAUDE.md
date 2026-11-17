# SO-101 phone teleop: notes for coding agents and maintainers

Teleoperate a **simulated** SO-101 arm with a phone and record demonstrations. Built for a
lecture with nursing students: the participants do not code, install or clone anything. They only
open links and scan QR codes. Keep it that way: every change must still work for a non-technical
user with two phones and no laptop.

- How to run it and what the data contains: [`README.md`](README.md)
- Step-by-step class workflow for teachers and students: [`GUIDE.md`](GUIDE.md)

## Architecture

```
steering phone                    teacher's laptop                    screen phone (or laptop)
/phone?room=CODE   ──WebSocket──►  server.py (FastAPI)   ──WebSocket──►  /?room=CODE
tilt / sliders, gripper,           relays messages per room,           MuJoCo (WASM) + three.js,
record buttons                     one controller per room,            inverse kinematics,
                                   stores episodes as JSON  ◄── POST ── records 30 Hz, uploads
```

- **The simulation runs in the browser of the screen device, not on the server.** The server
  only serves files, relays small JSON messages and stores episodes. One arm is a tiny
  simulation (a fraction of one CPU core, even on a phone). A central simulator streaming video
  to every group was considered and rejected: more latency (teleop needs < ~100 ms; the relay
  through a Cloudflare tunnel measured 39 ms median, 116 ms max), video bandwidth on classroom
  WiFi, and one machine as a single point of failure. A big GPU (5090) is for training a policy
  on the recorded episodes, not for running this sim.
- **Rooms** isolate groups. The screen page makes a random 4-letter room code if the URL has none
  and puts it in the URL (`history.replaceState`), so a reload keeps the room.
- **Phones need an HTTPS page** for motion sensors (and WebSocket must then be `wss://`). The
  teacher puts a Cloudflare quick tunnel in front of the server; the QR code is built from
  `location.origin`, so the screen page must be opened through the https address, not localhost
  (the page warns about that).

## Files

| file | what |
|---|---|
| `server.py` | FastAPI app: pages, `/model` (static, from `../gestures/sim/model`), `/qr.svg`, WebSocket relay `/ws/{room}/{role}`, episode upload / list / export |
| `static/view.html`, `static/view.js` | screen page: MuJoCo + three.js scene, IK, control loop, recording, QR code panel |
| `static/phone.html` | steering page: name screen, tilt and slider modes, height buttons, gripper, record buttons, "is steering / Take over" overlay. Plain inline JS, no build step |
| `serve.sh` | starts the server on `127.0.0.1:8001` (needs `TOKEN`; `DATA_DIR` defaults to `~/teleop-data`) |
| `pyproject.toml`, `uv.lock` | `fastapi`, `uvicorn[standard]` (WebSocket support), `segno` (QR codes) |

The SO-101 model and scene (table, red cube, green target) are **reused from
`../gestures/sim/model`** and served at `/model`. That folder belongs to the gestures lab (another
author): do not modify it from here. If this folder must stand alone, copy the model in.

CDN dependencies of the screen page (pinned in the import map of `view.html`):
`three@0.178.0` and `@mujoco/mujoco@3.17.0` from jsDelivr. The screen device needs internet.

## Message protocol (JSON over `/ws/{room}/{role}`, role = `phone` or `view`)

Phone → server:
- `{"type": "hello", "name"}`: sent on connect; the name is shown as "*name* is steering".
- `{"type": "takeover"}`: become the controller of the room. The server first sends a zero
  command to the views so the arm stops.

Phone → server → views (forwarded **only from the controller phone**, dropped from others):
- `{"type": "cmd", "vp", "vr", "vz"}`: speeds in -1..1 for turn, reach, height. Sent 20 times a
  second while something is pressed, plus one zero command on release.
- `{"type": "gripper", "open": bool}`
- `{"type": "record", "action": "start" | "save" | "discard", "name"?}`
- `{"type": "reset"}` (handled by the view; no button sends it at the moment)

Server → everyone in the room, on every connect / disconnect / hello / takeover:
- `{"type": "presence", "phones", "views", "controller": name | null}`, and for phones also
  `"you_steer": bool`.

View → server → all phones in the room, 4 times a second:
- `{"type": "status", "recording", "seconds", "open", "episodes", "message", "success"}`

Controller rules (in `server.py`): the first phone in a room with no controller becomes the
controller; `takeover` moves control; if the controller disconnects, nobody steers until a phone
taps "Start steering". The relay itself is stateless otherwise; rooms live in memory only.

## Control (in `view.js`)

- State: a target for the gripper in cylindrical coordinates, `pan` (rad, = the shoulder_pan
  joint), `r` (reach, m) and `z` (height, m), plus `open`. Home: pan 0, r 0.22, z 0.14.
- Every frame: `target += cmd * MAX * dt`, with `MAX = {pan: 0.9 rad/s, r: 0.10 m/s, z: 0.10 m/s}`.
  If no command arrived for `CMD_TIMEOUT = 0.3 s`, nothing moves (safety when a phone drops).
- Inverse kinematics: damped least squares on (r, z) of the `gripperframe` site in the arm plane,
  unknowns shoulder_lift and elbow_flex, Jacobian by finite differences with `mj_kinematics` on a
  separate `MjData` (`ikd`), warm-started from the last solution. `wrist_flex = PITCH - lift -
  elbow` (PITCH 1.7) points the gripper down as far as the wrist range allows (it is mostly at its
  limit). `wrist_roll` stays 0.
- A move is accepted only if the IK error is < 3 mm, and the target is clamped to
  `BOX = {r: 0.14-0.34 m, z: 0.01-0.28 m}`. This box was checked offline: the IK reaches it
  everywhere (reach map with the node build of `@mujoco/mujoco`).
- Joint targets go to the position actuators through a slew limit of 3 rad/s (smooth motion).
- Direction convention: the camera looks from behind the arm, so screen left = arm left; positive
  `vp` (tilt right / slider right) increases shoulder_pan, which turns the arm to the right.

Phone side (`phone.html`):
- **Tilt**: hold the big field; the orientation at the moment of pressing is the zero. gamma
  (left/right tilt) → `vp`, minus beta (top edge away) → `vr`. Dead zone 5°, full speed at 30°.
  iOS needs `DeviceOrientationEvent.requestPermission()` after a tap (done on Start and when
  choosing Tilt); if denied, the page starts in Sliders mode.
- **Sliders**: two thick bars, one per axis, so turn and reach never mix (a single 2D joystick
  was tried first and was hard to move in a straight line). Only the finger's position along the
  bar counts; the knob springs back to 0 on release. Dead zone 12 % around the middle. Both bars
  can be used at once (one pointer each, `setPointerCapture`).
- **▲ / ▼** set `vz` while held. The gripper button toggles `open`.

## Recording and data

- **Start** resets the arm to home and moves the cube by up to ±2 cm in x and y (some variety for
  learning). Samples are taken at 30 Hz on average, independent of the screen's frame rate
  (`lastSample` advances by 1/30 s). Episodes shorter than 1 s are not saved.
- **Save** POSTs the episode to `/api/episodes`; the server writes
  `DATA_DIR/episodes/<time>_<room>_<name>.json`. Export: `/api/export?t=<TOKEN>` (zip).
- Per frame: `t`, `state` (6 joint positions, rad, in `ARM` order: shoulder_pan, shoulder_lift,
  elbow_flex, wrist_flex, wrist_roll, gripper), `action` (the 6 joint targets), `command` (phone
  speeds), `gripper_target` (pan, r, z, open), `cube` (x y z, quaternion w x y z). Per episode:
  `room`, `name`, `started`, `fps`, `task`, `success` (cube on the green square when saved),
  `joint_names`, `units`.
- Joint names match the real SO-101, but the units are radians from the simulation, not LeRobot's
  normalized motor values, and there are **no camera images**. Converting to a LeRobot dataset, or
  adding rendered camera frames, would be the next step for training an image-based policy.

## Things that break easily

- A **hidden tab pauses the simulation** (browsers stop `requestAnimationFrame`). The screen page
  must stay in front. It requests a screen wake lock (`navigator.wakeLock`, iOS 16.4+; Safari may
  need one tap first) so a phone used as the screen does not lock.
- The quick tunnel's address **changes on every restart**, and all QR codes with it.
- `[hidden]` is forced with `display: none !important` in both pages, because some elements have
  their own `display: flex`. Keep that rule when restyling.
- The server binds to `127.0.0.1` on purpose (the tunnel connects locally). Port 8001 so it can run
  next to the gestures collector (8000).
- Names are free text from participants: they are stored in the episode files and shown on the
  screen. Do not add anything that sends them elsewhere.

## Checking a change

There are no automated tests. What was used:
1. Start a server: `TOKEN=test DATA_DIR=/tmp/teleop-test uv run uvicorn server:app --port 8001`.
2. Open `http://127.0.0.1:8001/?room=TEST` (screen) and `http://127.0.0.1:8001/phone?room=TEST`
   (phone, at a mobile viewport) in two browser tabs. Drive it with pointer events; synthetic
   events need `Element.prototype.setPointerCapture` stubbed out.
3. Controller lock: connect a view and two phones with Python `websockets`, check that only the
   controller's commands reach the view, before and after `takeover`, and after it disconnects.
4. Record a short episode, then check the JSON: ~30 Hz from `t`, `state` close to `action`.
5. Through a real tunnel and **on real phones** (iPhone and Android): tilt mode, screen wake lock,
   frame rate on the screen phone. These cannot be checked in a desktop browser.
