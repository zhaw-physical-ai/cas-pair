# Repositories and packages

What to pull, and what each thing actually gives you.

## From apt

```
sudo apt install -y ros-jazzy-desktop \
                    ros-jazzy-rmw-cyclonedds-cpp \
                    ros-jazzy-teleop-twist-keyboard \
                    ros-jazzy-sensor-msgs-py \
                    ros-jazzy-foxglove-bridge \
                    python3-colcon-common-extensions
```

| package | gives you | task |
|---|---|---|
| `ros-jazzy-desktop` | ROS 2 plus `rviz2` and `rosbag2` | 1, 3, 4 |
| `ros-jazzy-rmw-cyclonedds-cpp` | the middleware the dog speaks. **Not optional** | 1 |
| `ros-jazzy-teleop-twist-keyboard` | keyboard -> `geometry_msgs/Twist` on `/cmd_vel` | 2 |
| `ros-jazzy-sensor-msgs-py` | `read_points`, for the lidar | 5 |
| `ros-jazzy-foxglove-bridge` | a websocket at `ws://<jetson>:8765` for Foxglove / Lichtblick | 3 |
| `python3-colcon-common-extensions` | the build tool | 1 |

## From git

**unitree_ros2** - the dog's own message types. Nothing talks to a Go2 without these.

```
git clone https://github.com/unitreerobotics/unitree_ros2
colcon build --packages-select unitree_go unitree_api unitree_hg
```

Build only those three packages. The rest of the repo is Foxy-era examples that will not
build on Jazzy and that you do not need. Its README is written for Foxy - read `jazzy`
wherever it says `foxy`, and skip the "compile cyclonedds" step.

It also ships a `setup.sh` that sets `RMW_IMPLEMENTATION` and `CYCLONEDDS_URI` for you.
Correct the network interface name inside it first, and source it per terminal.

## Tools that are not ROS packages

| | |
|---|---|
| Foxglove Studio | desktop app, connects to the foxglove bridge |
| [Lichtblick](https://github.com/lichtblick-suite/lichtblick) | open-source fork of Foxglove Studio, same protocol, no account |

Both speak the same websocket, so the bridge above serves either.

## Things you do not need for this lab

- **unitree_sdk2 / unitree_sdk2_python** - Unitree's own SDK. A second, non-ROS way to drive
  the dog. It works, but it is not what these tasks are about
- **zenoh-bridge-ros2dds** - for driving a dog from outside the lab network. Not needed when
  your code runs on the Jetson that is cabled to the robot
- **a Go2 simulation** - the simulation labs use
  [khaledgabr77/unitree_go2_ros2](https://github.com/khaledgabr77/unitree_go2_ros2), which is a
  different setup from the real robot: it has `/cmd_vel`, a robot model and a TF tree. A real
  Go2 has none of those

#ATTENTION: there are community packages that expose a Go2 as a normal ROS robot, with
`/cmd_vel` and a URDF ready-made. If you find one and use it, you have skipped task 2 rather
than done it. Write the bridge first; then look at how someone else solved the same problem.
