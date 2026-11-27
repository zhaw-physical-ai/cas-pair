# High level task description for tb3

A TurtleBot3: a small differential-drive robot with a 360° 2D lidar. You write a ROS 2 node
that lets it wander - first a Burger in Gazebo, then, optionally, a real Burger or Waffle Pi in
class. Both have the same lidar and the same interfaces, so the same node drives either.

This is the lab of Session 1 (packages and first nodes). Everything you need was in this
morning's slides: a package, a publisher, a subscriber, a timer, sensor QoS, parameters and a
launch file. You get the package [`random_walk/`](random_walk/) with the important lines taken
out: each `# TODO` says what the missing line has to do. Write them yourself, without AI - the
point is that you can explain every line afterwards.

## The robot's interfaces

| topic        | type                               | direction                           |
| ------------ | ---------------------------------- | ----------------------------------- |
| `/scan`    | `sensor_msgs/msg/LaserScan`      | the robot publishes, 5 Hz, 360 rays |
| `/cmd_vel` | `geometry_msgs/msg/TwistStamped` | the robot subscribes                |

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

- fork cas-pair on GitHub and clone your fork into your workspace:
  ```
  mkdir -p ~/rap/ros2_ws/src && cd ~/rap/ros2_ws/src
  git clone <your fork>
  ```
- the TODOs in `package.xml` and `setup.py`: the dependencies, the launch file, and the
  executable, so that `ros2 run random_walk random_walk` finds the node
- build it, and source the overlay:
  ```
  cd ~/rap/ros2_ws && colcon build --symlink-install --packages-select random_walk
  source install/setup.bash
  ```

  `--packages-select`: your fork holds other ROS packages too, which do not build here

Advanced:

- `ros2 pkg executables random_walk` lists your node; you can say which file made that so

## Task 2: Random walk

The TODOs in `random_walk/decide.py`, `random_walk/node.py` and the launch file. The node has
to meet four requirements:

1. **Drive.** It moves forward while the space ahead is clear.
2. **Avoid.** It turns away when something is close ahead - in one direction, without
   wriggling between left and right.
3. **Never blind.** No recent scan means a zero command. This includes the start, before the
   first scan arrives, and the end: when your node stops, the robot stops.
4. **Reusable.** Relative topic names, the thresholds as parameters, and one launch file
   that starts the node and can set them.

### Done when

Your node passes these tests. Run them in this order and write down what you saw.

| test                | procedure                                   | pass                                  |
| ------------------- | ------------------------------------------- | ------------------------------------- |
| Start without scans | start your node before the simulator        | only zero commands                    |
| Open space          | robot in a clear area                       | drives forward                        |
| Obstacle ahead      | robot drives towards a wall                 | turns away, one direction, no wriggle |
| Obstacle cleared    | keep watching                               | drives forward again                  |
| Sensor lost         | stop the simulation while your node runs    | zero commands within about 0.5 s      |
| Stop                | `Ctrl+C` your node while the robot drives | the robot stops                       |
| Reconfigure         | change the threshold in the launch command  | behaviour changes, no code edit       |

Before the simulator, test the decision on its own: in the package folder,
`python3 -m pytest test/` must pass all tests.

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

## Task 3: The real robot

The same package, on a real robot. Your node runs **on the robot itself**: you log in to its
Raspberry Pi over ssh, build your package there and start it. The robot's own nodes (motors,
lidar) are already running - you start only yours.

When your node works in the simulation, **push it to your fork**. The robot gets it from there
with `git clone`.

**Show your teacher your random walk passing Task 2's acceptance tests in the simulation.**
Then you get a robot name and the password for the user `cas`. Your laptop on the ZHAW
wifi:

1. Log in:

   ```
   ssh cas@<robot>
   ```

   `cas` has no sudo: you cannot install anything, and you do not need to. ROS 2 and the
   robot's settings are loaded at login.
2. Check that you see the robot:

   ```
   ros2 node list           # turtlebot3_node, diff_drive_controller, hlds_laser_publisher, robot_state_publisher
   ros2 topic hz /scan      # about 5 Hz, Ctrl+C to end
   ```
3. Your workspace - one per group, in a folder with your group's name, so you do not build
   over the others:

   ```
   mkdir -p ~/<group>/src && cd ~/<group>/src
   git clone <your fork>
   cd ~/<group> && colcon build --symlink-install --packages-select random_walk
   source install/setup.bash
   ```
4. Start your launch file with half your speeds and watch which
   way the wheels turn. Ctrl+C: they must stop at once.

Each new terminal: `cd ~/<group> && source install/setup.bash`. A fix: change it on RunPod,
push, then `git pull` and `colcon build` on the robot.

Safety:

- **test "Stop" in simulation first.** A node that does not stop on exit leaves the robot
  driving its last command
- only one node on `/cmd_vel`: close teleop before you start yours
- do not touch the robot's own nodes: they belong to the user `ubuntu`, and you cannot stop
  them anyway

Advanced:

- the real lidar sees things the simulated one does not: chair legs, black surfaces, glass,
  people's feet. Which acceptance test fails first, and why?

## Task 4: Fun tb3 race (optional)

We build a race course on the floor: walls, a start and a goal. Your random walk has no idea
where the goal is - it only drives and turns away. Which robot gets there first? It is an
experiment: tune it, try it, keep what helps.

Rules:

- one robot on the course at a time, timed from start to goal. Three runs, your best counts:
  your robot turns in a random direction, so luck plays along
- your node, started with your launch file. Nobody touches the robot during a run. A robot stuck
  for 30 s is out for that run
- `forward_speed` at most 0.20 m/s, the same for Burger and Waffle Pi
- the safety rules from Task 3 still hold: one node on `/cmd_vel`, `Ctrl+C` stops it

What you can change:

- the parameters, from the launch command: `stop_distance`, `clear_distance`, `turn_speed`,
  `half_angle_deg`, ... - each one your launch file declares as an argument. Which one makes the biggest difference? Write down what you tried and
  the time it gave
- the code, if you want: turn towards the side with more room instead of a random side, or
  follow a wall. Does it beat your tuned random walk?

## Discussion: would it work on the Go2?

The Go2's lidar is 3D and sparse: a `PointCloud2` with few points per frame, in a pattern that
does not repeat. Its body pitches while it walks, so a thin 2D slice of the cloud hits the
floor or misses the obstacle. Which parts of your node change, and which should not? What would
replace the `LaserScan` as input?
