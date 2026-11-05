# SO-101 gesture sim

A simulated SO-101 arm in your browser, driven by gesture labels: **left, right, up, down, circle,
idle**. Physics is [MuJoCo](https://mujoco.org) compiled to WebAssembly, rendering is three.js.
Nothing to install.

Goal: push the red cube onto the green square.

## Open it
Your instructor gives you the link. To run it yourself, serve this folder and open the page:

```
python3 -m http.server 8080      # in gestures/sim/
```

then http://localhost:8080. Opening `index.html` as a file does not work: the browser blocks
loading the model from `file://`. MuJoCo and three.js come from a CDN (about 3 MB download),
so it needs internet.

## Labels
The camera starts behind the arm, so left and right on screen are left and right for the arm.

| label | key | arm |
|---|---|---|
| left | ← | turn 20° left (shoulder_pan) |
| right | → | turn 20° right |
| up | ↑ | raise the gripper one level (~4 cm) |
| down | ↓ | lower the gripper one level |
| circle | c | open / close the gripper |
| idle | | nothing |
| | r | reset |

Up and down move shoulder_lift, elbow_flex and wrist_flex together so the gripper goes straight up
or down, 22 cm in front of the base, at 7 heights from 2 cm to 26 cm. Joints stop at their limits.
Drag to orbit, scroll or pinch to zoom.

## Live predictions
Add `?channel=NAME` to the URL. The page then asks `/api/live/NAME/next` on the same server for
new predictions (long-polling) and applies every one:

```
{"seq": 12, "label": "left", "p": 0.93, "t": 1730800000.1}
```

The live page (`/live` on your phone) sends them, with the same channel name.

Each message is one step. If your model sends a prediction every 100 ms, the arm hits the end
stop quickly: send a label only when a gesture is done, or filter by `p`. The panel top left
shows the last label, its probability and the connection status.

From your own code in the browser:

```js
sim.command("left")      // returns false for an unknown label
sim.qpos()               // {shoulder_pan: 0.0, shoulder_lift: -0.5, ...} in radians
sim.reset()
```

In an iframe, the parent page can send
`iframe.contentWindow.postMessage({type: "gesture", label: "up", p: 0.8}, "*")`.

## Credits
- SO-101 model: [MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie/tree/main/robotstudio_so101),
  from [TheRobotStudio/SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100), Apache-2.0. Meshes
  decimated, see [`model/NOTICE.md`](model/NOTICE.md).
- [MuJoCo](https://github.com/google-deepmind/mujoco) WebAssembly bindings `@mujoco/mujoco` 3.17.0
  by Google DeepMind, Apache-2.0.
- [three.js](https://threejs.org) 0.178.0, MIT.
