# Teacher checklist: set up and test the SO-101 phone teleop

Every step says what you should see (✅) and what to do if not (❌). The full test takes about
20 minutes: do it the day before, and the short version (part F) before class. Below, **LINK**
means your tunnel address, e.g. `https://xxxx.trycloudflare.com`.

## A. Start the system (on your laptop)

1. **The right version**: branch `nursing-simulation`, folder `nursing-teleop`.
   ```
   cd cas-pair
   git switch nursing-simulation && git pull
   ```
2. **Nothing old running.** Stop any old server with Ctrl+C in its terminal, then check:
   ```
   lsof -iTCP:8001 -sTCP:LISTEN
   ```
   ✅ no output: port 8001 is free.
3. **Terminal 1: server.**
   ```
   cd cas-pair/nursing-teleop
   TOKEN=nursing ./serve.sh
   ```
   ✅ `Application startup complete.` ❌ `address already in use`: back to step 2.
4. **Terminal 2: tunnel.**
   ```
   cloudflared tunnel --url http://localhost:8001
   ```
   ✅ it prints `https://xxxx.trycloudflare.com`: that is LINK. A warning about QUIC is fine.
5. **Terminal 3: keep the Mac awake.**
   ```
   caffeinate -d
   ```
   Keep the laptop plugged in and the lid open (closing the lid still makes it sleep).
6. **Server reachable through the tunnel:** open `LINK/healthz`.
   ✅ `{"ok":true,"episodes":...}`. ❌ not loading: a new tunnel needs a moment, wait 30 s and reload.

## B. Link and QR codes

7. **Start QR code for the projector:** open `LINK/qr.svg?data=LINK/` (your address in both places).
   ✅ a QR code. Scanning it with a phone camera opens `LINK/` with the robot arm.
8. **Laptop as the screen:** open `LINK/` on the laptop (the https address, not localhost).
   ✅ after a few seconds: arm, table, red cube, green square, a big QR code and a room code.
   ❌ a red line "Phones cannot open a localhost link": you opened localhost, use LINK.
9. **Steering phone:** scan the QR code *on the laptop screen*, type a name, tap **Start**
   (iPhone: tap **Allow**).
   ✅ phone: "connected to room …"; laptop: the QR code folds away, "*name* is steering".

## C. Controls (on the phone)

10. **Sliders:** horizontal bar right ✅ arm turns right on screen; left ✅ turns left. Vertical bar
    up ✅ gripper reaches out; down ✅ pulls in. Let go ✅ the arm stops.
11. **Tilt:** tap **Tilt the phone**, keep your thumb on the big field and tilt. ✅ tilt right turns
    right, top away reaches out, thumb off stops. Note whether the speed feels right (too fast,
    too slow, too sensitive?).
12. **Height and gripper:** ✅ **▲ raise / ▼ lower** move the gripper while held; **Open gripper**
    opens it and the button changes to **Close gripper**.
13. **The task itself:** lower the gripper and push the cube onto the green square.
    ✅ the laptop shows "cube on the green square!". Is it doable in about 2 minutes for a beginner?

## D. Recording and data

14. **A good run:** tap **● Start recording**. ✅ the arm resets, the cube moves a little, the
    laptop shows "● REC" counting seconds. Do the task, tap **✓ Save**.
    ✅ "saved (cube on target)" on the laptop and the phone.
15. **A bad run:** start a recording, tap **✕ Discard**. ✅ "discarded", nothing saved.
16. **The data:**
    - `LINK/api/episodes` ✅ your run with your name and `"success": true`.
    - `LINK/api/export?t=nursing` ✅ a zip downloads; with a wrong word ✅ it is refused.

## E. What can go wrong in class

17. **Take over:** a second phone scans the same QR code with another name.
    ✅ it shows "*first name* is steering"; after **Take over** it steers and the first phone shows
    the take-over screen.
18. **Connection lost:** close the tab on the steering phone.
    ✅ the arm stops and the laptop shows the big QR code again; scanning it again reconnects.
19. **A phone as the screen:** scan the projector QR code (step 7) with a phone, turn it sideways,
    steer it with a second phone. ✅ the arm moves smoothly. Leave it untouched for 2 minutes:
    ✅ the screen stays on. ❌ it dims: the wake lock does not work on that phone; tell the students
    to touch the screen now and then.
20. **From outside the ZHAW network:** turn off WiFi on a phone and repeat step 9 over mobile data.
    ✅ it works (this is how the online group connects from home).
21. **iPhone and Android:** do steps 9-11 once on each if you can; motion permission works
    differently on the two.

Clear the test recordings, so the class starts with an empty list:
```
mkdir -p ~/teleop-data/test-runs && mv ~/teleop-data/episodes/*.json ~/teleop-data/test-runs/
```

## F. Before class (e.g. 12:30 for 13:45)

1. Steps 2-6. The tunnel gives a **new LINK**.
2. Quick check: steps 8-10.
3. Post `LINK/` on Moodle, or send it to whoever posts it.
4. Show the start QR code (step 7) on the projector or the Station D screen. Print the
   instruction cards: [`station-d-card.html`](station-d-card.html) (English),
   [`station-d-card-de.html`](station-d-card-de.html) (German).
5. During class: do **not** close the terminals or restart the tunnel. A restart means a new link
   and new QR codes for everyone.

## G. After class

1. Download the zip: `LINK/api/export?t=nursing`. The files also stay in
   `~/teleop-data/episodes/`.
2. Stop the three terminals with Ctrl+C.
