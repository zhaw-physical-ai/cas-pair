# Task 2: Use the tools

Every terminal needs the environment first - `source ~/go2env.sh`, or the block in
`GO2-TASK1-SETUP-SOL.md`. A terminal without it shows empty topic lists and unknown types.

What a real Go2 publishes:

| topic                   | type                                                                |
| ----------------------- | ------------------------------------------------------------------- |
| `/lf/sportmodestate`  | `unitree_go/msg/SportModeState` - mode, body velocity, foot state |
| `/utlidar/robot_odom` | `nav_msgs/Odometry`                                               |
| `/utlidar/cloud`      | `sensor_msgs/PointCloud2`                                         |
| `/lowstate`           | `unitree_go/msg/LowState` - joints, IMU, battery                  |

#ATTENTION: there is **no `/robot_description` and no `/tf`** on a real Go2. Nothing will draw
a dog in a 3D view, and RViz cannot place the point cloud in a world frame - set the Fixed
Frame to the cloud's own frame instead.

rviz:

```
rviz2
```

To see the lidar, and to check the tool is really working:

1. **Find the cloud's frame:**

   ```
   ros2 topic echo /utlidar/cloud --field header.frame_id --once
   ```

   It says `utlidar_lidar`. That is a *frame*, not the topic name - typing `utlidar/cloud`
   into Fixed Frame gives `could not transform from utlidar_lidar to utlidar/cloud`.

2. **Give rviz a frame to anchor to.** The dog publishes **no transforms at all** - `/tf` and
   `/tf_static` exist only because rviz subscribes to them, and `ros2 topic info /tf` shows
   `Publisher count: 0`. tf2 therefore knows no frames, the Fixed Frame dropdown is empty, and
   `utlidar_lidar` is not offered even though every message carries it.

   Leave this running in its own terminal - it must stay up, it is the only thing that makes
   `utlidar_lidar` a frame rviz knows:

   ```
   ros2 run tf2_ros static_transform_publisher --frame-id map --child-frame-id utlidar_lidar
   ```

   No offsets needed. With nothing else on screen there is nothing for the lidar to be
   correctly placed *relative to*, so a zero transform is enough. Now both `map` and
   `utlidar_lidar` exist and either works as Fixed Frame.
3. set **Fixed Frame** to `map`
4. **Add** -> **PointCloud2**, topic `/utlidar/cloud`
5. **tick the checkbox next to it in the Displays panel.** Adding a display does not enable
   it. An unticked display draws nothing, reports nothing, and looks exactly like a topic
   that is not publishing
6. set its **Reliability Policy** to **Best Effort**. The dog publishes best-effort, and a
   reliable display simply never receives anything - again no error, just an empty screen
7. walk in front of the robot and watch the points move

**To add the odometry too**, publish a second static transform - `/utlidar/robot_odom` is in
frame `odom`:

```
ros2 run tf2_ros static_transform_publisher --frame-id map --child-frame-id odom
```

Both of these are lies about the geometry: the lidar is not at the origin of `map`, and
neither is `odom`. rviz will draw them anyway, in the wrong places relative to each other.
Understanding why they are lies is worth more than the picture - it is the clearest way to see
what a missing TF tree actually costs you, and why the simulation in lab 1 looks so much
better than the real robot.

## Getting each tool

Two places a viewer can run, and it matters which:

- **on the Jetson** - it renders on the attached screen, and uses the Jetson's GPU
- **on your own laptop** - it connects over the network to `foxglove_bridge` on the Jetson.
  Both machines must be on the same wifi. Better with five machines in one room, because the
  Jetsons then only serve data

**rviz2** - already installed with `ros-jazzy-desktop`. Runs on the Jetson only:

```
source ~/go2env.sh
rviz2
```

Over ssh it needs `export DISPLAY=:1` first, or it dies with a Qt error - an ssh session has
no screen of its own.

**Foxglove Studio / Lichtblick** - desktop apps, meant for *your laptop*, not the Jetson.
Download from [foxglove.dev](https://foxglove.dev) or
[Lichtblick releases](https://github.com/lichtblick-suite/lichtblick/releases). Lichtblick is
the open-source fork and needs no account. Then, on the Jetson:

```
source ~/go2env.sh
ros2 launch foxglove_bridge foxglove_bridge_launch.xml
```

and in the app: **Open connection -> Foxglove WebSocket ->** `ws://<jetson-address>:8765`.

The bridge needs the Unitree message packages sourced, or the `unitree_go` topics arrive
undecodable.

#ATTENTION: it prints a wall of errors like `Failed to load schemaDefinition for topic
"/arm_Command" (unitree_arm/msg/ArmString): package 'unitree_arm' not found`. **Ignore them.**
The dog advertises around 120 topics and some use Unitree packages you deliberately did not
build. The bridge serves everything it can decode, which is everything this lab needs. Check
it is really up with `ss -ltn | grep 8765` rather than by reading the log.

If you want one of them on the Jetson itself, check first that the download has an **arm64**
build - many desktop apps ship x86-64 only, and a Jetson is arm64.

### Advanced - if you have time

Neither is needed to finish the task.

**PlotJuggler** is an apt package and runs on the Jetson:

```
sudo apt install -y ros-jazzy-plotjuggler-ros
ros2 run plotjuggler plotjuggler
```

Then **Streaming -> ROS2 Topic Subscriber** and pick a field. Better than rviz for anything
that is a number over time, and it needs no Fixed Frame and no transforms at all.

**RosBoard** is a web dashboard - clone it on the Jetson, look at it from any browser:

```
git clone https://github.com/dheera/rosboard.git ~/repos/cas_26_YOUR_NAME/rosboard
cd ~/repos/cas_26_YOUR_NAME/rosboard
./run
```

then `http://<jetson-address>:8888`. If it needs extra Python packages it will say so when
you run it.

More starting points in [`../LINKS.md`](../LINKS.md).

## Quick look at a single value, no GUI needed

```
ros2 topic echo /utlidar/robot_odom --field pose.pose.position
```
