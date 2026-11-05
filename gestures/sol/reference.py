# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy", "scikit-learn", "matplotlib", "torch"]
#
# [[tool.uv.index]]
# name = "pytorch-cpu"
# url = "https://download.pytorch.org/whl/cpu"
# explicit = true
#
# [tool.uv.sources]
# torch = { index = "pytorch-cpu" }
# ///
"""Instructor reference run for tasks 1-4. Not for students.

    uv run sol/reference.py "https://<server>/api/export?t=<token>"    # or gestures.zip
    uv run sol/reference.py gestures.zip --quick                        # fewer epochs

Prints the expected numbers and writes plots + results.md to ./ref_out/.
"""
import argparse
import sys
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from load import GESTURES, features, load  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("--out", default="ref_out")
ap.add_argument("--quick", action="store_true")
args = ap.parse_args()
OUT = Path(args.out)
OUT.mkdir(exist_ok=True)
torch.set_num_threads(8)
rng = np.random.default_rng(0)
results = []


def log(task, model, split, acc, n_train):
    results.append((task, model, split, acc, n_train))
    print(f"  {task:<8} {model:<22} {split:<10} acc {acc:.3f}  (train n~{n_train})")


X, y_str, person = load(args.src)
y = np.array([GESTURES.index(g) for g in y_str])
people = np.unique(person)
n_people = len(people)
K = min(5, n_people)
print(f"{len(X)} takes, {n_people} people, {np.bincount(y, minlength=6)} per gesture\n")
if n_people < 3:
    sys.exit("need at least 3 people for the per-person splits")

# ---------- task 1: plots + baseline ----------
print("Task 1/2: features, random split vs leave-person-out")
fig, axs = plt.subplots(2, 6, figsize=(20, 6), sharex=True)
for j, g in enumerate(GESTURES):
    idx = np.where(y == j)[0][:5]
    for i in idx:
        axs[0, j].plot(np.arange(100) / 50, X[i, :, :3], lw=0.8)
        axs[1, j].plot(np.arange(100) / 50, X[i, :, 3:], lw=0.8)
    axs[0, j].set_title(g)
axs[0, 0].set_ylabel("acc m/s²")
axs[1, 0].set_ylabel("gyro rad/s")
fig.tight_layout()
fig.savefig(OUT / "takes.png", dpi=80)
plt.close(fig)

F = features(X)
models = {
    "logreg": lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
    "random forest": lambda: RandomForestClassifier(300, n_jobs=-1, random_state=0),
}
n_tr = int(len(X) * (K - 1) / K)
for name, mk in models.items():
    rnd = cross_val_score(mk(), F, y, cv=StratifiedKFold(5, shuffle=True, random_state=0)).mean()
    grp = cross_val_score(mk(), F, y, cv=GroupKFold(K), groups=person).mean()
    log("T1/T2", name, "random", rnd, n_tr)
    log("T1/T2", name, "by-person", grp, n_tr)

# ---------- task 3: learning curves (RF, test people fixed) ----------
print("\nTask 3: learning curves (random forest, GroupKFold)")
rep_idx = np.zeros(len(X), int)  # rep number within (person, gesture)
for p in people:
    for j in range(6):
        m = np.where((person == p) & (y == j))[0]
        rep_idx[m] = np.arange(len(m))


def rf_acc(train_mask_fn):
    accs, ns = [], []
    for tr, te in GroupKFold(K).split(F, y, person):
        tr = tr[train_mask_fn(tr)]
        if len(np.unique(y[tr])) < 2:
            continue
        clf = RandomForestClassifier(200, n_jobs=-1, random_state=0).fit(F[tr], y[tr])
        accs.append((clf.predict(F[te]) == y[te]).mean())
        ns.append(len(tr))
    return np.mean(accs), np.mean(ns)


