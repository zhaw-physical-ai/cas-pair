# LeRobot installation from HuggingFace

https://huggingface.co/docs/lerobot/en/installation

#ATTENTION: use uv (not conda)

Create folder for your project e.g.:
```
mkdir -p ~/repos/cas_26_YOUR_NAME/lerobot
cd ~/repos/cas_26_YOUR_NAME/lerobot
```


Install python env and source:
```
uv python install 3.12
uv venv --python 3.12

source .venv/bin/activate
```

Additional packages needed:
```
sudo apt install ffmpeg
```

Install relevant packages
```
uv pip install lerobot[feetech,core_scripts]
```

Maybe needed later:
```
uv pip install 'lerobot[dataset]'      
uv pip install 'lerobot[training]'   
uv pip install 'lerobot[hardware]'   
uv pip install 'lerobot[viz]'   
```


# SO-101 - getting it to run
https://huggingface.co/docs/lerobot/en/so101
- power the robot arm
- connect your follower robot to your jetson

## Find ports of robot
```
lerobot-find-port
```

give access:
```
sudo chmod 666 /dev/ttyACM0
sudo chmod 666 /dev/ttyACM1
```

### Permission to use the USB ports

The ports (`/dev/ttyACM*`) belong to the `dialout` group. Add yourself once:

```bash
sudo usermod -aG dialout $USER
newgrp dialout
```


## Setup Motor ids and baudrate for leader and follower 
thus should be already done with the shipped arms. If however something fails do this step.

```
lerobot-setup-motors \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM0  # <- paste here the port found at previous step
```

## Calibrate both arms
see helping videos on https://huggingface.co/docs/lerobot/en/so101
```
# change the port if needed
lerobot-calibrate --robot.type=so101_follower --robot.port=/dev/ttyACM0 --robot.id=my_awesome_follower_arm
lerobot-calibrate --teleop.type=so101_leader  --teleop.port=/dev/ttyACM1 --teleop.id=my_awesome_leader_arm 
```
successful output, e.g.:
```
Calibration saved to /home/ema-student/.cache/huggingface/lerobot/calibration/robots/so_follower/my_awesome_follower_arm.json
```



# Teleoperate
from https://huggingface.co/docs/lerobot/en/il_robots

```
lerobot-teleoperate \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM0 \
    --robot.id=my_awesome_follower_arm \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttyACM1 \
    --teleop.id=my_awesome_leader_arm
```

# add camera
from: https://huggingface.co/docs/lerobot/en/cameras

```
lerobot-find-cameras opencv
```


teleoperate with camera:
```
lerobot-teleoperate \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM0 \
    --robot.id=my_awesome_follower_arm \
    --robot.cameras="{front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}}" \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttyACM1 \
    --teleop.id=my_awesome_leader_arm \
    --display_data=true
```

# Imitation Learning
from: https://huggingface.co/docs/lerobot/en/il_robots?teleoperate_koch_camera=Command


create access token to load your recorded dataset up to huggingface:
https://huggingface.co/settings/tokens

```
export HUGGINGFACE_TOKEN=xxxxx
```
```
hf auth login --token ${HUGGINGFACE_TOKEN} 
```
output e.g.
token saved to /home/ema-student/.cache/huggingface/stored_tokens

```
HF_USER=$(NO_COLOR=1 hf auth whoami | awk -F': *' '/user:/ {print $2}')
echo "$HF_USER"
```

- Record simple dataset:

Rules on gathering quality data: https://huggingface.co/blog/lerobot-datasets#what-makes-a-good-dataset

```
lerobot-record \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM0 \
    --robot.id=my_awesome_follower_arm \
    --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30}}" \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttyACM1 \
    --teleop.id=my_awesome_leader_arm \
    --display_data=true \
    --dataset.repo_id=${HF_USER}/record-test \
    --dataset.num_episodes=5 \
    --dataset.single_task="Grab the black cube" \
    --dataset.streaming_encoding=true \
    --dataset.encoder_threads=2
```

- Replay one episode of dataset:
```
lerobot-replay \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM0 \
    --robot.id=my_awesome_follower_arm \
    --dataset.repo_id=${HF_USER}/record-test_YOUR_SPECIFIC_FILE \ # find it under .cache/huggingface/lerobot/YOURACCOUNT/...
    --dataset.episode=0 # choose the episode you want to replay
```


- Train a policy (not recommended on jetson - use GPU server like runpod)

uv pip install 'lerobot[training]'

```
lerobot-train \
  --dataset.repo_id=${HF_USER}/so101_test_YOURPATH \
  --policy.type=act \
  --output_dir=outputs/train/act_so101_test \
  --job_name=act_so101_test \
  --policy.device=cuda \
  --wandb.enable=true \
  --policy.repo_id=${HF_USER}/my_policy
```


What helps to run a bigger load on the jetson:
- turn off screen
```
sudo systemctl isolate multi-user.target
```

to bring it up again
sudo systemctl set-default graphical.target
sudo reboot

tune parameters like batch size, workers, ....


# Troubleshooting
Helpful troubleshooting tips:
https://docs.nvidia.com/learning/physical-ai/sim-to-real-so-101/latest/troubleshooting.html


If you encounter build errors, you may need to install additional system dependencies: cmake, build-essential, and ffmpeg libs. To install these for Linux run:

```
sudo apt-get install cmake build-essential python3-dev pkg-config libavformat-dev libavcodec-dev libavdevi
```