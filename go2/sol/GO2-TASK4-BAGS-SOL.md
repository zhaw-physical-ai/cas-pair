# Task 4: Record and replay

Every terminal needs the environment first - `source ~/go2env.sh`, or the block in
`GO2-TASK1-SETUP-SOL.md`. A terminal without it shows empty topic lists and unknown types.

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
nothing will draw a dog - and, as in task 2, rviz needs a frame it knows about before it will
draw anything at all. `/utlidar/robot_odom` is in frame `odom`, so:

```
ros2 run tf2_ros static_transform_publisher --frame-id map --child-frame-id odom
```

Add an **Odometry** display on `/utlidar/robot_odom` and set the Fixed Frame to `map` - you get the path it took, which is what the
task is asking you to compare.

Two things to look at:

- the dog does not end up where it did the first time. That is the discussion, not a bug
- **check the timestamps rather than assuming them.** The dog stamps its own messages and its
  clock is its own. Sometimes it agrees with the Jetson to within a second; sometimes it is
  tens of minutes out. It is not reliably wrong *or* reliably right - measure it:

  ```
  date +%s
  ros2 topic echo /lf/sportmodestate --field stamp.sec --once
  ```
  If those differ by more than a second or two, commanded and measured motion will not line
  up on a shared time axis and a correct plot will look broken