reps_curve = []
for r in [1, 2, 3, 5, 10, 15]:
    if r > rep_idx.max() + 1:
        break
    a, n = rf_acc(lambda tr: rep_idx[tr] < r)
    reps_curve.append((r, a, n))
    print(f"  reps/gesture {r:>2}: acc {a:.3f}  n_train {n:.0f}")

ppl_curve = []
max_train_people = n_people - int(np.ceil(n_people / K))
for k in sorted({1, 2, 3, 5, 8, 12, 20, max_train_people}):
    if k > max_train_people:
        continue
    accs, ns = [], []
    for seed in range(3):
        r_ = np.random.default_rng(seed)

        def keep(tr):
            pick = r_.choice(np.unique(person[tr]), k, replace=False)
            return np.isin(person[tr], pick)
        a, n = rf_acc(keep)
        accs.append(a)
        ns.append(n)
    ppl_curve.append((k, np.mean(accs), np.mean(ns)))
    print(f"  people in train {k:>2}: acc {np.mean(accs):.3f}  n_train {np.mean(ns):.0f}")

fig, ax = plt.subplots(figsize=(6, 4))
ax.plot([n for _, _, n in reps_curve], [a for _, a, _ in reps_curve], "o-", label="more reps per person")
ax.plot([n for _, _, n in ppl_curve], [a for _, a, _ in ppl_curve], "s-", label="more people")
ax.set_xlabel("training takes")
ax.set_ylabel("accuracy on unseen people")
ax.set_ylim(0, 1)
ax.legend()
fig.tight_layout()
fig.savefig(OUT / "learning_curves.png", dpi=100)
plt.close(fig)

# ---------- task 4: MLP and 1D CNN ----------
print("\nTask 4: neural nets (GroupKFold over people, early-stopping split inside train)")


class Net(nn.Module):
    def __init__(self, kind, mean, std, dropout):
        super().__init__()
        self.register_buffer("mean", torch.tensor(mean))
        self.register_buffer("std", torch.tensor(std))
        if kind == "mlp":
            self.f = nn.Sequential(nn.Flatten(), nn.Linear(600, 256), nn.ReLU(), nn.Dropout(dropout),
                                   nn.Linear(256, 128), nn.ReLU(), nn.Dropout(dropout), nn.Linear(128, 6))
        else:
            self.f = nn.Sequential(
                nn.Conv1d(6, 32, 5, padding=2), nn.ReLU(), nn.MaxPool1d(2),
                nn.Conv1d(32, 64, 5, padding=2), nn.ReLU(), nn.MaxPool1d(2),
                nn.Conv1d(64, 64, 5, padding=2), nn.ReLU(), nn.AdaptiveAvgPool1d(1),
                nn.Flatten(), nn.Dropout(dropout), nn.Linear(64, 6))

    def forward(self, x):  # x: (B, T, 6) raw units
        x = (x - self.mean) / self.std
        return self.f(x.transpose(1, 2))


def rand_rot(B, max_deg=30):
    ax = torch.randn(B, 3)
    ax = ax / ax.norm(dim=1, keepdim=True)
    a = (torch.rand(B) * 2 - 1) * np.deg2rad(max_deg)
    Kx = torch.zeros(B, 3, 3)
    Kx[:, 0, 1], Kx[:, 0, 2], Kx[:, 1, 2] = -ax[:, 2], ax[:, 1], -ax[:, 0]
    Kx = Kx - Kx.transpose(1, 2)
    s, c = torch.sin(a)[:, None, None], torch.cos(a)[:, None, None]
    return torch.eye(3) + s * Kx + (1 - c) * Kx @ Kx


def augment(x):
    R = rand_rot(len(x))
    x = torch.cat([x[..., :3] @ R.transpose(1, 2), x[..., 3:] @ R.transpose(1, 2)], -1)
    x = torch.roll(x, int(np.random.randint(-10, 11)), dims=1)
    return x + 0.05 * x.std(dim=(0, 1), keepdim=True) * torch.randn_like(x)


