# Vision: label with a foundation model, train your own segmenter

A mobile robot shares a sidewalk or a factory floor with people. Its perception has to tell the
planner **which pixels are people**, so it can slow down, keep its distance, or stop. A box is
not enough: the robot needs to know where the person ends and the free floor begins.

Pixel labels are expensive: a polygon around one person takes about a minute, a box a few
seconds. So you let a big foundation model (**SAM 2.1**) turn cheap prompts into masks, and train
a small, fast model (**YOLO**) on them that could run on the robot. Then you check whether that
was a good idea.

The data: **Penn-Fudan**, 170 street photos with a human-drawn mask for every person. We treat the
human masks as the truth: 120 images to train on, 50 to test on.

No model code is handed out beyond the helpers, and coding agents are allowed. The human part is
judging the labels and **writing down your prediction before every experiment**. Keep these
predictions in your notebook, next to the result.

What you get: [`vision.py`](vision.py) with the plumbing (data, SAM, YOLO dataset, metrics,
plotting), and three notebooks in [`notebooks/`](notebooks/): `00_data` to look at the data,
`01_label_and_train` with the setup for tasks 1-4, and `02_your_object` for task 5.

Tasks 0-4 Basic take about 2 h 25 min. Advanced items and task 5 are for when you have time.

## Task 0: Set up and look at the data (~15 min)
- open `00_data` on Colab or RunPod (see Hints) and run it
- look at the human masks: where would *you* hesitate if you had to label them?

## Task 1: SAM as a labeling tool (~25 min)
Basic:
- **first write down your guess**: which prompt gives the best mask, one click, a few clicks, or
  a box?
- pick 3-5 people from different images. Prompt SAM with one click, then with a box, and
  compare each mask with the human mask (IoU)
- find a click that makes SAM segment the *wrong* thing (a bag, a shirt, two people). Fix it with more clicks, positive and negative

Advanced:
- real boxes are sloppy. Enlarge or shift the boxes by 10% and 25%: how robust is SAM?
- how many clicks does it take on average to reach IoU 0.9?

## Task 2: Label the training set (~30 min)
Basic:
- turn the human *boxes* of all 120 training images into SAM masks: these are your labels
- guess first, then measure: the mean IoU of your labels against the human masks
- look at the 5 worst images. Who is wrong, SAM or the human?
- label the same images with the smaller `sam2.1-hiera-tiny`. Compare it with `base-plus`: mean
  IoU, seconds per image, and the masks side by side where the two disagree most. Which would you
  use to label 100 000 images?

## Task 3: Train your own YOLO, and a U-Net (~55 min)
Basic:
- write your SAM labels as a YOLO dataset and fine-tune `yolo11n-seg` (30 epochs, ~2-3 min on a
  T4)
- measure it on the 50 test images against the human masks
- **guess first**: how much better is the same YOLO trained on the *human* masks? Then train it
  and see
- look at test images with several people. What can a robot do with YOLO's output (one mask per
  person) that "these pixels are person" cannot give it?
- YOLO is an *instance* segmenter: one mask per person. Train a *semantic* one on the same SAM
  labels: `UNetSegmenter` from `vision.py`, a U-Net with a ResNet-18 encoder (the notebook
  explains both). Then compare SAM (with the human boxes), YOLO and the U-Net on the test images:
  IoU, `person_recall`, ms per image, and the masks side by side
- **guess first**: how much did the pretrained checkpoints (YOLO on COCO, the U-Net's encoder on
  ImageNet) give you? Train both again from random weights (`yolo11n-seg.yaml` instead of `.pt`,
  `UNetSegmenter(encoder_weights=None)`) and compare

Advanced:
- learning curve: train on 15, 30, 60 and 120 images. Where does it flatten?
- write the U-Net training loop yourself instead of `UNetSegmenter.fit`

## Task 4: Is it ready for the robot? (~20 min)
Basic:
- a robot's perception-planning-control loop runs at 10-30 Hz. Measure milliseconds per image for SAM and for your YOLO. Which one could sit in the loop?
- IoU hides what matters for safety. Measure `person_recall` (how many people are found at all) at confidence 0.1, 0.25 and 0.5. Which threshold would you use for a safety stop, and what does it cost you?
- look at the people your model misses. What do they have in common?

Advanced:
- export your YOLO to ONNX (`model.export(format="onnx")`) and time it on the CPU: a robot without a GPU
- turn the masks into a decision: stop if a person is taller than 60% of the image (close to the camera). Compare the decisions from your model with those from the human masks: how many needed stops does it miss, how many stops are for nothing?

## Task 5: Your own object (optional)
Basic:
- the notebook is set up for your **laptop** (prompt `"a laptop."`). Another object a robot of
  this course could have to find works too: a tool, a part, a cup
- take 30-50 photos of it with your phone: different backgrounds, angles, distances, lighting. Keep 10 photos from a place you did *not* use for the others as the test set
- label them in `02_your_object` with a text prompt: Grounding DINO, an open-vocabulary detector,
  turns the words into boxes, SAM turns the boxes into masks.
  Check every label by eye and drop the bad ones
- train YOLO on your object and try it on the test photos. Where does it fail?

Advanced:
- how many photos did you really need? Train on half
- the test labels also came from SAM. How sure are you of your test numbers?
- a laptop is a COCO class: how well does the untrained `yolo11n-seg.pt` already find it?

## Report
Each pair adds one row per model to the [class results table](TODO-link): labels (SAM / human),
model, training images, test IoU, `person_recall` at your chosen threshold, ms per image, GPU.

## Hints
- Work on **Google Colab** (`Runtime -> Change runtime type -> T4 GPU`) or a **RunPod** GPU pod: step by step in [`RUNPOD.md`](RUNPOD.md). A CPU works for tasks 0-2, but training is slow.
- In each notebook, the first cell installs the packages and fetches `vision.py` if it is not next to the notebook. Locally or on RunPod, clone this repo instead and open the notebooks from `vision/notebooks/`.
- Downloads on first use: Penn-Fudan ~50 MB, SAM 2.1 base-plus ~300 MB, YOLO ~6 MB, Grounding DINO tiny ~700 MB (task 5 only).
- `train_yolo(yaml, name)` from `vision.py` fine-tunes YOLO and returns the model. The weights are in `runs/<name>/weights/last.pt`: load them again later with `YOLO("runs/<name>/weights/last.pt")` (`from ultralytics import YOLO`).
- It trains with `val=False`: the test images stay untouched, and you measure them yourself with `mean_iou` and `person_recall`.
- Ultralytics (YOLO) is AGPL-3.0: fine for this lab, check the license before you ship it in a product.
- Stuck? See [`sol/HINTS.md`](sol/HINTS.md).
