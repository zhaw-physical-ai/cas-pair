# IMU gestures

Supervised learning with your phone. The class records 2 s gestures (left, right, up, down,
circle, idle) with the phone's accelerometer and gyroscope. Then pairs train and compare
classifiers on the pooled data, from kNN and random forests to small neural nets.

No robot, no Jetson: a phone and a laptop are enough.

## Start here
1. **Record.** Scan the QR code on the projector with your phone, enter your name, and record
   15 takes per gesture.
2. **Read the tasks:** [`GESTURES-TASK-DESCRIPTION.md`](GESTURES-TASK-DESCRIPTION.md).
3. **Set up** a folder with [`load.py`](load.py) and the notebooks, and download the class data:
   ```
   mkdir -p ~/repos/cas_26_YOUR_NAME/gestures && cd ~/repos/cas_26_YOUR_NAME/gestures
   uv init && uv add numpy scikit-learn matplotlib torch jupyterlab
   # copy load.py and notebooks/*.ipynb from this repo into this folder
   curl -o gestures.zip "<export link from the projector>"
   uv run jupyter lab
   ```
4. **Work through the notebooks:** [`00_data`](notebooks/00_data.ipynb) to look at the data, then
   [`01_classical`](notebooks/01_classical.ipynb) for tasks 1, 2, 3 and 5. For task 4 and the
   advanced tasks, start your own notebook from the same `load()` call.
5. **Optional, task 6:** upload your model and try it live on your phone, steering a simulated
   SO-101 arm in your browser.

## What is here

| | |
|---|---|
| [`GESTURES-TASK-DESCRIPTION.md`](GESTURES-TASK-DESCRIPTION.md) | the tasks, basic and advanced |
| [`load.py`](load.py) | loads the class export into arrays; `features(X)` for a tabular start |
| [`notebooks/`](notebooks/) | `00_data` (complete) and `01_classical` (setup given, experiments yours) |
| [`sol/HINTS.md`](sol/HINTS.md) | hints per task, for when you are stuck |
| [`sim/`](sim/) | the simulated SO-101 arm your live gestures drive (task 6) |
| [`collector/`](collector/) | the server: phone page, upload, live page. Run by the instructor; to run your own, see [`collector/HOSTING.md`](collector/HOSTING.md) |

Write down your prediction before every experiment. That part is not optional.
