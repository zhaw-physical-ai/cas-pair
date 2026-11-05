"""Score one ONNX model on the hold-out set. Run by app.py in a subprocess (memory/time limited).

    python score.py model.onnx holdout.npz    -> prints one JSON line

Model contract (see ../GESTURES-TASK-DESCRIPTION.md, task 6): input float32 (N, 100, 6) in the
units load.py returns (acc m/s^2 incl. gravity, gyro rad/s, 50 Hz); output (N, 6) scores in
GESTURES order (logits or probabilities). Normalization belongs inside the model.
"""
import json
import resource
import sys
import time

resource.setrlimit(resource.RLIMIT_AS, (4 << 30, 4 << 30))   # 4 GB

import numpy as np  # noqa: E402
import onnxruntime as ort  # noqa: E402

GESTURES = ["left", "right", "up", "down", "circle", "idle"]


def main(model_path, holdout_path):
    d = np.load(holdout_path)
    X, y = d["X"].astype(np.float32), d["y"]
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 2
    sess = ort.InferenceSession(model_path, opts, providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0]
    dims = [d if isinstance(d, int) else None for d in inp.shape]   # symbolic dims -> None
    if len(dims) != 3 or dims[1] not in (100, None) or dims[2] not in (6, None):
        raise ValueError(f"input must be (N, 100, 6), model has {inp.shape}")
    batch_ok = dims[0] in (None, len(X))
    t0 = time.perf_counter()
    if batch_ok:
        out = sess.run(None, {inp.name: X})[0]
    else:  # fixed batch size 1
        out = np.concatenate([sess.run(None, {inp.name: X[i:i + 1]})[0] for i in range(len(X))])
    ms = (time.perf_counter() - t0) * 1000 / len(X)
    out = np.asarray(out).reshape(len(X), -1)
    if out.shape[1] != 6:
        raise ValueError(f"output must be (N, 6), model gives {out.shape}")
    pred = out.argmax(1)
    per_class = {g: round(float((pred[y == j] == j).mean()), 3) if (y == j).any() else None
                 for j, g in enumerate(GESTURES)}
    return {"acc": round(float((pred == y).mean()), 4), "n": int(len(y)),
            "ms": round(ms, 3), "per_class": per_class}


if __name__ == "__main__":
    try:
        print(json.dumps(main(sys.argv[1], sys.argv[2])))
    except Exception as e:  # report, never crash the server
        msg = f"{type(e).__name__}: {e}".replace(str(sys.argv[1]), "model.onnx")
        print(json.dumps({"error": msg[:300]}))