def train(kind, Xtr, ytr, Xva, yva, reg, epochs):
    mean = Xtr.reshape(-1, 6).mean(0)
    std = Xtr.reshape(-1, 6).std(0) + 1e-6
    net = Net(kind, mean, std, 0.3 if reg else 0.0)
    opt = torch.optim.AdamW(net.parameters(), 1e-3, weight_decay=1e-2 if reg else 0.0)
    lossf = nn.CrossEntropyLoss()
    Xt, yt = torch.tensor(Xtr), torch.tensor(ytr)
    Xv, yv = torch.tensor(Xva), torch.tensor(yva)
    hist, best = [], (np.inf, None)
    for ep in range(epochs):
        net.train()
        perm = torch.randperm(len(Xt))
        tl = 0.0
        for i in range(0, len(Xt), 64):
            b = perm[i:i + 64]
            xb = augment(Xt[b]) if reg else Xt[b]
            loss = lossf(net(xb), yt[b])
            opt.zero_grad()
            loss.backward()
            opt.step()
            tl += loss.item() * len(b)
        net.eval()
        with torch.no_grad():
            vl = lossf(net(Xv), yv).item()
        hist.append((tl / len(Xt), vl))
        if reg and vl < best[0]:  # early stopping: keep best weights on the inner val people
            best = (vl, {k: v.clone() for k, v in net.state_dict().items()})
    if reg and best[1] is not None:
        net.load_state_dict(best[1])
    return net, hist


EPOCHS = 40 if args.quick else 150
curves = {}
for kind in ["mlp", "cnn"]:
    for reg in [False, True]:
        label = f"{kind} {'regularized' if reg else 'plain'}"
        t0 = time.time()
        accs, ns = [], []
        for fold, (tr, te) in enumerate(GroupKFold(K).split(X, y, person)):
            inner = GroupShuffleSplit(1, test_size=0.2, random_state=fold)
            itr, iva = next(inner.split(tr, groups=person[tr]))
            torch.manual_seed(fold)
            net, hist = train(kind, X[tr[itr]], y[tr[itr]], X[tr[iva]], y[tr[iva]], reg, EPOCHS)
            with torch.no_grad():
                pred = net.eval()(torch.tensor(X[te])).argmax(1).numpy()
            accs.append((pred == y[te]).mean())
            ns.append(len(itr))
            if fold == 0:
                curves[label] = hist
        log("T4", label, "by-person", float(np.mean(accs)), int(np.mean(ns)))
        print(f"           ({time.time() - t0:.0f} s)")

fig, axs = plt.subplots(1, 4, figsize=(18, 4), sharey=True)
for ax, (label, h) in zip(axs, curves.items()):
    h = np.array(h)
    ax.plot(h[:, 0], label="train")
    ax.plot(h[:, 1], label="val (unseen people)")
    ax.set_title(label)
    ax.set_xlabel("epoch")
axs[0].set_ylabel("cross-entropy")
axs[0].set_ylim(0, 3)
axs[0].legend()
fig.tight_layout()
fig.savefig(OUT / "loss_curves.png", dpi=90)
plt.close(fig)

# ---------- summary ----------
lines = ["| task | model | split | accuracy | n train |", "|---|---|---|---|---|"]
lines += [f"| {t} | {m} | {s} | {a:.3f} | {n} |" for t, m, s, a, n in results]
lines += ["", "Learning curve, reps per gesture (RF, by person): "
          + ", ".join(f"{r}: {a:.2f}" for r, a, _ in reps_curve),
          "Learning curve, people in train (RF, by person): "
          + ", ".join(f"{k}: {a:.2f}" for k, a, _ in ppl_curve)]
(OUT / "results.md").write_text(f"Source: {args.src}\n{len(X)} takes, {n_people} people\n\n"
                                + "\n".join(lines) + "\n")
print("\n" + "\n".join(lines))
print(f"\nplots and results.md in {OUT}/")
