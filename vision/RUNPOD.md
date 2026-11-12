# Running the vision lab on RunPod

RunPod rents you a GPU machine (a **pod**) by the second. You open Jupyter in your browser and
run the notebooks there, like on Colab, but nobody takes the GPU away from you after an hour.

## What you need

| | |
|---|---|
| GPU | any NVIDIA GPU with **16 GB** or more. The lab needs less than 8 GB at peak; 16 GB leaves room. Good choices: **RTX A4000**, **RTX 4000 Ada**, **L4**, **RTX 4090** |
| Not this GPU | **Blackwell** cards (**RTX 50xx**, **RTX PRO … Blackwell**): YOLO crashed on an RTX PRO 4000 Blackwell, see [below](#if-something-does-not-work). The GPUs above are tested or an older, safe generation |
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
2. Pick **Community Cloud** (cheaper) and a GPU from the table above, not a Blackwell one. If it
   shows no free GPU, pick another one from the list.
3. Under **Template**, choose **Runpod PyTorch 2.x**, the newest version (marked *Current*), with
   its default tag.
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

### 4. Get the lab and check the GPU
In Jupyter, open **File → New → Terminal** and run:
```
cd /workspace
git clone https://github.com/zhaw-physical-ai/cas-pair.git
nvidia-smi --query-gpu=name,memory.total --format=csv
python -c "import torch, torchvision; b = torch.rand(10, 4, device='cuda'); b[:, 2:] += b[:, :2]; print(torchvision.ops.nms(b, torch.rand(10, device='cuda'), 0.5))"
```
- `nvidia-smi` shows your GPU and its memory.
- The `python` line runs the one GPU operation YOLO needs that the rest of the lab does not
  (`torchvision`'s NMS) on 10 random boxes. It prints `tensor([...], device='cuda:0')` when the
  GPU works for the whole lab. If it prints `no kernel image is available`, the installed
  `torchvision` has no code for this GPU (we saw that on a Blackwell card): terminate the pod and
  deploy one from the table.

In the file browser on the left, open `cas-pair/vision/notebooks/00_data.ipynb` and pick the
**Python 3** kernel. The first cell of every notebook installs the missing packages
(`transformers`, `ultralytics`, `segmentation-models-pytorch`, ~1 min) and prints `device: cuda`.
If it prints `device: cpu`, the pod has no GPU: deploy a new one. It also runs the NMS check from
above and prints `WARNING: YOLO will crash on this GPU` if it fails.

### 5. Work
- Run `00_data`, then `01_label_and_train`, as in the [task description](VISION-TASK-DESCRIPTION.md).
  Run a cell with `Shift+Enter`; `[*]` next to it means it is still running.
- The data and your training runs go into the notebook's folder, on the volume. The packages and
  the SAM / Grounding DINO weights go to the container disk: after a stop they download again on
  first use (~1 GB, about a minute).
- Watch the GPU from the terminal with `nvidia-smi` (or `watch -n 1 nvidia-smi`).

### 6. Task 5: your photos
`02_your_object` reads the photos from two folders **next to the notebook**, i.e. in
`cas-pair/vision/notebooks/`:

| Folder | What goes in |
|---|---|
| `my_photos/` | 30-50 photos of your object |
| `my_photos_test/` | ~10 photos taken in a different place |

- Create each folder with the **New Folder** button above the file browser, open it, and drag
  your photos in from your computer.
- Or make two zips, `train.zip` and `test.zip`, drag them into `notebooks/`, and unzip them in
  the terminal:
  ```
  cd /workspace/cas-pair/vision/notebooks
  unzip -j -q train.zip -d my_photos
  unzip -j -q test.zip -d my_photos_test
  ```
  `-j` drops the folders inside the zip: the notebook looks only directly in each folder.
- Only `.jpg`, `.jpeg` and `.png` are read.
### 7. Stop, or terminate
A running pod costs money even when you do nothing.
- **Stop** when you take a break or come back another day: the GPU is released and the
  `/workspace` volume stays (it costs a few cents per day). Starting again may give you a
  different GPU of the same type, or none if they are all busy.
- **Terminate** when you are done: everything is deleted. Before that, download what you want to
  keep (right-click a file in Jupyter → **Download**), or push it to your own Git repository.

## If something does not work

| What you see | Why | What to do |
|---|---|---|
| No free GPU of the type you chose | they are all rented | pick another type from the table, or Secure Cloud |
| Jupyter does not open | the pod is still starting | wait a minute, refresh; else restart the pod from its menu |
| `CUDA error: no kernel image is available for execution on the device`, right after YOLO's last epoch | the installed `torchvision` has no code for this GPU, so its NMS (used when YOLO validates and predicts) fails, while `torch` and the training work. Seen on an RTX PRO 4000 Blackwell (`torch` 2.13.0 / `torchvision` 0.28.0, both cu129). Not a missing package | terminate the pod and deploy one from the table |
| `CUDA out of memory` | models from earlier cells still on the GPU | **Kernel → Restart**, then run the cells again. In task 2, `del sam_tiny` when you are done with it |
| ONNX export: `requirements: ... not found, attempting AutoUpdate` and `Restart runtime` | Ultralytics installs `onnx`, `onnxruntime` and `onnxslim` itself the first time | nothing: the export continues and works. If it fails, run the same cell once more |
| `You are sending unauthenticated requests to the HF Hub` | the models come from Hugging Face without a login | nothing; slower downloads only |
| `You are using a model of type sam2_video to instantiate ... sam2` | SAM 2.1 checkpoints contain the video parts too; the lab uses the image parts | nothing |
| `02_your_object` finds `0 training photos` | wrong folder name or place, photos in a subfolder, or `.HEIC` files | see [Task 5: your photos](#6-task-5-your-photos) |
| `No space left on device` | something else filled the disk, often old training runs (the lab needs < 2 GB) | check with `df -h`; delete `runs/` folders you do not need |
| `git clone` asks for a password | the URL is mistyped; the repository is public | copy the URL from step 4 |

A red box under a cell is not always an error: warnings are red too. It is an error when it
ends with a `Traceback` and a line like `SomethingError: ...`.

## Estimated GPU use per notebook
`00_data` and both solution notebooks ran on an **RTX 4090** with the PyTorch 2.13 template (November
2026). The times below are estimates from an Apple laptop GPU; expect a similar order on an RTX
A4000 or L4, and faster on a 4090.

| Notebook | GPU time | Peak GPU memory | What runs |
|---|---|---|---|
| `00_data` | < 1 min | none | loads the data |
| `01_label_and_train` | ~20 min | < 8 GB | SAM 2.1 base-plus and tiny on 120 images, 3 YOLO trainings (~3 min each), 2 U-Nets (~30 s each), ONNX export |
| `02_your_object` | ~5 min | < 8 GB | Grounding DINO + SAM on your photos, 1 YOLO training |
