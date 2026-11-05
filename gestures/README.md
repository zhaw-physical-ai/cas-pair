# IMU gestures

Supervised learning with your phone. The class records 2 s gestures (left, right, up, down,
circle, idle) with the phone's accelerometer and gyroscope. Then pairs train and compare
classifiers on the pooled data, from kNN and random forests to small neural nets.

No robot, no Jetson: a phone and a laptop are enough.

## Start here
1. **Record.** Scan the QR code on the projector with your phone, enter your name, and record
   15 takes per gesture.
2. **Read the tasks:** [`GESTURES-TASK-DESCRIPTION.md`](GESTURES-TASK-DESCRIPTION.md).
3. **Load the data** with [`load.py`](load.py), the only code you get:
   ```
   uv init && uv add numpy scikit-learn matplotlib torch
   curl -o gestures.zip "<export link from the projector>"
   ```
   ```python
   from load import load, features
   X, y, person = load("gestures.zip")   # X: (N, 100, 6), 2 s at 50 Hz, acc xyz + gyro xyz
   ```

## What is here

| | |
|---|---|
| [`GESTURES-TASK-DESCRIPTION.md`](GESTURES-TASK-DESCRIPTION.md) | the tasks, basic and advanced |
| [`load.py`](load.py) | loads the class export into arrays; `features(X)` for a tabular start |
| [`sol/HINTS.md`](sol/HINTS.md) | hints per task, for when you are stuck |
| [`collector/`](collector/) | the recording server and phone page (run by the instructor) |

Write down your prediction before every experiment. That part is not optional.
