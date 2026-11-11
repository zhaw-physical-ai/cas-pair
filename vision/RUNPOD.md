# Running the vision lab on RunPod

RunPod rents you a GPU machine (a **pod**) by the second. You open Jupyter in your browser and
run the notebooks there, like on Colab, but nobody takes the GPU away from you after an hour.

## What you need

| | |
|---|---|
| GPU | any NVIDIA GPU with **16 GB** or more. The lab needs less than 8 GB at peak; 16 GB leaves room. Good choices: **RTX A4000**, **RTX 4000 Ada**, **L4**, **RTX 4090** |
| Template | the official **Runpod PyTorch 2.x** template: Jupyter is already in it |
| Disk | the template's defaults are plenty: the lab writes < 2 GB (packages ~0.2 GB, models ~1.2 GB, data and runs ~0.2 GB). Keep a **volume disk** (10 GB is enough) at `/workspace`: it keeps your notebooks and trained models when the pod stops |
| Time | ~2.5 h for tasks 0-4 at your own pace. Of that, the GPU is busy for ~20-30 min |
| Cost | ~$0.20-0.45 per hour on Community Cloud for the GPUs above, so roughly **$1** for the lab. Prices change: see [runpod.io/pricing](https://www.runpod.io/pricing) |

A bigger GPU (A100, H100) does not make the lab noticeably faster: the models are small, and most
of the time goes into your thinking and Python code, not the GPU.

## Step by step

### 1. Account
If you do not have one yet, register and join the course team as described in
[RunPod Registration](../so101/SO-101-TASK-DESCRIPTION.md#runpod-registration). The course pays for
the credits.

### 2. Deploy a pod
1. In the [RunPod console](https://console.runpod.io), go to **Pods → Deploy**.
2. Pick **Community Cloud** (cheaper) and a GPU from the table above. If it shows no free GPU,
   pick another one from the list.
3. Under **Template**, choose **Runpod PyTorch 2.x** (the newest version). For an RTX 50xx GPU
   take a template with CUDA 12.8 or newer.
4. Click **Edit Template**. Leave the disk sizes as they are, but check that there is a **Volume
   Disk** (10 GB or more, mounted at `/workspace`) and that **HTTP port 8888** is in the list:
   that is Jupyter.
5. Give the pod a name with your name in it, e.g. `vision-your-name`, and click **Deploy
   On-Demand**. It starts in 1-3 minutes.

### 3. Open Jupyter
1. On the **Pods** page, open your pod and click **Connect**.
2. Under **HTTP Services**, click **Jupyter Lab** (port 8888). If it says *Not Ready*, wait a
   minute and refresh.
3. If it asks for a password or token, it is in the pod's **Logs**.

### 4. Get the lab
In Jupyter, open **File → New → Terminal** and run:
```
cd /workspace
git clone https://github.com/zhaw-physical-ai/cas-pair.git
nvidia-smi
```
`nvidia-smi` shows your GPU and its memory. In the file browser on the left, open
`cas-pair/vision/notebooks/00_data.ipynb` and pick the **Python 3** kernel.

The first cell of every notebook installs the missing packages (`transformers`, `ultralytics`,
`segmentation-models-pytorch`, ~1 min) and prints `device: cuda`. If it prints `device: cpu`, the
pod has no GPU: deploy a new one.

### 5. Work
- Run `00_data`, then `01_label_and_train`, as in the [task description](VISION-TASK-DESCRIPTION.md).
- The data and your training runs go into the notebook's folder, on the volume. The packages and
  the SAM / Grounding DINO weights go to the container disk: after a stop they download again on
  first use (~1 GB, about a minute).
- Watch the GPU from the terminal with `nvidia-smi` (or `watch -n 1 nvidia-smi`).
- Task 5: drag your photos (or a zip) from your computer into the Jupyter file browser. Unzip in
  the terminal with `unzip photos.zip -d my_photos`.

### 6. Stop, or terminate
A running pod costs money even when you do nothing.
- **Stop** when you take a break or come back another day: the GPU is released and the
  `/workspace` volume stays (it costs a few cents per day). Starting again may give you a
  different GPU of the same type, or none if they are all busy.
- **Terminate** when you are done: everything is deleted. Before that, download what you want to
  keep (right-click a file in Jupyter → **Download**), or push it to your own Git repository.

## If something does not work
- **No GPU available** for the type you chose: pick another type from the table, or Secure Cloud.
- **Jupyter does not open**: wait a minute, refresh; else restart the pod from its menu.
- **`CUDA out of memory`**: restart the kernel (**Kernel → Restart**), then run the cells again.
  In task 2, `del sam_tiny` when you are done with it.
- **Disk full** (`No space left on device`): check with `df -h`. The lab needs < 2 GB, so
  something else filled it, often old training runs: delete `runs/` folders you do not need.
- **`git clone` asks for a password**: you typed the URL wrong; the repository is public.

## Estimated GPU use per notebook
Estimates from a run of the solution notebooks on an Apple laptop GPU (not yet on RunPod); expect
a similar order on an RTX A4000 or L4, and faster on a 4090.

| Notebook | GPU time | Peak GPU memory | What runs |
|---|---|---|---|
| `00_data` | < 1 min | none | loads the data |
| `01_label_and_train` | ~20 min | < 8 GB | SAM 2.1 base-plus and tiny on 120 images, 3 YOLO trainings (~3 min each), 2 U-Nets (~30 s each), ONNX export |
| `02_your_object` | ~5 min | < 8 GB | Grounding DINO + SAM on your photos, 1 YOLO training |
