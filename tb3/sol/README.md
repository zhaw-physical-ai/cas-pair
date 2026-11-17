# Solutions and hints for the tb3 tasks

Hints first. [`random_walk/`](random_walk/) is a complete reference package that passes the
acceptance tests - look at it after you have tried, and compare it with your own design.

## Task 0 - simulator up

- `ros2 topic info /cmd_vel -v` shows the type the robot accepts: `TwistStamped`.
  `ros2 topic info /scan -v` shows a reliable publisher in simulation - the Gazebo bridge's
  default. The real robot's lidar driver publishes best effort.
- Index 0 of `ranges` is straight ahead, and the angles grow counter-clockwise (REP 103: x
  forward, y left, z up). Index 90 is left, index 270 is right. Do not hard-code that: a
  different lidar or driver starts somewhere else and has a different number of rays.

## Task 1 - the package

```
cd ~/rap/ros2_ws/src
ros2 pkg create random_walk --build-type ament_python --node-name random_walk \
  --dependencies rclpy geometry_msgs sensor_msgs --license Apache-2.0
cd ~/rap/ros2_ws && colcon build --symlink-install && source install/setup.bash
```

`--node-name` writes `random_walk/random_walk.py` and its entry point in `setup.py`. The
launch file needs `launch` and `launch_ros` in `package.xml` and a `data_files` line in
`setup.py` - slide 50.

## Task 2 - random walk

**The robot does not move, and nothing is wrong.** Your publisher sends `Twist`. The robot
ignores it, there is no error - `ros2 topic info /cmd_vel` lists two types on the topic.
Publish `TwistStamped`.

**No scan arrives on the real robot, but did in simulation.** A reliable subscription does not
connect to a best-effort publisher, and the real lidar driver is best effort. Use
`qos_profile_sensor_data`: it connects to both.

**The robot sees an obstacle that is not there**, or never sees one. Usually index-based ray
selection, or `inf` treated as a number. Compute the angle per ray and wrap it to [-π, π]:
`math.atan2(math.sin(a), math.cos(a))`. Then keep `range_min <= r <= range_max`, which also
drops `inf` and `NaN`.

**It wriggles.** It turns while the obstacle is closer than the threshold, and drives as soon
as it is not - and the next scan puts it back. Two fixes, both needed:
- remember the turn direction once a turn has started, and keep it until the turn ends
- end the turn at a larger distance than it started (hysteresis: start below 0.5 m, stop
  above 0.7 m)

**It keeps driving after the scan is gone.** The decision runs in the scan callback, so when
scans stop, so does the node. Store the latest scan and its arrival time in the callback; a
timer decides and publishes, and sends zero when the scan is too old.

**The watchdog never fires when Gazebo stops.** With `use_sim_time:=true` the timer runs on
simulation time, and simulation time stops with Gazebo. Leave `use_sim_time` off, or create
the timer on a steady clock: `create_timer(period, cb, clock=Clock(clock_type=ClockType.STEADY_TIME))`.

**It does not stop on `Ctrl+C`.** rclpy's own signal handler shuts the context down first, and
the stop message in your `finally` is never sent. Start with
`rclpy.init(signal_handler_options=SignalHandlerOptions.NO)`: `Ctrl+C` then arrives as
`KeyboardInterrupt`, you publish zero, then shut down.

**The launch argument does not change anything.** Launch arguments are strings. Pass them as
parameters with a type: `ParameterValue(LaunchConfiguration('stop_distance'), value_type=float)`.
And check that the node reads the parameter, not a constant.

## Task 3 - the real robot

- `ros2 node list` empty: an old `ros2` daemon from before. `ros2 daemon stop`, then again.
  `printenv RMW_IMPLEMENTATION` must say `rmw_zenoh_cpp`; if not, log out and in again.
- `ros2 topic hz /scan` works but `node list` is empty: the same old daemon.
- You tried from RunPod: it cannot work. The ZHAW network accepts no connections from
  outside; you log in to the robot from your laptop on the ZHAW wifi.
- The robot does not move: is another node publishing on `/cmd_vel` (`ros2 topic info
  /cmd_vel`)? Teleop left running in another terminal holds it too.

- Lichtblick connects to nothing: terminal 2 (bridge) or 3 (tunnel) is not running, or the
  tunnel was opened to another robot. `ws://localhost:8765` only works while both run.
- The tunnel says `Address already in use`: an old tunnel still runs - close it, or use
  another port on your laptop: `-L 8766:127.0.0.1:8765` and `ws://localhost:8766`.
- The 3D panel stays empty: **Display frame** is not `odom`, the eye on `/scan` is off, or the
  view is far from the robot - zoom in on `odom`. A panel that says "Waiting for first GPS
  point" is the **Map** panel, the wrong one.

## The reference package

```
cp -r random_walk ~/rap/ros2_ws/src/
cd ~/rap/ros2_ws && colcon build --symlink-install --packages-select random_walk
source install/setup.bash
ros2 launch random_walk random_walk.launch.py stop_distance:=0.8
```

| file | what it does |
|---|---|
| `random_walk/decide.py` | the decision without ROS: nearest valid range ahead, turn with hysteresis |
| `random_walk/node.py` | store the scan, decide on a 10 Hz timer, watchdog, stop on exit |
| `launch/random_walk.launch.py` | starts the node; `stop_distance`, `clear_distance`, `forward_speed`, `stamped` as arguments |
| `test/test_decide.py` | pytest for `decide.py`: `python3 -m pytest test/` in the package folder |

The turn direction is random - the extension "smarter turn" is still yours.
