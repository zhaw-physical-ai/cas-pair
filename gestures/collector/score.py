"""Inspect, check and (if there is a hold-out set) score one uploaded ONNX model.
Run by app.py in a subprocess (memory and time limited).

    python score.py model.onnx takes.npz labels    -> prints one JSON line

Accepted models (the live page adapts its input the same way, see static/live.html):
  input  (N, T, 6)  time x channel, T any (the 2 s window is resampled to T points)
         (N, 6, T)  channel x time
         (N, 6*T)   flattened (time-major, like X.reshape(len(X), -1))
         (N, 30)    features(X) from load.py (for scikit-learn models via skl2onnx)
  output the first float output of shape (N, C): scores for the C labels, in the given order;
         or integer class indices (N,); or string labels (N,) (skl2onnx default)
labels: comma-separated label names in output order, e.g. "left,right,up,down,circle,idle".
"""
import json
import resource
import sys
import time

import numpy as np  # noqa: E402
import onnxruntime as ort  # noqa: E402

GESTURES = ["left", "right", "up", "down", "circle", "idle"]


def features(X):   # same as load.features
    return np.concatenate([X.mean(1), X.std(1), X.min(1), X.max(1), (X ** 2).mean(1)], 1)


def resample(X, T):
    if T == X.shape[1]:
        return X
    src, dst = np.linspace(0, 1, X.shape[1]), np.linspace(0, 1, T)
    return np.stack([np.stack([np.interp(dst, src, x[:, c]) for c in range(x.shape[1])], 1) for x in X])


def layout(dims):
    """dims: input shape with None for symbolic sizes -> (layout, T)"""
    if len(dims) == 3:
        if dims[1] == 6 and dims[2] != 6:
            return "nct", dims[2] or 100
        if dims[2] in (6, None):
            return "ntc", dims[1] or 100
    if len(dims) == 2:
        k = dims[1]
        if k == 30:
            return "features", 100
        if k is None:
            return "flat", 100
        if k % 6 == 0:
            return "flat", k // 6
    raise ValueError(f"input shape {dims} not supported: use (N, 100, 6), (N, 6, 100), (N, 600) or (N, 30)")


def adapt(X, lay, T):
    if lay == "features":
        return features(X).astype(np.float32)
    Xr = resample(X, T).astype(np.float32)
    if lay == "nct":
        return np.ascontiguousarray(Xr.transpose(0, 2, 1))
    if lay == "flat":
        return Xr.reshape(len(Xr), -1)
    return Xr


def predict(sess, inp, x, batch_ok):
    if batch_ok:
        return sess.run(None, {inp: x})
    outs = [sess.run(None, {inp: x[i:i + 1]}) for i in range(len(x))]
    return [np.concatenate([o[k] for o in outs]) for k in range(len(outs[0]))]


def main(model_path, data_path, labels_csv):
    labels = [s.strip() for s in labels_csv.split(",") if s.strip()]
    d = np.load(data_path)
    X, y = d["X"].astype(np.float32), d["y"]
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 2
    sess = ort.InferenceSession(model_path, opts, providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0]
    dims = [s if isinstance(s, int) else None for s in inp.shape]
    lay, T = layout(dims)
    x = adapt(X, lay, T)
    batch_ok = dims[0] in (None, len(x))
    t0 = time.perf_counter()
    outs = predict(sess, inp.name, x, batch_ok)
    ms = (time.perf_counter() - t0) * 1000 / len(x)
    names = [o.name for o in sess.get_outputs()]
    out_i, kind = None, None
    for i, o in enumerate(outs):      # prefer scores, then class indices, then string labels
        a = np.asarray(o)
        if a.dtype.kind == "f" and a.ndim == 2 and a.shape[0] == len(x):
            out_i, kind = i, "scores"
            break
    if out_i is None:
        for i, o in enumerate(outs):
            a = np.asarray(o)
            if a.ndim == 1 and len(a) == len(x) and a.dtype.kind in "iu":
                out_i, kind = i, "index"
                break
            if a.ndim == 1 and len(a) == len(x) and a.dtype.kind in "OUS":
                out_i, kind = i, "label"
                break
    if out_i is None:
        raise ValueError("no usable output: need scores (N, C), class indices (N,) or labels (N,). "
                         "For skl2onnx use options={'zipmap': False}.")
    a = np.asarray(outs[out_i])
    warnings = []
    if kind == "scores":
        if a.shape[1] != len(labels):
            raise ValueError(f"the model gives {a.shape[1]} scores but you listed {len(labels)} labels "
                             f"({','.join(labels)}): list one label per output, in output order")
        pred = [labels[j] for j in a.argmax(1)]
    elif kind == "index":
        if a.max() >= len(labels):
            raise ValueError(f"the model predicts class index {a.max()} but you listed {len(labels)} labels")
        pred = [labels[j] for j in a]
    else:
        pred = [str(v) for v in a]
        labels = sorted(set(pred) | set(labels))
    unknown = [lb for lb in labels if lb not in GESTURES]
    if unknown:
        warnings.append(f"labels {unknown} are not gestures; the live page never sends them to the sim")
    io = {"input": inp.name, "layout": lay, "T": int(T), "batch": bool(batch_ok),
          "output": names[out_i], "kind": kind, "labels": labels}
    res = {"ms": round(ms, 3), "io": io, "warnings": warnings}
    truth = [GESTURES[j] for j in y]
    hits = float(np.mean([p == t for p, t in zip(pred, truth)]))
    if "kind" in d.files and str(d["kind"]) == "check":
        # class takes, maybe training data: no score, but catch a wrong label order
        if len(y) >= 10 and hits < 0.35:
            warnings.append(f"only {hits:.0%} of {len(y)} class takes come out right: is the label "
                            f"order ({','.join(labels)}) the order of your model's outputs?")
    if "kind" in d.files and str(d["kind"]) == "holdout":
        truth = [GESTURES[j] for j in y]
        res["acc"] = round(float(np.mean([p == t for p, t in zip(pred, truth)])), 4)
        res["n"] = int(len(y))
        res["per_class"] = {g: round(float(np.mean([p == g for p, t in zip(pred, truth) if t == g])), 3)
                            if g in truth else None for g in GESTURES}
    return res


if __name__ == "__main__":
    resource.setrlimit(resource.RLIMIT_AS, (4 << 30, 4 << 30))   # 4 GB, for this subprocess only
    try:
        print(json.dumps(main(sys.argv[1], sys.argv[2], sys.argv[3])))
    except Exception as e:  # report, never crash the server
        msg = f"{type(e).__name__}: {e}".replace(str(sys.argv[1]), "model.onnx")
        print(json.dumps({"error": msg[:400]}))
