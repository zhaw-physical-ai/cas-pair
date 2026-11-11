# Vision

Label with a foundation model, train your own segmenter. SAM 2.1 turns cheap boxes and clicks
into pixel masks of people; you train a small YOLO on them and check whether it is good and fast
enough for a robot. Optionally, you do the same for an object you photograph yourself.

No robot, no Jetson: a browser with Google Colab or a RunPod GPU pod is enough.

## Start here
1. **Read the tasks:** [`VISION-TASK-DESCRIPTION.md`](VISION-TASK-DESCRIPTION.md).
2. **Open a notebook** on Colab (`File -> Open notebook -> GitHub`, this repo) with a T4 GPU, or
   clone the repo on a RunPod pod and open Jupyter (step by step: [`RUNPOD.md`](RUNPOD.md)). The
   first cell installs what is missing.
3. **Work through the notebooks:** [`00_data`](notebooks/00_data.ipynb) to look at the data,
   then [`01_label_and_train`](notebooks/01_label_and_train.ipynb) for tasks 1-4.
4. **Optional, task 5:** photograph your own object and train on it in
   [`02_your_object`](notebooks/02_your_object.ipynb).

## What is here

| | |
|---|---|
| [`VISION-TASK-DESCRIPTION.md`](VISION-TASK-DESCRIPTION.md) | the tasks, basic and advanced |
| [`RUNPOD.md`](RUNPOD.md) | how to run the notebooks on a RunPod GPU pod, and what it costs |
| [`vision.py`](vision.py) | data, SAM 2.1 labeler, text-prompt boxes, YOLO dataset writer, metrics, U-Net, plotting |
| [`notebooks/`](notebooks/) | `00_data` (complete), `01_label_and_train` and `02_your_object` (setup given, experiments yours) |
| [`sol/HINTS.md`](sol/HINTS.md) | hints per task, for when you are stuck |
| [`sol/`](sol/) | solutions: `01_label_and_train` and `02_your_object` notebooks |

Write down your prediction before every experiment. That part is not optional.
