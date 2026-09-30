# Links and tools

Where things come from and what each one is for, for both labs. **Not instructions** - the
commands live in the task files. For the Go2, that is
[`go2/sol/GO2-TASK1-SETUP-SOL.md`](go2/sol/GO2-TASK1-SETUP-SOL.md), and the ROS apt repository
has to be added before any of these install.

## Go2 - packages you install

| package | gives you | task |
|---|---|---|
| `ros-jazzy-desktop` | ROS 2 plus `rviz2` and `rosbag2` | 1, 2, 4 |
| `ros-jazzy-rmw-cyclonedds-cpp` | the middleware the dog speaks. **Not optional** | 1 |
| `ros-jazzy-rosidl-generator-dds-idl` | the Unitree messages will not configure without it. **Not optional** | 1 |
| `ros-jazzy-teleop-twist-keyboard` | keyboard -> `geometry_msgs/Twist` on `/cmd_vel` | 3 |
| `ros-jazzy-sensor-msgs-py` | `read_points`, for the lidar | 5 |
| `ros-jazzy-foxglove-bridge` | a websocket at `ws://<jetson>:8765` for Foxglove / Lichtblick | 2 |
| `python3-colcon-common-extensions` | the build tool | 1 |

## Go2 - source you clone

**[unitree_ros2](https://github.com/unitreerobotics/unitree_ros2)** - the dog's own message
types. Nothing talks to a Go2 without them. Build only `unitree_go`, `unitree_api` and
`unitree_hg`; the rest is Foxy-era examples that will not build on Jazzy and that you do not
need. Its README is written for Foxy - read `jazzy` wherever it says `foxy`, and skip the
"compile cyclonedds" step.

## Viewers - either lab

| | |
|---|---|
| [Lichtblick](https://github.com/lichtblick-suite/lichtblick) | desktop app, connects to `foxglove_bridge`. **No account needed** - start here |
| [Foxglove Studio](https://foxglove.dev) | the same thing, but **requires signing up for an account** before you can use it |

Both speak the same websocket, so one bridge serves either.

## Other tools people use - either lab

Not part of either lab. If you want to go further, these are where to start:

| | |
|---|---|
| [PlotJuggler](https://github.com/facontidavide/PlotJuggler) | plotting values over time; needs no frames or transforms |
| [RosBoard](https://github.com/dheera/rosboard) | a web dashboard - nothing to install on the machine you look from |
| [rqt](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-RQt.html) | the standard ROS plugin GUI, already installed with `ros-jazzy-desktop` |

## Reference

- [SO-101 instructions](so101/SO-101-TASK-DESCRIPTION.md) and
  [Go2 instructions](go2/GO2-TASK-DESCRIPTION.md)

- [ROS 2 Jazzy installation](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)
- [rosbag2](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Recording-And-Playing-Back-Data/Recording-And-Playing-Back-Data.html)
- [tf2 static transforms](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Static-Broadcaster-Py.html)
