"""PIPELINE TEST ONLY - synthetic gesture takes. Not real data; never mix into the class data.

Posts fake takes through the collector API (web JSON and phyphox CSV uploads), checks the API
(token, delete-last, counts, dashboard, export), and saves the export zip. Run it against a
separate server with its own DATA_DIR:

    CLASS_TOKEN=test DATA_DIR=/tmp/gtest uv run uvicorn app:app --port 8791 &
    uv run --with numpy fake_data.py --url http://127.0.0.1:8791 --token test --out fake.zip

The signals are crude (sine pulses along the move axis, per-person grip rotation, speed,
amplitude, sample rate), just realistic enough that leave-one-person-out is harder than a
random split. Numbers from models trained on them say nothing about the real class data.
"""
import argparse
import io
import json
import urllib.error
import urllib.request
import uuid
import zipfile

import numpy as np

GESTURES = ["left", "right", "up", "down", "circle", "idle"]
G = 9.81


def rot(rng, max_deg):
    """Random rotation matrix, angle up to max_deg about a random axis."""
    ax = rng.normal(size=3)
    ax /= np.linalg.norm(ax)
    a = np.deg2rad(rng.uniform(-max_deg, max_deg))
    K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
    return np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * K @ K


def take(rng, gesture, p, duration):
    """One take in Android/phyphox conventions: t [s], acc incl. g [m/s^2], gyro [rad/s]."""
    fs = p["fs"] * rng.uniform(0.97, 1.03)
    t = np.cumsum(rng.uniform(0.8, 1.2, int(duration * fs)) / fs)
    t -= t[0]
    D = p["dur"] * rng.uniform(0.8, 1.25)                       # gesture length, s
    t0 = rng.uniform(0.3, max(0.35, duration - D - 0.2))        # onset
    s = np.clip((t - t0) / D, 0, 1)
    on = (s > 0) & (s < 1)
    A = p["amp"] * rng.uniform(0.8, 1.2)
    lin = np.zeros((len(t), 3))
    gyr = np.zeros((len(t), 3))
    pulse = A * np.sin(2 * np.pi * s) * on                     # accelerate, then brake
    if gesture in ("left", "right"):
        lin[:, 0] = pulse * (-1 if gesture == "left" else 1)
        gyr[:, 1] = 0.3 * pulse / A * (-1 if gesture == "left" else 1)
    elif gesture in ("up", "down"):
        lin[:, 1] = pulse * (1 if gesture == "up" else -1)
        gyr[:, 0] = 0.3 * pulse / A * (1 if gesture == "up" else -1)
    elif gesture == "circle":
        w = 2 * np.pi * s
        lin[:, 0] = -A * np.cos(w) * on
        lin[:, 1] = -A * np.sin(w) * on
        gyr[:, 2] = 0.8 * np.sin(np.pi * s) * on
    # idle: only tremor + noise
    lin += p["style"] * np.sin(2 * np.pi * 3 * t)[:, None] * on[:, None]   # personal wobble
    R = p["R"] @ rot(rng, 8)                                    # grip: per person + per take
    gravity = np.array([0, G, 0])                               # upright, screen facing you
    acc = (gravity + lin) @ R.T + rng.normal(0, p["noise"], (len(t), 3))
    gyr = gyr @ R.T + rng.normal(0, 0.03, (len(t), 3)) + 0.05 * np.sin(2 * np.pi * 1.3 * t)[:, None]
    return t, acc, gyr


def post(url, path, data=None, method=None, headers=None):
    req = urllib.request.Request(url + path, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def post_web(url, token, person, gesture, t, acc, gyr, ios, rng):
    a = -acc if ios else acc                                    # iOS reports opposite sign
    d = np.rad2deg(gyr)
    alpha, beta, gamma = d[:, 2], d[:, 0], d[:, 1]
    r4 = lambda x: np.round(x, 4).tolist()
    body = {"token": token, "person": person, "gesture": gesture, "ios": ios,
            "ua": ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) fake" if ios
                   else "Mozilla/5.0 (Linux; Android 14; K) Chrome/156.0 fake"), "interval": 1000 * float(np.mean(np.diff(t))),
            "t": r4(1000 * (t + rng.uniform(1000, 5000))),       # ms, arbitrary origin
            "accG": r4(a), "acc": r4(a - (G * np.array([0, 1, 0]))),
            "gyro": r4(np.stack([alpha, beta, gamma], 1))}
    if rng.random() < 0.05:                                     # occasional null rotationRate
        body["gyro"][3] = [None, None, None]
    return post(url, "/api/recording", json.dumps(body).encode(), headers={"Content-Type": "application/json"})


