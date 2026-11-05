"""Load the pooled gesture recordings.

    from load import load, features, GESTURES
    X, y, person = load("https://<server>/api/export?t=<token>")   # or "gestures.zip"
    X.shape   # (N, 100, 6): 2 s at 50 Hz; channels acc x,y,z [m/s^2, incl. gravity], gyro x,y,z [rad/s]
    F = features(X)   # (N, 30) per-channel mean, std, min, max, energy

Every take is resampled to a fixed rate from its own timestamps (phones record at 50-200 Hz),
then cropped to the window with the most motion, or edge-padded if it is too short.
Handles both formats the collector stores: web recordings (JSON) and phyphox CSV uploads.
phyphox takes have either acc or gyro; the missing three channels are zero.

Run `python load.py <url-or-zip>` for a summary of the data. Needs only numpy.
"""
import csv
import io
import json
import sys
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np

GESTURES = ["left", "right", "up", "down", "circle", "idle"]
CHANNELS = ["acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z"]
STATS = ["mean", "std", "min", "max", "energy"]
FEATURE_NAMES = [f"{c}_{s}" for s in STATS for c in CHANNELS]
DEG = np.pi / 180


# ---------- reading the export ----------
def _read_records(src):
    """Yield (name, dict) for every take in a URL, a zip file, or a folder of .json files."""
    src = str(src)
    if src.startswith(("http://", "https://")):
        req = urllib.request.Request(src, headers={"User-Agent": "gestures-load"})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
        zf = zipfile.ZipFile(io.BytesIO(data))
    elif Path(src).is_dir():
        for p in sorted(Path(src).rglob("*.json")):
            yield p.name, json.loads(p.read_text())
        return
    else:
        zf = zipfile.ZipFile(src)
    for name in sorted(zf.namelist()):
        if name.endswith(".json"):
            yield name, json.loads(zf.read(name))


def _clean(a):
    """List of [x,y,z] with possible nulls -> float array; NaN gaps interpolated, all-NaN -> 0."""
    a = np.array([[np.nan if v is None else v for v in row] for row in a], dtype=float).reshape(-1, 3)
    idx = np.arange(len(a))
    for k in range(3):
        ok = np.isfinite(a[:, k])
        if ok.sum() == 0:
            a[:, k] = 0.0
        elif not ok.all():
            a[:, k] = np.interp(idx, idx[ok], a[ok, k])
    return a


def _is_ios(r):
    """The user agent decides when it is clear; otherwise trust the page's flag (iPadOS reports
    a Mac user agent). Early takes flagged Android Chrome as iOS, which this corrects."""
    ua = r.get("ua") or ""
    if any(k in ua for k in ("iPhone", "iPad", "iPod")):
        return True
    if "Android" in ua:
        return False
    return bool(r.get("ios"))


def _parse_web(r):
    """Web DeviceMotion take -> t [s], (n,6) acc+gyro in phyphox/Android conventions."""
    t = np.array([np.nan if v is None else v for v in r["t"]], dtype=float) / 1000.0
    acc = _clean(r["accG"])
    a, b, g = _clean(r["gyro"]).T                      # rotationRate alpha, beta, gamma [deg/s]
    gyro = np.stack([b, g, a], axis=1) * DEG           # spec: beta about x, gamma about y, alpha about z
    if _is_ios(r):
        acc = -acc   # iOS browsers report accelerationIncludingGravity with the opposite sign
    n = len(acc)
    # Degenerate timestamps (batched events): assume even spacing over the recording.
    if not np.isfinite(t).all() or len(np.unique(t)) < 0.5 * n or t[-1] - t[0] <= 0:
        dt = (r.get("interval") or 2500.0 / n) / 1000.0
        t = np.arange(n) * dt
    return t, np.hstack([acc, gyro])


def _parse_phyphox(r):
    """phyphox CSV ('Acceleration with g' or 'Gyroscope') -> t [s], (n,6)."""
    text = r["csv"]
    first = text.splitlines()[0]
    delim = max([",", ";", "\t"], key=first.count)
    if delim == ";":
        text = text.replace(",", ".")                   # 'Semicolon, decimal comma' export
    rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    header, rows = rows[0], [row for row in rows[1:] if row and row[0].strip()]
    cols = {}
    for i, h in enumerate(header):
        for ax in "xyz":
            if f" {ax} " in f" {h.strip()} ":                # "Acceleration x (m/s^2)"
                cols.setdefault(ax, i)
    if set(cols) != set("xyz"):
        raise ValueError(f"phyphox columns not found in header {header}")
    vals = np.array([[float(row[0])] + [float(row[cols[ax]]) for ax in "xyz"] for row in rows])
    t, xyz = vals[:, 0], vals[:, 1:]
    out = np.zeros((len(t), 6))
    gyro = r.get("kind") == "gyro" or "Gyroscope" in first or "rad/s" in first
    if gyro:
        out[:, 3:] = xyz
    else:
        out[:, :3] = xyz
    return t, out


