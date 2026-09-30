# Task 2: Use the tools

Every terminal needs the environment first - `source ~/go2env.sh`, or the block in
`GO2-TASK1-SETUP-SOL.md`. A terminal without it shows empty topic lists and unknown types.

What a real Go2 publishes:


| topic | type |
|---|---|
| `/lf/sportmodestate` | `unitree_go/msg/SportModeState` - mode, body velocity, foot state |
| `/utlidar/robot_odom` | `nav_msgs/Odometry` |
| `/utlidar/cloud` | `sensor_msgs/PointCloud2` |
| `/lowstate` | `unitree_go/msg/LowState` - joints, IMU, battery |

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

   On 30 Sep 2026 that was `utlidar_lidar`. That is a *frame*, not the topic name - typing
   `utlidar/cloud` into Fixed Frame gives `could not transform from utlidar_lidar to
   utlidar/cloud`.

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

Verified on 30 Sep 2026: with the static transform running and Fixed Frame set to `map`, the
cloud renders and changes as someone moves in front of the robot.

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

The dog does not need to walk for any of this, and it should not - driving is task 3.

Foxglove Studio or Lichtblick - run the bridge on the Jetson:

```
ros2 launch foxglove_bridge foxglove_bridge_launch.xml
```

then connect the app to `ws://<jetson-address>:8765` - **Open connection -> Foxglove
WebSocket**. The bridge process needs the Unitree message packages sourced, or the
`unitree_go` topics arrive undecodable.

#ATTENTION: it prints a wall of errors like `Failed to load schemaDefinition for topic
"/arm_Command" (unitree_arm/msg/ArmString): package 'unitree_arm' not found`. **Ignore them.**
The dog advertises around 120 topics and some use Unitree packages you deliberately did not
build. The bridge serves everything it can decode, which is everything this lab needs.
Check it is really up with `ss -ltn | grep 8765` rather than by reading the log.

Quick look at a single value, no GUI needed:

```
ros2 topic echo /utlidar/robot_odom --field pose.pose.position
```
