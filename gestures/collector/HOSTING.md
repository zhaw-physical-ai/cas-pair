# Run your own gestures server

The class server is enough for the lab. Run your own copy to try things without the class: your
own recordings, uploads, the live page and the sim. Everything is in this folder: one Python app
(`app.py`), the phone pages (`static/`), and the sim (`../sim/`).

Phones only give motion sensors to **HTTPS** pages. So the server needs an HTTPS address: RunPod's
port proxy gives you one, and on a laptop a Cloudflare quick tunnel does.

## On a RunPod pod
1. Deploy a **CPU pod** (no GPU needed), any Ubuntu-based template. Under **Expose HTTP ports**,
   add `8000`. A volume at `/workspace` keeps your data when the pod stops.
2. In the pod's terminal:
   ```
   git clone https://github.com/zhaw-physical-ai/cas-pair.git
   cd cas-pair/gestures/collector
   CLASS_TOKEN=<a word of your choice> DATA_DIR=/workspace/gestures-data ./serve.sh
   ```
3. Your server is at `https://<pod-id>-8000.proxy.runpod.net` (the pod's **Connect** menu shows
   the link). Open `/pages?t=<your word>` there: it lists every page.

## On your laptop
```
git clone https://github.com/zhaw-physical-ai/cas-pair.git
cd cas-pair/gestures/collector
CLASS_TOKEN=<a word> ./serve.sh                       # terminal 1
cloudflared tunnel --url http://localhost:8000        # terminal 2: prints https://....trycloudflare.com
```
`cloudflared` is a single download from Cloudflare (no account needed for quick tunnels). With
`tmux` installed, `CLASS_TOKEN=<a word> ./run.sh` starts both and prints the links.

## Pages
| | |
|---|---|
| `/?t=<word>` | phone: record gestures |
| `/upload?t=<word>` | upload an ONNX model |
| `/live?t=<word>` | phone: run a model live, send gestures to the sim |
| `/sim/?channel=<name>` | the SO-101 sim; same channel name as on the live page |
| `/dashboard` | takes per person and gesture |
| `/api/export?t=<word>` | all takes as a zip, for `load()` |

Your server starts empty. To train on the class data, keep using the class export link; your
server is for uploading, testing live and steering the sim.

## For your coding agent
Paste this:
> Start the gestures server from `gestures/collector/HOSTING.md` in github.com/zhaw-physical-ai/cas-pair
> on this machine. Use `serve.sh` with CLASS_TOKEN=<word>. If this is a RunPod pod, check that
> HTTP port 8000 is exposed and give me the `https://<pod-id>-8000.proxy.runpod.net` link;
> otherwise start a Cloudflare quick tunnel and give me its https link. Check that `/healthz`
> answers through that link before you report back.

## If something does not work
- Phone says **Not HTTPS**: open the `https://` link, not `http://` or the pod's IP.
- **Sim stays on "loading"**: it downloads MuJoCo and three.js from the jsDelivr CDN, so the
  laptop needs internet access.
- **Live page lists no models**: upload one at `/upload` on *this* server, with the same word.
- Data is in `DATA_DIR`, one JSON file per take; uploaded models in `DATA_DIR/models/`.