def _resample(t, v, fs):
    order = np.argsort(t, kind="stable")
    t, v = t[order], v[order]
    t, keep = np.unique(t, return_index=True)
    v = v[keep]
    grid = np.arange(t[0], t[-1] + 1e-9, 1.0 / fs)
    return np.stack([np.interp(grid, t, v[:, k]) for k in range(v.shape[1])], axis=1)


def _window(v, T):
    """Crop to the T samples with the most motion, or edge-pad (centered) if shorter."""
    n = len(v)
    if n <= T:
        before = (T - n) // 2
        return np.pad(v, ((before, T - n - before), (0, 0)), mode="edge")
    acc_dev = v[:, :3] - np.median(v[:, :3], axis=0)
    energy = (acc_dev ** 2).sum(1) + (v[:, 3:] ** 2).sum(1) * 10.0   # rad/s weighted ~ m/s^2
    c = np.concatenate([[0.0], np.cumsum(energy)])
    start = int(np.argmax(c[T:] - c[:-T]))
    return v[start:start + T]


# ---------- public API ----------
def load(src, window_s=2.0, fs=50, return_meta=False, verbose=True):
    """Return X (N, T, 6) float32, y (N,) gesture names, person (N,) names.

    src: export URL ("https://.../api/export?t=TOKEN"), a downloaded zip, or a folder of .json.
    return_meta=True also returns a list of dicts (id, source, ios, raw sample rate).
    """
    T = int(round(window_s * fs))
    X, y, person, meta = [], [], [], []
    skipped, partial = [], 0
    for name, r in _read_records(src):
        try:
            if r.get("source") == "phyphox":
                t, v = _parse_phyphox(r)
                partial += 1
            else:
                t, v = _parse_web(r)
            if len(t) < 10:
                raise ValueError(f"only {len(t)} samples")
            raw_hz = (len(t) - 1) / (t.max() - t.min())
            w = _window(_resample(t, v, fs), T)
        except Exception as e:
            skipped.append(f"{name}: {e}")
            continue
        X.append(w)
        y.append(r["gesture"])
        person.append(r["person"])
        meta.append({"id": r.get("id", name), "source": r.get("source", "web"),
                     "ios": r.get("source", "web") == "web" and _is_ios(r), "raw_hz": round(float(raw_hz), 1)})
    if verbose:
        print(f"loaded {len(X)} takes from {len(set(person))} people", file=sys.stderr)
        if partial:
            print(f"  {partial} phyphox takes: acc-only or gyro-only, missing channels are 0",
                  file=sys.stderr)
        for s in skipped:
            print(f"  skipped {s}", file=sys.stderr)
    X = np.asarray(X, dtype=np.float32).reshape(-1, T, 6)
    out = (X, np.array(y, dtype=str), np.array(person, dtype=str))
    return out + (meta,) if return_meta else out


def features(X):
    """(N, T, 6) -> (N, 30): mean, std, min, max, energy (mean of squares) per channel.
    Column names in FEATURE_NAMES."""
    X = np.asarray(X, dtype=np.float32)
    return np.concatenate([X.mean(1), X.std(1), X.min(1), X.max(1), (X ** 2).mean(1)], axis=1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python load.py <export-url | gestures.zip>")
    X, y, person, meta = load(sys.argv[1], return_meta=True)
    print(f"X {X.shape}  (N, time, [acc_x acc_y acc_z gyro_x gyro_y gyro_z])")
    c = Counter(zip(person, y))
    w = max([len(p) for p in person] + [6])
    print("person".ljust(w), *[g.rjust(6) for g in GESTURES])
    for p in sorted(set(person), key=str.lower):
        print(p.ljust(w), *[str(c[(p, g)]).rjust(6) for g in GESTURES])
    hz = np.array([m["raw_hz"] for m in meta])
    if len(hz):
        print(f"raw sample rates: min {hz.min():.0f}, median {np.median(hz):.0f}, max {hz.max():.0f} Hz")
        idle = y == "idle"
        g = np.linalg.norm(X[:, :, :3], axis=2).mean(1)[idle]
        if len(g):
            print(f"|acc| on idle takes: median {np.median(g):.2f} m/s^2 (should be ~9.8)")
            # gravity direction per platform: should agree (upright: y ~ +9.8, flat: z ~ +9.8)
            for label, src, ios in [("web android", "web", False), ("web iOS", "web", True),
                                    ("phyphox", "phyphox", False)]:
                m = np.array([mt["source"] == src and mt["ios"] == ios for mt in meta]) & idle
                if m.any():
                    print(f"  idle mean acc x,y,z {label:<12} {np.round(X[m, :, :3].mean((0, 1)), 1)}"
                          f"  ({m.sum()} takes)")
