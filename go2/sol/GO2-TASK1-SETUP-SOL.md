# Setting up the Jetson for the Go2

Two routes: ROS 2 Jazzy natively, or a `ros:humble` container. Both work with the dog. This
is the native one.

#ATTENTION: a ROS 2 release is tied to an Ubuntu version. The Jetson runs 24.04, so natively
it is Jazzy. There is no `ros-humble-*` package for this machine.

## Install ROS 2 Jazzy

https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html

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
colcon build --packages-select unitree_go unitree_api unitree_hg
source install/setup.bash
```

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

Per terminal, not in `~/.bashrc` - the machines are shared:

```
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces>
  <NetworkInterface name="enP8p1s0"/></Interfaces></General></Domain></CycloneDDS>'
```

Find the interface name - it is the one holding the `192.168.123.x` address:

```
ip -br addr
```

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

Topics are listed but their types show as unknown:
- the Unitree message packages are not built, or `install/setup.bash` is not sourced here

It worked, then went deaf after the cable was moved or the dog power-cycled:
- CycloneDDS binds the interface at startup and does not recover. Restart your nodes.
