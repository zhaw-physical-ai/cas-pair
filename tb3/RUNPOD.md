# TurtleBot3 simulation on RunPod

A TurtleBot3 Burger in Gazebo Harmonic, on a ROS 2 Jazzy desktop in your browser. It runs on a
RunPod GPU pod, from the same image as the Summit simulation - if you deployed that one, this
is the same procedure with a different template.

If you have a RAP pod on the ZHAW cluster, you can use that instead: install the TurtleBot3
packages there with `sudo apt install ros-jazzy-turtlebot3-gazebo ros-jazzy-turtlebot3-teleop`
and continue at **Launch**. Only the RAP pod can reach the real robots.

## Open the desktop

1. Open the template, logged in to your own RunPod account, and click **Configure Pod**:
   TODO-TEMPLATE-LINK

2. Follow steps 2-7 of [`../summit/SUMMIT-SIM.md`](../summit/SUMMIT-SIM.md#open-the-desktop):
   pod name with your name in it, your own `PASSWD`, a GPU, a 10 GB **volume disk** (it
   mounts to `~/rap`, and your package lives there), **Deploy Pod**, open the browser desktop.

3. Open a terminal (the `$_` icon in the dock). The TurtleBot3 packages install in the
   background during the first 1-2 minutes after start. Until they are done, every new
   terminal says so. Watch the install with:

   ```
   tail -f /tmp/tb3-install.log
   ```

   It ends with `=== tb3: TurtleBot3 installed`. Then close that terminal and open a new one.

## Launch

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

   The teleop terminal has to have the focus for the keys to work. `s` stops.

Stop a launch with `Ctrl+C` in its terminal.

Every terminal already has `TURTLEBOT3_MODEL=burger`, `GZ_IP=127.0.0.1` and
`ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` set (see the end of `~/.bashrc`). The last two keep
Gazebo and ROS traffic inside the pod.

## Your files

Make your workspace on the volume, so it survives a stop:

```
mkdir -p ~/rap/ros2_ws/src
```

Only `~/rap` is kept, and only if you added a volume. The TurtleBot3 packages are not kept:
they install again on every start.

Use **Stop**, not **Terminate**: Terminate deletes the volume with the pod. A stopped pod costs
only its disk (about $2 per month for 10 GB). Push your package to your own git repo as well.

## If Gazebo is slow

As for Summit: `glxinfo -B | grep renderer` shows `NVIDIA ...` for the GPU, `llvmpipe` for
software rendering. The TurtleBot3 world is small, so it works on either, but the Gazebo window
is sluggish in software. The simulation itself is not affected: `/scan` keeps its rate.

## For teachers: the RunPod template

| | |
|---|---|
| Image | `johnsmic/rap-pod:jazzy-8677293`, the Summit image. It has `ros-jazzy-desktop-full` (Gazebo Harmonic) but no TurtleBot3 packages |
| Start command | see the header of [`runpod_start.sh`](runpod_start.sh). It installs the TurtleBot3 packages in the background, adds the lab environment to `~/.bashrc`, then runs [`../summit/runpod_start.sh`](../summit/runpod_start.sh) for the desktop |
| HTTP port | `8080` (noVNC) |
| Visibility | public, so students deploy it from their own accounts |
| Environment | `PASSWD` = `change-me`, as for Summit: each student sets their own at deploy |
| Container disk | 30 GB |
| Volume disk | 10 GB at `/home/ros/rap`, added by each student |
| GPU | NVIDIA only: the image stops without one |

The start script is fetched from `main` on GitHub at every pod start: a change takes effect on
the next start, and only once it is pushed. To skip the install wait, bake the two packages
into an image tag of their own and drop the install block.
