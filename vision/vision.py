"""Helpers for the vision lab: data, SAM 2.1 labeling, YOLO datasets, evaluation.

    from vision import *
    images, instances, train, test = load_pennfudan()   # downloads ~50 MB once
    sam = SamLabeler()                                  # SAM 2.1, ~300 MB once
    masks, scores = sam(images[0], boxes=boxes_from_instances(instances[0]))

images[i]:    (H, W, 3) uint8 RGB
instances[i]: (H, W) int, 0 = background, 1..N = one id per person (the human labels)
masks:        (n, H, W) bool, one mask per prompt / per object

Everything here is plumbing. The experiments are yours.
"""
import pathlib
import time
import urllib.request
import zipfile

import matplotlib.pyplot as plt
import numpy as np
import torch
from PIL import Image, ImageOps

PENNFUDAN_URL = "https://www.cis.upenn.edu/~jshi/ped_html/PennFudanPed.zip"


def get_device():
    """'cuda' on Colab / RunPod, 'mps' on a Mac, else 'cpu'."""
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


# ---------- data ----------
def load_pennfudan(root="data", n_test=50, seed=0):
    """Penn-Fudan pedestrians: 170 street photos with a human-drawn mask per person.
    Returns images, instances, train, test; train/test are index arrays (120 / 50)."""
    root = pathlib.Path(root)
    if not (root / "PennFudanPed").exists():
        root.mkdir(parents=True, exist_ok=True)
        print("downloading Penn-Fudan (~50 MB) ...")
        urllib.request.urlretrieve(PENNFUDAN_URL, root / "PennFudanPed.zip")
        zipfile.ZipFile(root / "PennFudanPed.zip").extractall(root)
    img_paths = sorted((root / "PennFudanPed" / "PNGImages").glob("*.png"))
    mask_paths = sorted((root / "PennFudanPed" / "PedMasks").glob("*.png"))
    images = [np.array(Image.open(p).convert("RGB")) for p in img_paths]
    instances = [np.array(Image.open(p)) for p in mask_paths]
    perm = np.random.default_rng(seed).permutation(len(images))
    return images, instances, np.sort(perm[n_test:]), np.sort(perm[:n_test])


def load_folder(folder, max_side=1024):
    """All .jpg/.jpeg/.png photos in a folder as RGB arrays, upright, longest side <= max_side."""
    paths = sorted(p for p in pathlib.Path(folder).iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png"))
    out = []
    for p in paths:
        im = ImageOps.exif_transpose(Image.open(p)).convert("RGB")   # phones store rotation in EXIF
        im.thumbnail((max_side, max_side))
        out.append(np.array(im))
    return out


def boxes_from_instances(inst):
    """One tight box [x0, y0, x1, y1] per person id in an instance mask."""
    boxes = []
    for pid in np.unique(inst):
        if pid == 0:
            continue
        ys, xs = np.nonzero(inst == pid)
        boxes.append([int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())])
    return boxes


def instances_to_masks(inst):
    """Instance mask (H, W) -> (n, H, W) bool, one mask per person."""
    return np.stack([inst == pid for pid in np.unique(inst) if pid != 0])


# ---------- metrics ----------
def iou(pred, gt):
    """Intersection over union of two bool masks: 0 = no overlap, 1 = identical."""
    union = np.logical_or(pred, gt).sum()
    return np.logical_and(pred, gt).sum() / union if union else 1.0


def mean_iou(predict, images, instances):
    """Mean IoU of predict(image) -> (H, W) bool against 'any person' in the human labels."""
    return float(np.mean([iou(predict(im), inst > 0) for im, inst in zip(images, instances)]))


def person_recall(predict, images, instances, min_cover=0.5):
    """Fraction of people (human labels) of whom at least min_cover of the pixels are predicted.
    Returns (recall, misses); misses = list of (image index, person id) that were not found."""
    found, misses = 0, []
    for k, (im, inst) in enumerate(zip(images, instances)):
        pred = predict(im)
        for pid in np.unique(inst):
            if pid == 0:
                continue
            person = inst == pid
            if (pred & person).sum() >= min_cover * person.sum():
                found += 1
            else:
                misses.append((k, int(pid)))
    return found / (found + len(misses)), misses


def seconds_per_image(predict, images):
    """Average wall-clock time of predict(image), after one warm-up call."""
    predict(images[0])
    t0 = time.time()
    for im in images:
        predict(im)
    return (time.time() - t0) / len(images)