def phyphox_file(t, xyz, kind, variant):
    if kind == "acc":
        names = ["Acceleration x (m/s^2)", "Acceleration y (m/s^2)", "Acceleration z (m/s^2)",
                 "Absolute acceleration (m/s^2)"]
    else:
        names = ["Gyroscope x (rad/s)", "Gyroscope y (rad/s)", "Gyroscope z (rad/s)", "Absolute (rad/s)"]
    rows = np.column_stack([t, xyz, np.linalg.norm(xyz, axis=1)])
    if variant == "semicolon":
        lines = [";".join(f'"{h}"' for h in ["Time (s)"] + names)]
        lines += [";".join(f"{v:.9E}".replace(".", ",") for v in r) for r in rows]
    else:
        lines = [",".join(f'"{h}"' for h in ["Time (s)"] + names)]
        lines += [",".join(f"{v:.9E}" for v in r) for r in rows]
    text = "\n".join(lines) + "\n"
    if variant == "zip":
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("Raw Data.csv", text)
            z.writestr("meta/device.csv", '"property","value"\n')
        return "export.zip", buf.getvalue()
    return "Raw Data.csv", text.encode()


def post_phyphox(url, token, person, gesture, fname, content):
    b = uuid.uuid4().hex
    parts = []
    for k, v in (("token", token), ("person", person), ("gesture", gesture)):
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    parts.append(f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{fname}"\r\n'
                 f"Content-Type: application/octet-stream\r\n\r\n".encode() + content + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    return post(url, "/api/phyphox", b"".join(parts),
                headers={"Content-Type": f"multipart/form-data; boundary={b}"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8791")
    ap.add_argument("--token", default="test")
    ap.add_argument("--people", type=int, default=8)
    ap.add_argument("--reps", type=int, default=15)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="fake.zip")
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    url = a.url.rstrip("/")

    # API checks
    st, _ = post(url, "/api/recording", json.dumps({"token": "wrong"}).encode(),
                 headers={"Content-Type": "application/json"})
    assert st == 403, st
    st, _ = post(url, "/api/export?t=wrong")
    assert st == 403, st

    n_ok = 0
    for i in range(a.people):
        name = f"Fake Person {i}"
        p = {"fs": rng.choice([50, 60, 100, 200]), "R": rot(rng, 35), "dur": rng.uniform(0.5, 1.0),
             "amp": rng.uniform(4, 12), "noise": rng.uniform(0.05, 0.3), "style": rng.uniform(0, 2)}
        ios = i % 3 == 0
        for g in GESTURES:
            for k in range(a.reps):
                if i == a.people - 1 and k < 3:                 # some phyphox uploads
                    kind = ["acc", "gyro", "acc"][k]
                    variant = ["comma", "semicolon", "zip"][k]
                    t, acc, gyr = take(rng, g, p, 4.0)
                    fname, content = phyphox_file(t, acc if kind == "acc" else gyr, kind, variant)
                    st, body = post_phyphox(url, a.token, name, g, fname, content)
                else:
                    t, acc, gyr = take(rng, g, p, 2.5)
                    st, body = post_web(url, a.token, name, g, t, acc, gyr, ios, rng)
                assert st == 200, (st, body)
                n_ok += 1
    print(f"posted {n_ok} takes")

    # a bad take, then delete it again
    t, acc, gyr = take(rng, "left", p, 2.5)
    post_web(url, a.token, "Fake Person 0", "left", t, acc, gyr, True, rng)
    before = json.loads(post(url, "/api/counts?person=Fake%20Person%200")[1])["left"]
    st, body = post(url, "/api/recording/last?person=Fake%20Person%200&t=wrong", method="DELETE")
    assert st == 403, st
    st, body = post(url, f"/api/recording/last?person=Fake%20Person%200&t={a.token}", method="DELETE")
    assert st == 200 and json.loads(body)["counts"]["left"] == before - 1, body
    # bad phyphox upload is rejected with a hint
    st, body = post_phyphox(url, a.token, "Fake Person 1", "up", "x.csv",
                            b'"Time (s)","Linear Acceleration x (m/s^2)"\n0,1\n')
    assert st == 400 and b"with g" in body, body
    st, body = post(url, "/dashboard")
    assert st == 200 and b"Fake Person 0" in body and b"<svg" in body
    st, data = post(url, f"/api/export?t={a.token}")
    assert st == 200
    open(a.out, "wb").write(data)
    print(f"API checks passed; export {len(data) // 1024} kB -> {a.out}")


if __name__ == "__main__":
    main()
