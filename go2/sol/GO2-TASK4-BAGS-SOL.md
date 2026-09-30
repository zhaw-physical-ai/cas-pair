# Task 4: Record and replay


```
ros2 bag record -o my_route /cmd_vel /utlidar/robot_odom /lf/sportmodestate
```

Those three topics only. `/utlidar/cloud` is gigabytes a minute and a bag you cannot copy off
the machine is not much use.

```
ros2 bag info my_route
ros2 bag play my_route
```

#ATTENTION: **replay drives the robot.** Nothing downstream can tell whether a `/cmd_vel`
message came from your keyboard or from a bag. Before you press play: remote in hand, area
clear, someone watching the dog rather than the screen, and a short bag the first time.

To watch it in rviz, remember there is **no TF tree and no robot model** on a real Go2, so
nothing will draw a dog. Add an **Odometry** display on `/utlidar/robot_odom` and set the
Fixed Frame to that message's own `frame_id` - you get the path it took, which is what the
task is asking you to compare.

Two things to look at:

- the dog does not end up where it did the first time. That is the discussion, not a bug
- the timestamps may not say what you assume. The dog's clock is not the Jetson's - it was
  about 39 minutes off on 23 Sep 2026. If that is still true, commanded and measured motion
  will not line up on a shared time axis, and a correct plot will look broken