# ---------- SAM 2.1 ----------
class SamLabeler:
    """SAM 2.1 as a labeling assistant. Give it boxes or clicks, get masks.

    sam = SamLabeler("facebook/sam2.1-hiera-base-plus")   # also: -tiny, -small, -large
    masks, scores = sam(image, boxes=[[x0, y0, x1, y1], ...])           # one mask per box
    masks, scores = sam(image, points=[[x, y], ...], point_labels=[1, 0, ...])
        # all clicks describe ONE object; label 1 = part of it, 0 = not part of it
    scores: SAM's own guess of each mask's IoU
    """

    def __init__(self, model_id="facebook/sam2.1-hiera-base-plus", device=None):
        from transformers import Sam2Model, Sam2Processor

        self.device = device or get_device()
        self.processor = Sam2Processor.from_pretrained(model_id)
        self.model = Sam2Model.from_pretrained(model_id).to(self.device).eval()
        print(f"{model_id}: {sum(p.numel() for p in self.model.parameters()) / 1e6:.0f} M parameters")

    def __call__(self, image, boxes=None, points=None, point_labels=None):
        kwargs = {}
        if boxes is not None:
            kwargs["input_boxes"] = [[list(map(float, b)) for b in boxes]]
        if points is not None:
            kwargs["input_points"] = [[[list(map(float, p)) for p in points]]]
            kwargs["input_labels"] = [[list(point_labels or [1] * len(points))]]
        inputs = self.processor(images=image, return_tensors="pt", **kwargs)
        inputs = inputs.to(device=self.device, dtype=torch.float32)   # float32: MPS has no float64
        with torch.no_grad():
            out = self.model(**inputs, multimask_output=False)
        masks = self.processor.post_process_masks(out.pred_masks.cpu(), inputs["original_sizes"])[0][:, 0]
        return masks.numpy().astype(bool), out.iou_scores.cpu().numpy()[0, :, 0]


# ---------- text prompts (task 5) ----------
class TextBoxer:
    """Grounding DINO: boxes from a text prompt, to feed SAM without drawing boxes yourself.

    boxer = TextBoxer()
    boxes, scores = boxer(image, "a laptop.")     # lower case, end with a period
    """

    def __init__(self, model_id="IDEA-Research/grounding-dino-tiny", device=None):
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor

        self.device = device or get_device()
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = AutoModelForZeroShotObjectDetection.from_pretrained(model_id).to(self.device).eval()

    def __call__(self, image, text, threshold=0.35, text_threshold=0.25):
        inputs = self.processor(images=image, text=text, return_tensors="pt").to(self.device)
        with torch.no_grad():
            out = self.model(**inputs)
        r = self.processor.post_process_grounded_object_detection(
            out, inputs["input_ids"], threshold=threshold, text_threshold=text_threshold,
            target_sizes=[image.shape[:2]])[0]
        return r["boxes"].cpu().numpy().tolist(), r["scores"].cpu().numpy()


# ---------- YOLO ----------
def mask_to_polygon(mask):
    """Outline of the largest blob of a bool mask, as (n, 2) x, y normalised to 0..1; None if empty."""
    import cv2

    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    xy = max(contours, key=cv2.contourArea).reshape(-1, 2)
    if len(xy) < 3:
        return None
    h, w = mask.shape
    return xy / [w, h]


def write_yolo_dataset(folder, images, masks, name="person"):
    """Write images and their per-object masks in the YOLO segmentation format.

    images: list of (H, W, 3) uint8; masks: list of (n_i, H, W) bool, one entry per image
    folder/images/train/0000.png, folder/labels/train/0000.txt (one polygon line per object)
    Returns the path of folder/data.yaml, for YOLO(...).train(data=...).
    """
    folder = pathlib.Path(folder).resolve()
    for sub in ("images", "labels"):
        d = folder / sub / "train"
        d.mkdir(parents=True, exist_ok=True)
        for old in d.iterdir():
            old.unlink()
    n_objects = 0
    for k, (im, ms) in enumerate(zip(images, masks)):
        Image.fromarray(im).save(folder / "images" / "train" / f"{k:04d}.png")
        lines = []
        for m in ms:
            poly = mask_to_polygon(m)
            if poly is not None:
                lines.append("0 " + " ".join(f"{v:.5f}" for v in poly.flatten()))
        (folder / "labels" / "train" / f"{k:04d}.txt").write_text("\n".join(lines))
        n_objects += len(lines)
    yaml = folder / "data.yaml"
    yaml.write_text(f"path: {folder}\ntrain: images/train\nval: images/train\nnames:\n  0: {name}\n")
    print(f"{len(images)} images, {n_objects} objects -> {yaml}")
    return str(yaml)


def yolo_device(device=None):
    """The device argument Ultralytics expects."""
    device = device or get_device()
    return 0 if device == "cuda" else device


