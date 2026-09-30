# Setting up the Jetson for the Go2

Two routes: ROS 2 Jazzy natively, or a `ros:humble` container. Both work with the dog. This
is the native one.

#ATTENTION: a ROS 2 release is tied to an Ubuntu version. The Jetson runs 24.04, so natively
it is Jazzy. There is no `ros-humble-*` package for this machine.

## Install ROS 2 Jazzy

https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html

#ATTENTION: a fresh Jetson has no ROS apt repository. Without this first step every
`apt install ros-jazzy-*` below fails with `Unable to locate package`.

```
sudo apt install -y software-properties-common curl
sudo add-apt-repository universe

export ROS_APT_SOURCE_VERSION=$(curl -s https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F "tag_name" | awk -F'"' '{print $4}')
curl -L -o /tmp/ros2-apt-source.deb "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.$(. /etc/os-release && echo ${UBUNTU_CODENAME})_all.deb"
sudo dpkg -i /tmp/ros2-apt-source.deb
sudo apt update
```

Then ROS itself:

```
sudo apt install -y ros-jazzy-desktop
echo 'source /opt/ros/jazzy/setup.bash' >> ~/.bashrc
```

The packages the tasks need:

```
sudo apt install -y ros-jazzy-rmw-cyclonedds-cpp \
                    ros-jazzy-rosidl-generator-dds-idl \
                    ros-jazzy-teleop-twist-keyboard \
                    ros-jazzy-sensor-msgs-py \
                    ros-jazzy-foxglove-bridge \
                    python3-colcon-common-extensions
```

## Build the Unitree message types

The dog's messages are in no ROS distribution. Clone and build them yourself:

```
mkdir -p ~/repos/cas_26_YOUR_NAME/ros_ws/src
cd ~/repos/cas_26_YOUR_NAME/ros_ws/src
git clone https://github.com/unitreerobotics/unitree_ros2
```

Only the message packages - the rest of that repo is Foxy-era examples that will not build
and are not needed:

```
cd ~/repos/cas_26_YOUR_NAME/ros_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select unitree_go unitree_api unitree_hg \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
source install/setup.bash
```

#ATTENTION: that `-DPython3_EXECUTABLE` is not optional on these machines. `uv` puts its own
Python in `~/.local/bin`, ahead of the system one on your PATH. CMake picks it up, and it has
none of ROS's Python dependencies - the build dies with `ModuleNotFoundError: No module named
'em'`, which says nothing about the real cause. The flag tells CMake which Python to use.

Verified on 29 Sep 2026: `Summary: 3 packages finished` in about a minute.

Check they are there:

```
ros2 interface show unitree_api/msg/Request
```

## Connect to the dog

Ethernet, no DHCP - the Go2 hands out no addresses, so set yours by hand. Once per Jetson:

```
nmcli -t -f NAME,DEVICE con show
sudo nmcli con mod "Wired connection 1" ipv4.method manual ipv4.addresses 192.168.123.99/24
sudo nmcli con up "Wired connection 1"
ping -c2 192.168.123.161
```

`192.168.123.161` is the dog's main board. A reply means the cable is fine - it does not mean
the robot is ready to talk ROS, which takes longer.

## Point ROS at the dog

Find the interface name first - it is the one holding the `192.168.123.x` address, and it
is **not** the same on every machine (a USB Ethernet adapter comes up as `enx...`):

```
ip -br addr
```

Then, in **every terminal** you work in. All four lines, every time - the machines are
shared, so do not put them in `~/.bashrc`:

```
source /opt/ros/jazzy/setup.bash
source ~/repos/cas_26_YOUR_NAME/ros_ws/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces>
  <NetworkInterface name="YOUR_INTERFACE"/></Interfaces></General></Domain></CycloneDDS>'
```

Forgetting the second line is the most common way to lose twenty minutes: the topics appear
but their types show as unknown, because the Unitree messages live in that workspace.

`unitree_ros2` ships its own `setup.sh` that sets both of these. If you use it, correct the
interface name inside it first.

## Check it works

```
ros2 topic list
```

successful output contains, e.g.:

```
/api/sport/request
/lf/sportmodestate
/lowstate
/utlidar/cloud
/utlidar/robot_odom
```

```
ros2 topic echo /lf/sportmodestate --field mode
```

A number that changes when you press buttons on the remote means you are talking to a real
robot.

## What you pull, and what you write

Most of this lab is stock ROS. Only two things are yours to program:

| pull | write |
|---|---|
| ROS 2 Jazzy, `teleop_twist_keyboard`, `rviz2`, `foxglove_bridge`, `rosbag2` | the bridge node: `geometry_msgs/Twist` -> `unitree_api/msg/Request` |
| the Unitree message packages | the obstacle node: lidar -> stop or turn |

`teleop_twist_keyboard` is a package, not something you write:

```
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

It publishes `geometry_msgs/Twist` on `/cmd_vel`, and by itself it does nothing to the dog -
**a Go2 has no `/cmd_vel`.** The node that turns those messages into something the robot
understands is task 2, and there is no package for it. See `GO2-TASK2-DRIVE-SOL.md`.

# Troubleshooting

`ros2 topic list` is empty or nearly empty:
- the robot is not ready yet - wait, it takes longer than `ping` does
- `RMW_IMPLEMENTATION` is not set in *this* terminal
- `CYCLONEDDS_URI` is not pinning the interface, and CycloneDDS bound the wifi instead
- a stale CLI daemon is answering - try `ros2 topic list --no-daemon`

`colcon build` fails with `Could not find a package configuration file provided by
"rosidl_generator_dds_idl"`:
- that generator is not pulled in by `ros-jazzy-desktop` or `ros-base`. Install
  `ros-jazzy-rosidl-generator-dds-idl` and build again

`colcon build` fails with `ModuleNotFoundError: No module named 'em'`:
- CMake found `uv`'s Python in `~/.local/bin` instead of the system one. Look at the path in
  the error - if it is not `/usr/bin/python3`, that is why. Rebuild with
  `--cmake-args -DPython3_EXECUTABLE=/usr/bin/python3`

Topics are listed but their types show as unknown:
- the Unitree message packages are not built, or `install/setup.bash` is not sourced here

It worked, then went deaf after the cable was moved or the dog power-cycled:
- CycloneDDS binds the interface at startup and does not recover. Restart your nodes.
