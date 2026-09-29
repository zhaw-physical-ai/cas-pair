# Task 3: Use the tools


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

Foxglove Studio or Lichtblick - run the bridge on the Jetson:

```
ros2 launch foxglove_bridge foxglove_bridge_launch.xml
```

then connect the app to `ws://<jetson-address>:8765`. The bridge process needs the Unitree
message packages sourced, or the `unitree_go` topics arrive undecodable.

Quick look at a single value, no GUI needed:

```
ros2 topic echo /utlidar/robot_odom --field pose.pose.position
```
