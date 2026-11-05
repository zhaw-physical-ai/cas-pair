# IMU gestures: supervised learning with your phone

Your phone's accelerometer and gyroscope record a 2 s gesture: **left, right, up, down, circle,
idle**. The whole class pools its recordings. In pairs you train and compare classifiers, from
a random forest to a small CNN.

No model code is handed out, and coding agents are allowed. The human part is the data:
collecting it, checking it, and **writing down your prediction before every experiment**. Keep
these predictions in your notes, next to the result.

What you get: [`load.py`](load.py), which turns the class export into arrays.

## Task 0: Collect (pairs, ~25 min)
1. Scan the QR code on the projector, or open the link, on your phone. Enter your name, the same
   every time.
2. One person performs, the other watches the plot after each take and deletes bad ones with
   **Delete my last take**. Then swap.
3. **15 reps per gesture per person.** Hold the phone upright, screen facing you, with the same
   grip every take. Vary your speed a bit.
4. The rep counter on each gesture button and the dashboard on the projector show your progress.

iPhone: tap **Record** and allow motion access when asked. If the page shows no sensor data,
use the phyphox fallback at the bottom of the page.

## Task 1: Baseline
Basic:
- load the pooled data, then plot a few takes per gesture and per person
- train a logistic regression and a random forest on `features(X)`, and a k-nearest-neighbor
  classifier (kNN) on the standardized features

## Task 2: Split matters
Basic:
- **first write down your guess** of the accuracy for both splits
- compare a random train/test split with leave-one-person-out (group by person)
- for each test take, find whose recording its nearest neighbor is. How often is it the same
  person, under each split?
- explain the gap

## Task 3: How much data
Basic:
- learning curve over reps per gesture: train on 1, 2, 5, 10, 15 reps per person and gesture
- learning curve over the number of people in training
- which helps more? Guess first

## Task 4: Neural nets
Basic:
- before the neural nets, kNN as a reference:
  - sweep k (1, 3, 5, 15, 50) and plot train vs validation accuracy
  - compare unscaled vs standardized features
  - compare kNN on the raw window (Euclidean) with kNN on the features
  - try other distances: Manhattan, cosine, one that ignores how the phone is held (only |acc|
    and |gyro|), dynamic time warping (DTW: tolerates different speeds), and a learned one
    (NCA). Which fits gestures best, and why?
- train an MLP on the raw window, then a 1D CNN
- plot train and validation loss
- make the model overfit on purpose
- fix it with dropout, weight decay, early stopping or augmentation: noise, time shift, random
  3D rotation (phone orientation varies between people). Which helps most?

## Task 5: Label noise
Basic:
- flip 10%, 20% and 40% of the training labels at random and measure the effect

## Advanced (pick one per pair)
- **Sequence models:** an LSTM/GRU or a small transformer. Does it beat the CNN? At what data
  size?
- **LLM zero-shot / few-shot:** send the signal as text (downsampled, rounded) to an LLM and ask
  for the gesture. Then add a few labeled examples to the prompt. Compare accuracy and latency
  with your CNN, and with kNN given the same few examples per class.
- **VLM:** plot the window as an image and ask a vision-language model to classify it.

## Report
Each pair adds one row to the [class results table](TODO-link): model, split, accuracy on
leave-one-person-out, number of training samples.

## Hints
- Work on your laptop or a RunPod pod. A CPU is enough for everything here.
- Set up the environment:
  ```
  mkdir -p ~/repos/cas_26_YOUR_NAME/gestures && cd ~/repos/cas_26_YOUR_NAME/gestures
  uv init && uv add numpy scikit-learn matplotlib torch
  # copy load.py from this repo into this folder
  ```
- Load the data with the export link from the projector:
  ```python
  from load import load, features, GESTURES
  X, y, person = load("https://<server>/api/export?t=<token>")   # X: (N, 100, 6)
  ```
  `uv run python load.py <link>` prints how many takes each person has. Check yours are there.
- Channels: acc x, y, z (m/s², including gravity), then gyro x, y, z (rad/s), at 50 Hz.
  x is to the right of the screen, y up, z out of the screen.
- New takes keep arriving during class. Download the zip once
  (`curl -o gestures.zip "<link>"`) and use `load("gestures.zip")`, so your numbers stay
  comparable.
- Stuck? See [`sol/HINTS.md`](sol/HINTS.md).
