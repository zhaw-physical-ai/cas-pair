# Hints for the tb3 tasks

For when you are stuck on a TODO in [`../random_walk/`](../random_walk/). Try it yourself first.

## Task 0 - simulator up

- `ros2 topic info /cmd_vel -v` shows the type the robot accepts: `TwistStamped`.
  `ros2 topic info /scan -v` shows a reliable publisher in simulation - the Gazebo bridge's
  default. The real robot's lidar driver publishes best effort.
- Index 0 of `ranges` is straight ahead, and the angles grow counter-clockwise (REP 103: x
  forward, y left, z up). Index 90 is left, index 270 is right. Do not hard-code that: a
  different lidar or driver starts somewhere else and has a different number of rays.

## Task 1 - the package

- `package.xml`: `<depend>` on `rclpy`, `geometry_msgs` and `sensor_msgs` - what the node
  imports from. `<exec_depend>` on `launch` and `launch_ros` - what the launch file imports.
- `setup.py`, the launch file - slide 50. Add `import os` and `from glob import glob` at the
  top, then in `data_files`:
  `(os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py'))`
- `setup.py`, the executable: `'random_walk = random_walk.node:main'` in `console_scripts` -
  name, then module, then function.
- After changing `setup.py`, build again: `--symlink-install` links your Python files, but not
  new entry points or data files.

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
