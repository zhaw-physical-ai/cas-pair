# Hints: vision

Short pointers, not solutions. Ask your coding agent for the code, then check that it does what
these hints say.

## Task 0: Setup
- Colab: `File -> Open notebook -> GitHub`, paste this repo's URL, pick `vision/notebooks/...`.
  Then `Runtime -> Change runtime type -> T4 GPU` **before** you run anything.
- `device: cpu` on Colab means you forgot the GPU runtime.
- `transformers` prints that a `sam2_video` checkpoint is loaded into `Sam2Model`. That is
  expected: SAM 2.1 checkpoints contain the video parts too, and we use only the image parts.
- Everything downloaded lives in the runtime. A new Colab runtime starts empty, so the first cell
  downloads again.

## Task 1: SAM as a labeling tool
- One person's human mask: `instances[i] == pid`. Its box: `boxes_from_instances(instances[i])`
  gives the boxes in the order of the ids 1, 2, ...
- A click is `[x, y]` in pixels, x to the right, y down. `ys, xs = np.nonzero(mask)` gives every
  pixel of the person; `np.median` of them is a click near the centre.
- `sam(image, points=[[x, y]])` is one object with one click. Several clicks for the same object:
  `points=[[x1, y1], [x2, y2]], point_labels=[1, 0]` (1 = part of it, 0 = not part of it).
- Wrong objects: click on a bag, a jacket, or where two people overlap.
- Sloppy boxes: grow each side by `f * width` and `f * height`, clip to the image. Shift: add
  `f * width` to both x.
- `show(ax, image, mask, boxes=..., points=..., point_labels=...)` draws all of it.

## Task 2: Label the training set
- One SAM call per image with all its boxes: `sam(images[i], boxes=boxes_from_instances(...))`
  returns one mask per box. Keep the `(n, H, W)` masks per image: YOLO needs one mask per
  person, `masks.any(0)` is the "any person" mask for IoU.
- Mean IoU against `instances[i] > 0`. `np.argsort` of the IoUs gives the worst images first.
- Typical disagreements: bags and umbrellas (human: part of the person, SAM: not), hair, gaps
  between legs, small people in the background that nobody labeled.
- Model sizes: `SamLabeler("facebook/sam2.1-hiera-tiny")`. Time it with `time.time()` around
  the labeling loop. Keep `sam` (base-plus): task 3 uses it again; `del sam_tiny` when done.
- Where the two disagree: `iou(base_masks.any(0), tiny_masks.any(0))` per image, smallest first.
  A scatter plot of the two IoUs against the human masks shows it at a glance.

## Task 3: Train your own YOLO
- `write_yolo_dataset(folder, images, masks)` with `masks` a list of `(n, H, W)` arrays, one per
  image. Human labels: `instances_to_masks(instances[i])`.
- Use different folders and run names for SAM and human labels, or the second run overwrites
  the first.
- Training on a T4: ~2-3 min for 30 epochs at `imgsz=640`. Ultralytics prints a lot; the line to
  look for is the loss going down.
- Evaluate: `yolo = train_yolo(yaml, name)` returns the trained model; then
  `mean_iou(lambda im: yolo_predict(yolo, im)[0].any(0), test_images, test_instances)`.
  To call Ultralytics yourself, pass an absolute `project` path: a relative one ends up under
  `runs/segment/`.
- Expect both YOLOs to land close to each other. If the human-label one is much better, check
  your SAM masks; if much worse, check that you wrote the right masks.
- Several people: `yolo_predict` returns one mask and one box per person. A robot can count them,
  follow each one over time (tracking), and estimate where each one stands on the floor.
- Learning curve: `train[:15]`, `train[:30]`, ... Keep the test set fixed.
- U-Net: `UNetSegmenter().fit(images, masks)` with one `(H, W)` mask per image: the SAM labels
  merged, `m.any(0)`. ~30 s on a T4. `unet(image)` returns an `(H, W)` bool mask, so it plugs
  into `mean_iou`, `person_recall` and `seconds_per_image` like the YOLO lambda.
- SAM in the comparison: label the test images with their human boxes once, and look the masks
  up in the `predict` function. Its time is the one from task 2. Say in your table that it needs
  the boxes.
- U-Net behind YOLO is expected: it works at 256 x 256 and gives one blob for people who touch.
- Random weights: `train_yolo(yaml, name="scratch", model="yolo11n-seg.yaml", pretrained=False)`
  builds the same network from its architecture file, with no checkpoint. Use a new `name`, or it
  overwrites your pretrained run. `UNetSegmenter(encoder_weights=None)` does the same for the
  U-Net. Same labels and epochs, so only the starting point differs.
- From scratch, 120 images and 30 epochs are far too little: expect a big drop. That gap is what
  the checkpoint is worth.

## Task 4: Ready for the robot?
- `seconds_per_image(predict, images)` does a warm-up call first: the first call is always slow.
  For SAM, time the labeling of one image with its boxes; and remember that someone had to draw
  those boxes.
- `person_recall(predict, images, instances)` returns the recall and the list of
  `(image index, person id)` it missed. Plot a few of them.
- Lower confidence finds more people, but also predicts people where there are none. Count the
  predicted pixels outside every human mask to see that cost.
- ONNX: `yolo.export(format="onnx")` writes a `.onnx` next to the weights; `YOLO("...onnx")`
  loads it like a `.pt`. Time it with `device="cpu"` in `yolo_predict`.
- Stop rule: a person's height in pixels is `np.ptp(np.nonzero(mask.any(1))[0])`, for each of
  the per-person masks from `yolo_predict` and from `instances_to_masks`. Compare the rule on
  your predictions with the rule on the human masks. "Any person pixel in the bottom third" does
  not work here: in Penn-Fudan almost everyone is photographed full-length.

## Task 5: Your own object
- Colab: zip your photos, upload the zip in the file panel (left), then
  `!unzip -q photos.zip -d my_photos`. RunPod: drag the files into the Jupyter file browser.
- Text prompt: lower case, one noun phrase, end with a period: `"a laptop."`. If it finds
  too much or too little, change `threshold` (0.2-0.5) or the words (`"an open laptop."`).
- One object per photo is the easy case: keep only the box with the highest score.
- Review every label in a grid with its index in the title; keep a list of indices to drop. This
  is the human part of the pipeline.
- `write_yolo_dataset(..., name="laptop")` sets the class name.
- Untrained YOLO: `YOLO("yolo11n-seg.pt").predict(image, classes=[63])` keeps only COCO's
  laptops (`model.names[63]`).
- The 10 test photos from a different place tell you whether the model learned the object or the
  background.
