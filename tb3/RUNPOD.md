# Running the TurtleBot3 lab on RunPod

RunPod rents you a GPU machine (a **pod**) by the second. This one runs a ROS 2 Jazzy desktop in
your browser, with a TurtleBot3 Burger in Gazebo Harmonic. It is the same image as the Summit
simulation: if you deployed that one, this is the same procedure with a different template.

If you have a RAP pod on the ZHAW cluster, you can use that instead: install the TurtleBot3
packages there with `sudo apt install ros-jazzy-turtlebot3-gazebo ros-jazzy-turtlebot3-teleop`
and continue at [step 5](#5-launch). The real robots (Task 3) are not reachable from RunPod.

## What you need

|          |                                                                                                                                                           |
| -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GPU      | any NVIDIA GPU: the image does not start without one. Tested on the **RTX PRO 4500 Blackwell SE**: `/scan` at 4.7 Hz, real-time factor about 96 % |
| Template | the course template, linked in [step 2](#2-deploy-a-pod). It installs the TurtleBot3 packages by itself                                                    |
| Disk     | a **volume disk** of 10 GB, mounted at `~/rap`: it keeps your package when the pod stops                                                          |
| Cost     | shown on the deploy page, per hour; you pay for every minute the pod runs. A stopped pod costs only its volume, about $2 per month for 10 GB              |

## Step by step

### 1. Account

If you do not have one yet, register and join the course team as described in
[RunPod Registration](../so101/SO-101-TASK-DESCRIPTION.md#runpod-registration). The course pays for
the credits.

### 2. Deploy a pod

1. Open the template, logged in to your own RunPod account, and click **Configure Pod**:
   https://console.runpod.io/hub/template/ew4zbalm4l?ref=vc5f9d3q
2. Enter a **Pod name** with your name in it, e.g. `tb3-your-name`. Click **Set overrides** next
   to the template, change `PASSWD` from `change-me` to your own password, then **Set
   overrides** ([screenshots](../summit/SUMMIT-SIM.md#open-the-desktop), steps 2-5).
3. Choose a GPU. Any available NVIDIA card works. On the right, check the cost per hour.
4. Under **Storage**, click **Add volume** → **Create volume** → **Volume disk**, 10 GB →
   **Add volume disk**. Without it nothing in the pod is kept.
5. Check that the breakdown on the right lists a **Volume disk cost**, then click **Deploy
   Pod**. The first start takes a few minutes.

### 3. Open the desktop

1. Under **Connect**, wait for **Ready** next to port 8080, click **browser desktop**, then
   **Connect**.
2. Log in with your password from step 2.

In the noVNC side tab, ⚙ Settings → Scaling mode → **Remote resizing** makes the desktop fill
the browser window.

### 4. Wait for the TurtleBot3 packages

Open a terminal (the `$_` icon in the dock). The packages install in the background during the
first 1-2 minutes after every start; until they are done, every new terminal says so. Watch it
with:

```
tail -f /tmp/tb3-install.log
```

It ends with `=== tb3: TurtleBot3 installed`. Then close that terminal and open a new one.

### 5. Launch

Each command in its **own** terminal.

1. Simulation: Gazebo with the robot in the TurtleBot3 world. The first start takes up to a
   minute while Gazebo loads the models.
   ```
   ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py
   ```

   Check: `ros2 topic hz /scan` shows about 5 Hz.
2. Drive by hand once, to see which way is forward and what the scan sees:
   ```
   ros2 run turtlebot3_teleop teleop_keyboard
   ```

   The teleop terminal needs the focus for the keys to work. `s` stops.

Stop a launch with `Ctrl+C` in its terminal.

Every terminal already has `TURTLEBOT3_MODEL=burger`, `GZ_IP=127.0.0.1` and
`ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` set (see the end of `~/.bashrc`). The last two keep
Gazebo and ROS traffic inside the pod.

### 6. Work

Make your workspace on the volume, so it survives a stop:

```
mkdir -p ~/rap/ros2_ws/src
```

Then the [task description](TB3-TASK-DESCRIPTION.md). Only `~/rap` is kept; the TurtleBot3
packages install again on every start.

### 7. Stop, or terminate

A running pod costs money even when you do nothing.

- **Stop** when you take a break or come back another day: the GPU is released and `~/rap`
  stays. Start it again from **Pods** next time.
- **Terminate** when you are done: everything is deleted, the volume too. Push your package to
  GitHub before.

## If something does not work

| What you see                                                      | Why                                                                                                                   | What to do                                                                                       |
| ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| No free GPU of the type you chose                                 | they are all rented                                                                                                   | pick another NVIDIA GPU                                                                          |
| **browser desktop** does not open                           | the pod is still starting                                                                                             | wait for **Ready** next to port 8080, refresh                                              |
| A new terminal says the packages are still installing             | the install after start is not done                                                                                   | wait, `tail -f /tmp/tb3-install.log`                                                           |
| The log ends with `install FAILED`                              | the package server did not answer, three times                                                                        | run the command printed on that line                                                             |
| `libEGL warning: failed to open /dev/dri/... Permission denied` | Gazebo renders through the desktop instead                                                                            | nothing                                                                                          |
| `gz_frame_id ... not defined in SDF`                            | from the TurtleBot3 model file                                                                                        | nothing                                                                                          |
| The Gazebo window is sluggish                                     | the desktop renders in software on this host: `glxinfo -B \| grep renderer` shows `llvmpipe` instead of `NVIDIA` | nothing for the lab: `/scan` keeps its rate. Or deploy a new pod, it may land on a better host |
| Teleop keys do nothing                                            | the teleop terminal does not have the focus                                                                           | click into it                                                                                    |
| Your node runs, the robot does not move                           | your node publishes `Twist`, the robot takes `TwistStamped`                                                       | see [the robot&#39;s interfaces](TB3-TASK-DESCRIPTION.md#the-robots-interfaces)                   |
| Your package is gone after a stop                                 | it was not under `~/rap`, or the pod has no volume                                                                  | make the workspace in `~/rap`; push to GitHub                                                  |
