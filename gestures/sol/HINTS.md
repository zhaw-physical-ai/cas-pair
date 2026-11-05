# Hints: IMU gestures

Short pointers, not solutions. Ask your coding agent for the code, then check that it does what
these hints say.

## Task 1: Baseline
- `features(X)` gives 30 numbers per take; `FEATURE_NAMES` names them. Logistic regression needs
  `StandardScaler` first; a random forest does not.
- Plot: `plt.plot(np.arange(100) / 50, X[i])`, one subplot per gesture, a few takes each. Look
  for takes that are flat, clipped, or plainly a different gesture.
- kNN: `make_pipeline(StandardScaler(), KNeighborsClassifier(5))`. Without the scaler, the
  acceleration features (energy ~100) swamp the gyro features (~0.1) in the distance.
- `sklearn.metrics.ConfusionMatrixDisplay`: which gestures get confused? If left/right or
  up/down get mixed up: a left move speeds up to the left, then brakes to the right. Which of the
  30 features know what came first?

## Task 2: Split matters
- Random split: `train_test_split(..., stratify=y)`.
- Per person: `LeaveOneGroupOut()` or `GroupKFold(n_splits=5)` with `groups=person`, passed to
  `cross_val_score`.
- Whose neighbor? `NearestNeighbors(n_neighbors=1).fit(F_train)`, then `.kneighbors(F_test)` gives
  indices into the training set; compare `person[train][idx]` with `person[test]`.
- Why the gap? The same person's takes are similar: same grip, speed and phone. A random split
  puts some of each person's takes in the test set, so the model can recognize the person
  instead of the gesture.

## Task 3: How much data
- Keep the test people fixed (e.g. `GroupKFold`). Shrink only the training set: take the first
  k reps of each (person, gesture), or a random subset of the training people.
- Plot accuracy against the number of training takes for both curves, on the same axes.

## Task 4: Neural nets
- Normalize each channel with the training mean and std.
- PyTorch wants (N, channels, time): `X.transpose(0, 2, 1)`.
- MLP: flatten (600 inputs) → 128 → ReLU → 6.
- Minimal 1D CNN:
  ```
  Conv1d(6, 32, k=5, padding=2) → ReLU → MaxPool1d(2)
  Conv1d(32, 64, k=5, padding=2) → ReLU → AdaptiveAvgPool1d(1) → Flatten → Linear(64, 6)
  ```
- Validation set: hold out whole **people**, not random takes, or you measure the Task 2 leak.
- Overfit on purpose: few training people, a wide model, many epochs, no regularization. The
  training loss goes to ~0 while the validation loss turns back up.
- Fixes:
  - `Dropout(0.3)` before the last layer
  - `AdamW(weight_decay=1e-2)`
  - keep the weights from the epoch with the lowest validation loss (early stopping)
- Augmentation, applied to each training batch on the fly:
  - noise: `x + 0.05 * std * randn`
  - time shift: `torch.roll` by ±10 samples
  - random 3D rotation, the same matrix R applied to the acc triplet and to the gyro triplet;
    `scipy.spatial.transform.Rotation.random()` or a small random angle about a random axis.
    This simulates a different grip.

## Task 4: kNN distances
- `KNeighborsClassifier(metric="manhattan")`, also `"cosine"` and `"chebyshev"`. Standardize first.
- Ignore the grip: per time step, `np.linalg.norm(X[..., :3], axis=-1)` and the same for gyro.
  Rotating the phone does not change these two numbers.
- DTW: lets one take run faster or slower than the other. Downsample to 25 Hz (`X[:, ::2]`) and
  limit the warp to ±10 steps (a Sakoe-Chiba band), or it is slow. `tslearn.metrics.cdist_dtw`
  computes it; then `KNeighborsClassifier(metric="precomputed")`. With a band of 0, DTW is the
  Euclidean distance.
- Learned: `make_pipeline(StandardScaler(), NeighborhoodComponentsAnalysis(), KNeighborsClassifier())`.

## Task 5: Label noise
- Flip only the **training** labels: pick a random 10% of the indices and give each one a
  random *other* class. The test labels stay clean.
- Repeat with a few seeds; one run is noisy.

## Task 6: Live
- Export from PyTorch:
  ```python
  model.eval()
  torch.onnx.export(model, torch.zeros(1, 100, 6), "model.onnx", input_names=["x"],
                    output_names=["logits"], dynamic_axes={"x": {0: "n"}, "logits": {0: "n"}},
                    dynamo=False)
  ```
  The model must take raw `load()` units: store the training mean and std as buffers
  (`register_buffer`) and normalize in `forward`.
- Other inputs work too: `(N, 6, 100)`, flattened `(N, 600)`, another window length such as
  `(N, 50, 6)`, or the 30 features. A scikit-learn model on `features(X)`:
  ```python
  from skl2onnx import to_onnx          # uv add skl2onnx
  onx = to_onnx(clf, F[:1].astype(np.float32), options={id(clf): {"zipmap": False}})
  open("model.onnx", "wb").write(onx.SerializeToString())
  ```
  If you used a scaler, export the whole pipeline. Labels: `",".join(clf.classes_)` (alphabetical).
- The label order on the upload page is the order of your model's outputs. `np.unique(y)` and
  scikit-learn sort the labels alphabetically: `circle,down,idle,left,right,up`.
- Check before uploading: `onnxruntime.InferenceSession("model.onnx").run(None, {"x": X[:5]})`
  should match your PyTorch output.
- The live page sends a gesture only when the same label wins several windows in a row with
  enough confidence (both settings are on the page), and never `idle`.
- Misfires: training windows are centred on the motion, live windows slide. Train with random
  time shifts of ±30 samples (pad with the edge values).

## Advanced
- LSTM/GRU: input (N, T, 6) with `batch_first=True`; classify from the last hidden state or the
  mean over time. Downsampling to 25 Hz makes training faster.
- LLM: `np.round(X[i, ::5], 1)`, i.e. 20 time steps × 6 channels, as a small CSV in the prompt.
  Ask for exactly one word from the label list. For few-shot, use examples from *other* people
  than the test take. Measure seconds per prediction too.
- VLM: one figure per take with fixed axis limits, the same for all takes, and the channel names
  in the legend.
