# SO-101 phone teleop

Use your phone as a remote control for a simulated SO-101 arm, and record demonstrations.
The arm runs in the browser on a laptop or projector (MuJoCo + three.js, the same SO-101 scene
as [`../gestures/sim`](../gestures/sim)). The phone is only the controller.

```
phone (/phone?room=CODE)  ──WebSocket──►  server  ──WebSocket──►  laptop (/?room=CODE)
 tilt or joystick, gripper,                relays,                MuJoCo SO-101, inverse kinematics,
 start / save recording                    stores episodes        records 30 Hz, uploads episodes
```

Step-by-step class workflow for teachers and students: [`GUIDE.md`](GUIDE.md). Design notes for
coding agents and maintainers: [`CLAUDE.md`](CLAUDE.md).

## Run it (instructor)
Needs [`uv`](https://docs.astral.sh/uv/) and `cloudflared` (`brew install cloudflared`).

```
cd teleop
TOKEN=<a word> ./serve.sh                          # terminal 1
cloudflared tunnel --url http://localhost:8001      # terminal 2: prints https://....trycloudflare.com
```

Open `https://....trycloudflare.com/` on the laptop or projector (not `localhost`: the QR code
must point to the https address). The page shows the arm, a room code and a QR code.

For a class without laptops, put a QR code of the start address on the projector:
`https://....trycloudflare.com/qr.svg?data=https://....trycloudflare.com/`.

## Use it (participants, in groups with two phones)
- **Screen phone:** scan the projector's QR code. It opens the arm with its own room code and a
  big QR code. Turn it sideways (landscape) and prop it up. The screen stays on while the page is
  open; do not switch apps, or the simulation pauses.
- **Steering phone:** scan the QR code on the screen phone, then:

1. Enter a first name or nickname, tap **Start**. On an iPhone, allow motion access.
2. Steer the arm:
   - **Tilt the phone**: hold the big field and tilt. Left / right turns the arm, forward / back
     moves the gripper out / in. Let go and the arm stops.
   - **Sliders**: two thick bars, one per direction. Slide along the horizontal bar to turn, along
     the vertical bar to reach out / pull in; let go and it springs back to stop. Moving off the bar
     sideways does nothing, so the two directions never mix. Works on every phone.
   - **▲ raise / ▼ lower**: hold to move the gripper up or down.
   - **Open / Close gripper**.
3. Task: move the red cube onto the green square.
4. **● Start recording** resets the arm and puts the cube in a slightly different place. Do the
   task, then **✓ Save** (or **✕ Discard** if it went wrong).

One phone steers at a time: the first phone in a room steers, any other phone in the same room
sees "*name* is steering" and a **Take over** button. Each screen has its own room, so several
screens can run at once.

## The data
Each saved episode is one JSON file in `~/teleop-data/episodes/`. Download them all as a zip:
`https://....trycloudflare.com/api/export?t=<the word>`. `/api/episodes` lists them.

Per frame, at 30 Hz:

| field | what |
|---|---|
| `t` | seconds since the start of the recording |
| `state` | the 6 joint positions (rad): shoulder_pan, shoulder_lift, elbow_flex, wrist_flex, wrist_roll, gripper |
| `action` | the 6 joint targets sent to the arm (rad), the same order |
| `command` | the phone's command: turn, reach, height speed, each -1..1 |
| `gripper_target` | where the gripper should be: pan (rad), reach (m), height (m), open (0/1) |
| `cube` | cube position (m) and orientation (quaternion w x y z) |

Plus per episode: `name`, `room`, `started`, `fps`, `task`, and `success` (cube on the square
when saved). `state` / `action` are the observation / action pairs a LeRobot-style policy learns
from; the joint names match the real SO-101. There are no camera images.

## How the control works
The phone sends speeds 20 times a second. The laptop moves a target point for the gripper
(turn angle, reach, height) and solves the inverse kinematics for shoulder_lift and elbow_flex
with MuJoCo's own kinematics; the wrist keeps the gripper pointing down as far as its range
allows. Targets outside the reachable zone (reach 14-34 cm, height 1-28 cm) are ignored. If no
message arrives for 0.3 s, the arm stops.
