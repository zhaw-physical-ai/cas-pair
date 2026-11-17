# SO-101 phone teleop: step by step for the class

The students steer a simulated SO-101 robot arm with their phones and record demonstrations: move
the red cube onto the green square. No laptop, no installation, no code: each group needs **two
phones**, one as the screen and one as the remote control.

## Teacher

### What you need
- Your laptop with this repository, [`uv`](https://docs.astral.sh/uv/) and `cloudflared`
  (`brew install cloudflared`), plugged in, with internet.
- A projector for the start QR code.

Your laptop is the meeting point for all groups: it sends them the web pages and the robot model,
passes the messages between each group's two phones and stores the recordings. The simulations
themselves run on the students' screen phones, so the load on your laptop stays small. But if
your laptop sleeps or goes offline, every group stops.

### The day before: test once
1. Do the steps of "Start of class" below.
2. Try a full round with two real phones, ideally one iPhone and one Android: screen phone, steering
   phone, tilt and sliders, a recording with **Save**.
3. Check that the screen phone stays on, the arm moves smoothly, and the recording shows up at
   `https://xxxx.trycloudflare.com/api/episodes`.
4. Stop everything (Ctrl+C in each terminal).

### Start of class (about 5 minutes)
1. **Terminal 1: start the server.** Choose a word for `TOKEN`: it protects the data download.
   ```
   cd cas-pair/nursing-teleop
   TOKEN=<your word> ./serve.sh
   ```
   If it says `address already in use`, another server is still running on port 8001: stop it, or
   use `PORT=8002 TOKEN=<your word> ./serve.sh` and port 8002 in the next step.
2. **Terminal 2: open the tunnel.**
   ```
   cloudflared tunnel --url http://localhost:8001
   ```
   It prints an address like `https://xxxx.trycloudflare.com`. That is your class address. A
   warning about QUIC can be ignored: it then uses HTTP/2.
3. **Terminal 3: keep the laptop awake.**
   ```
   caffeinate -d
   ```
   macOS will not sleep while this runs. Keep the lid open: closing it still puts the Mac to sleep.
4. **Projector: show the start QR code.** Open in the browser, with your address:
   ```
   https://xxxx.trycloudflare.com/qr.svg?data=https://xxxx.trycloudflare.com/
   ```
   and show it full screen.
5. Explain the task and the two roles (screen phone, steering phone), then let the groups start.

### During class
- Progress: `https://xxxx.trycloudflare.com/api/episodes` lists every saved recording with name,
  length and whether the cube reached the green square.
- Do **not** close the terminals or restart the tunnel: a restart gives a new address, and all
  groups would have to scan again.
- A group that wants to show its arm to the class can open its own screen link on the projector
  laptop instead of a phone (the room code is in the link, e.g. `https://xxxx.trycloudflare.com/?room=ABCD`).

### End of class
1. Download all recordings as one zip:
   `https://xxxx.trycloudflare.com/api/export?t=<your word>`.
   A copy also stays on your laptop in `~/teleop-data/episodes/` (one JSON file per recording).
2. Stop the three terminals with Ctrl+C.

What is in a recording: see [`README.md`](README.md#the-data).

## Students

Work in groups. Each group needs two phones.

### 1. Set up the screen phone
1. Scan the QR code on the projector.
2. The robot arm appears, with a big QR code and a room code.
3. Turn the phone sideways and prop it up where the whole group can see it.
4. Leave it on this page: if you switch to another app, the robot freezes.

### 2. Set up the steering phone
1. Scan the QR code on the **screen phone**.
2. Type your first name or a nickname and tap **Start**.
3. On an iPhone, tap **Allow** when it asks for motion access.
4. The QR code on the screen phone disappears and it shows "*your name* is steering".

### 3. Practise steering
Choose one of the two ways at the top:
- **Tilt the phone**: put your thumb on the big field and keep it there, then tilt the phone.
  Left / right turns the arm, tilting the top away from you / towards you moves the gripper out /
  in. Lift your thumb and the arm stops.
- **Sliders**: slide along the horizontal bar to turn, along the vertical bar to reach out / pull
  in. Let go and the arm stops.

And for both:
- **▲ raise / ▼ lower**: hold to move the gripper up or down.
- **Open gripper / Close gripper**: tap to switch.

### 4. Record
1. Tap **● Start recording**. The arm goes back to its start position and the cube moves a little.
2. Move the red cube onto the green square, for example by pushing it with the gripper.
3. Tap **✓ Save**. If it went wrong, tap **✕ Discard** and start again.
4. Each person records a few times.

### 5. Take turns
The next person scans the QR code on the screen phone (tap **QR** in its corner to show it again),
types their own name and taps **Take over**. Only one phone steers at a time.

### If something goes wrong
| what you see | what to do |
|---|---|
| the screen phone shows the big QR code again | the steering phone lost its connection: scan it again |
| "*someone* is steering" | tap **Take over** |
| the robot froze | the screen phone switched apps or locked: go back to the page, it continues |
| tilting does nothing | use **Sliders** |
| "screen not open" on the steering phone | the screen phone left the page: open it again (same room) |
