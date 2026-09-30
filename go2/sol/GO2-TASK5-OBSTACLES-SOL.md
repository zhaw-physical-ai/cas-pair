# Task 5: Avoid obstacles

Task 2 first - this node steers through the one you already wrote.

#ATTENTION: a node that drives forward by itself is exactly the thing that walks into a wall
while you are reading its output. Hand on the remote the first time, every time.

## The lidar

```
ros2 topic info /utlidar/cloud
ros2 topic hz /utlidar/cloud
ros2 topic echo /utlidar/cloud --once --field fields
```

The last one shows you the layout of a point. Read it before you write anything - **do not
assume which axis is forward.** Check it: put an obstacle in front of the dog, echo a few
points, and see which coordinate changes.

Reading points needs:

```
sudo apt install -y ros-jazzy-sensor-msgs-py
```

## What your node has to do

- subscribe to `/utlidar/cloud`, type `sensor_msgs/PointCloud2`
- **the dog publishes best-effort.** A reliable subscription simply never matches, and the
  symptom is silence rather than an error. Ask for best-effort QoS
- read the points - `sensor_msgs_py.point_cloud2.read_points`, with `skip_nans=True`
- keep only the points that matter: further than the dog's own body, nearer than your
  threshold, inside a corridor left and right, above the floor
- **the floor is also points.** Without a height filter the ground is a permanent obstacle
- count them, do not trust one. A handful of points is noise; a wall is hundreds
- publish `geometry_msgs/Twist` to `/cmd_vel` - your task 2 node turns that into robot
  commands. Do not talk to `/api/sport/request` from here
- start by stopping, then make it turn away instead
- on exit, publish a zero Twist so the task 2 node sends StopMove

## Running it

Two terminals, plus the robot:

```
ros2 run <your_pkg> <your_bridge_node>
```

```
ros2 run <your_pkg> <your_avoid_node>
```

Walk the dog at a wall. It should stop or turn before it gets there.

#ATTENTION: do not leave `teleop_twist_keyboard` running at the same time. Both it and your
avoidance node publish to `/cmd_vel`, and the bridge simply acts on whichever message arrived
last - so a stray key press can override a stop.

## Advanced: the camera

React to what something *is*, not only how far away it is.

#ATTENTION: `/frontvideostream` is a raw H.264 stream, not `sensor_msgs/Image`, so there is
no `image_transport` path to it without decoding first. If you want vision without fighting a
codec, put a USB camera on the Jetson instead.

# Troubleshooting

The subscription never fires:
- QoS. The dog publishes best-effort; a reliable subscription matches nothing and says nothing

Everything looks like an obstacle:
- you are seeing the floor, or the dog's own legs. Filter by height and by minimum distance

It stops in open space, or ignores a wall:
- your idea of "forward" does not match the sensor's. Go back and check the axis
- your point count threshold is too low, or too high