def train_yolo(data, name, epochs=30, imgsz=640, model="yolo11n-seg.pt", device=None, **kwargs):
    """Fine-tune a YOLO segmentation model on a dataset from write_yolo_dataset; returns the trained model.

    Weights end up in runs/<name>/weights/last.pt. model="yolo11n-seg.yaml" trains from scratch.
    val=False: YOLO does not validate during training; you measure the test set yourself.
    Extra keyword arguments go to Ultralytics' train(), e.g. batch=8 or fliplr=0.
    """
    from ultralytics import YOLO

    runs = pathlib.Path("runs").resolve()     # absolute: Ultralytics puts relative paths under runs/segment/
    YOLO(model).train(data=data, epochs=epochs, imgsz=imgsz, val=False, plots=False, device=yolo_device(device),
                      project=str(runs), name=name, exist_ok=True, verbose=False, **kwargs)
    return YOLO(runs / name / "weights" / "last.pt")


def yolo_predict(model, image, conf=0.25, device=None):
    """Run a YOLO segmentation model. Returns masks (n, H, W) bool, boxes (n, 4), scores (n,)."""
    r = model.predict(Image.fromarray(image), retina_masks=True, conf=conf, device=yolo_device(device),
                      verbose=False)[0]
    if r.masks is None:
        return np.zeros((0, *image.shape[:2]), bool), np.zeros((0, 4)), np.zeros(0)
    return (r.masks.data.cpu().numpy() > 0.5, r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy())


# ---------- U-Net (task 3) ----------
class UNetSegmenter:
    """A U-Net with a pretrained ResNet-18 encoder for semantic segmentation (person / not person).

    unet = UNetSegmenter().fit(images, masks)   # masks: list of (H, W) bool
    pred = unet(image)                          # (H, W) bool
    """

    MEAN = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    STD = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)

    def __init__(self, size=256, encoder_weights="imagenet", device=None):
        import segmentation_models_pytorch as smp

        self.size, self.device = size, device or get_device()
        self.model = smp.Unet("resnet18", encoder_weights=encoder_weights, classes=1).to(self.device)

    def _x(self, image):
        x = torch.from_numpy(image).permute(2, 0, 1).float() / 255
        x = torch.nn.functional.interpolate(x[None], size=(self.size, self.size), mode="bilinear")[0]
        return (x - self.MEAN) / self.STD

    def fit(self, images, masks, epochs=25, batch_size=8, lr=1e-3, seed=0):
        """Adam, binary cross-entropy, cosine learning rate, random left/right flips."""
        F = torch.nn.functional
        torch.manual_seed(seed)
        X = torch.stack([self._x(im) for im in images])
        Y = torch.stack([F.interpolate(torch.from_numpy(m.astype(np.float32))[None, None],
                                       size=(self.size, self.size), mode="nearest")[0] for m in masks])
        opt = torch.optim.Adam(self.model.parameters(), lr=lr)
        sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)
        self.history = []
        for _ in range(epochs):
            self.model.train()
            order, total = torch.randperm(len(X)), 0.0
            for s in range(0, len(X), batch_size):
                idx = order[s:s + batch_size]
                xb, yb = X[idx].to(self.device), Y[idx].to(self.device)
                flip = torch.rand(len(idx), device=self.device) < 0.5
                xb[flip], yb[flip] = xb[flip].flip(-1), yb[flip].flip(-1)
                loss = F.binary_cross_entropy_with_logits(self.model(xb), yb)
                opt.zero_grad()
                loss.backward()
                opt.step()
                total += loss.item() * len(idx)
            sched.step()
            self.history.append(total / len(X))
        return self

    @torch.no_grad()
    def __call__(self, image):
        self.model.eval()
        logits = self.model(self._x(image)[None].to(self.device))
        logits = torch.nn.functional.interpolate(logits, size=image.shape[:2], mode="bilinear")
        return (logits[0, 0] > 0).cpu().numpy()


# ---------- plotting ----------
def show(ax, image, mask=None, boxes=(), points=(), point_labels=None, title=""):
    """Image with an optional mask overlay (cyan), boxes (green) and clicks (green = 1, red = 0).
    mask may be (H, W) or (n, H, W); an int instance mask is shown as 'any person'."""
    ax.imshow(image)
    if mask is not None:
        m = np.asarray(mask)
        m = m.any(0) if m.ndim == 3 else m > 0
        overlay = np.zeros((*m.shape, 4))
        overlay[m] = (0.0, 0.9, 1.0, 0.55)
        ax.imshow(overlay)
    for x0, y0, x1, y1 in boxes:
        ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec="lime", lw=2))
    for k, (x, y) in enumerate(points):
        positive = point_labels is None or point_labels[k] == 1
        ax.scatter(x, y, c="lime" if positive else "red", marker="*", s=250, edgecolors="white")
    ax.set_title(title)
    ax.axis("off")


__all__ = [n for n in dir() if not n.startswith("_") and n not in ("pathlib", "time", "urllib", "zipfile")]
