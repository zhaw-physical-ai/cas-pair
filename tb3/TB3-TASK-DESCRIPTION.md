# High level task description for tb3

A TurtleBot3 Burger: a small differential-drive robot with a 360° 2D lidar. You write a ROS 2
node that lets it wander - first in Gazebo, then, optionally, on a real robot in class.

This is the lab of Session 1 (packages and first nodes). Everything you need was in this
morning's slides: a package, a publisher, a subscriber, a timer, sensor QoS, parameters and a
launch file. There is no skeleton: you design the node.

## The robot's interfaces

| topic | type | direction |
|---|---|---|
| `/scan` | `sensor_msgs/msg/LaserScan` | the robot publishes, 5 Hz, 360 rays |
| `/cmd_vel` | `geometry_msgs/msg/TwistStamped` | the robot subscribes |

**`TwistStamped`, not `Twist`.** On Jazzy the simulated TurtleBot3 takes `TwistStamped`; the
slides show `Twist`. A `Twist` publisher on `/cmd_vel` never connects to the robot, and your
node reports no error - the robot just does not move. The velocities are in `msg.twist`; fill in `msg.header.stamp` as well. A real
TurtleBot3 can be configured for either type: check with `ros2 topic info /cmd_vel` before you
drive one.

Units are SI. The Burger's top speeds are 0.22 m/s and 2.84 rad/s; stay well below them.

## Task 0: Simulator up

Basic:
- start the simulation, on RunPod ([`RUNPOD.md`](RUNPOD.md)) or in your RAP pod
- drive the robot by hand with teleop once
- check both interfaces with `ros2 topic info -v`: type, number of publishers and
  subscribers, and the QoS of each

Advanced:
- echo one scan and work out which index of `ranges` looks straight ahead, and which way
  the angles grow. Put an obstacle in front of the robot (drive it to a pillar) and check

## Task 1: The package

Basic:
- create an `ament_python` package `random_walk` in `~/rap/ros2_ws/src`, with its
  dependencies declared up front
- one node, started with `ros2 run random_walk random_walk`
- build with `colcon build --symlink-install` and source the overlay

Advanced:
- `ros2 pkg executables random_walk` lists your node; you can say which file made that so

## Task 2: Random walk

Write the node. It has to meet four requirements:

1. **Drive.** It moves forward while the space ahead is clear.
2. **Avoid.** It turns away when something is close ahead - in one direction, without
   wriggling between left and right.
3. **Never blind.** No recent scan means a zero command. This includes the start, before the
   first scan arrives, and the end: when your node stops, the robot stops.
4. **Reusable.** Relative topic names, the thresholds as parameters, and one launch file
   that starts the node and can set them.

### Done when

Your node passes these tests. Run them in this order and write down what you saw.

| test | procedure | pass |
|---|---|---|
| Start without scans | start your node before the simulator | only zero commands |
| Open space | robot in a clear area | drives forward |
| Obstacle ahead | robot drives towards a wall | turns away, one direction, no wriggle |
| Obstacle cleared | keep watching | drives forward again |
| Sensor lost | stop the simulation while your node runs | zero commands within about 0.5 s |
| Stop | `Ctrl+C` your node while the robot drives | the robot stops |
| Reconfigure | change the threshold in the launch command | behaviour changes, no code edit |

`ros2 topic echo /cmd_vel` shows what your node sends. For the "sensor lost" test, `Ctrl+C` the
Gazebo launch: it takes the scan with it.

Hints:
- ahead is an **angle**, not an index. Compute each ray's angle from `angle_min` and
  `angle_increment`, and keep the rays within ±30° of zero. The TurtleBot3's scan runs from 0
  to 2π, so "ahead" is at both ends of the array
- not every range is valid: `inf`, `NaN`, and anything outside `[range_min, range_max]`
- store, then act. If you decide in the scan callback, who notices when scans stop arriving?
- subscribe to the scan with `qos_profile_sensor_data`. In simulation a reliable
  subscription works too - the Gazebo bridge publishes reliable - but the real robot's lidar
  driver is best effort, and a reliable subscriber gets nothing from it
- no wriggle needs memory: once your node has started a turn, when does it end?
- stopping on `Ctrl+C` is harder than it looks: by default ROS shuts down before your
  `finally` runs, and a publish there goes nowhere

## Task 3: The real robot (optional)

Only from a RAP pod on the ZHAW cluster: RunPod cannot reach the robots.

Basic:
- ask for a robot. The lab assistant sets it to your group's `ROS_DOMAIN_ID`
- in every terminal you use for the robot: source `set_remote_robot.sh` from
  [RAP_BUILD_LAB](https://github.zhaw.ch/RAP-EN/RAP_BUILD_LAB) and export your
  `ROS_DOMAIN_ID`. `ros2 node list` then shows the robot's nodes
- check the type of `/cmd_vel` on the robot, then run your launch file

Safety:
- **test "Stop" in simulation first.** A node that does not stop on exit leaves the robot
  driving its last command
- start with the robot lifted off the floor, wheels free, and watch which way they turn
- halve your speeds for the first run, and stay next to it

Advanced:
- the real lidar sees things the simulated one does not: chair legs, black surfaces, glass,
  people's feet. Which acceptance test fails first, and why?

## Task 4: Go further (optional)

Pick one.

| extension | question | evidence |
|---|---|---|
| Testable logic | is the decision code testable without ROS? | pytest cases for the edge conditions |
| Timing | how long from "scan lost" to "zero command"? | measured intervals, with and without load |
| Smarter turn | turn towards the side with more room? | compared against a random choice |
| Replay | can another team reproduce your result? | a bag, your config, your package revision |
| C++ port | the same node in rclcpp? | builds, passes the tests above |
| Two robots | can commands reach the wrong robot? | namespaces or domains, demonstrated |

## Discussion: would it work on the Go2?

The Go2's lidar is 3D and sparse: a `PointCloud2` with few points per frame, in a pattern that
does not repeat. Its body pitches while it walks, so a thin 2D slice of the cloud hits the
floor or misses the obstacle. Which parts of your node change, and which should not? What would
replace the `LaserScan` as input?
