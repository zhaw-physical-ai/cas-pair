# High level task description for so-101: URDF and Xacro

The lab of Session 2 (robot models: URDF and Xacro). Runs in your RAP pod; no robot needed.
No RAP pod? Use RunPod as in [`../tb3/RUNPOD.md`](../tb3/RUNPOD.md), any GPU.

## Task 0: Setup

```bash
mkdir -p ~/rap/urdf_ws/src && cd ~/rap/urdf_ws     # ~/rap survives a pod restart
source /opt/ros/jazzy/setup.bash
sudo apt install -y liburdfdom-tools ros-jazzy-joint-state-publisher-gui ros-jazzy-tf2-tools
```

The apt line is needed again after a pod restart. Check every model before launching it:

```bash
xacro model.urdf.xacro -o /tmp/model.urdf && check_urdf /tmp/model.urdf
```

## Task 1: Robot from scratch

Basic:

- build `sam_bot_description` with the [Nav2 URDF guide](https://docs.nav2.org/setup_guides/urdf/setup_urdf.html)
- show it in RViz2 with `display.launch.py`
- in RViz2: Fixed Frame `base_link`, Add → RobotModel (topic `/robot_description`), Add → TF

## Task 2: SO-101 package

```bash
git clone --depth 1 https://github.com/TheRobotStudio/SO-ARM100 ~/rap/SO-ARM100
```

Start from `~/rap/SO-ARM100/Simulation/SO101/so101_new_calib.urdf`; meshes are in `assets/`.

Basic:

- a package `so101_description` with `urdf/`, `meshes/`, `launch/`
- mesh paths `assets/*.stl` become `package://so101_description/meshes/…`
- upstream `base_link` has an `<inertial>`: add an empty `base_link` root above it
- delete the `<transmission>` blocks (ROS 1)
- RViz2 shows the arm, the sliders move all joints

Advanced:

- a `prefix` argument on every link and joint; two arms side by side
- `camera_link` and `camera_optical_frame` on the gripper. Optical joint:
  `rpy="${radians(-90)} 0 ${radians(-90)}"`. The mount STL is in mm: `scale="0.001 0.001 0.001"`

## Task 3: The tree

```bash
urdf_to_graphviz /tmp/so101.urdf /tmp/so101
ros2 run tf2_tools view_frames
```

Why are the two pictures different? Stop the sliders and run `view_frames` again.

## If stuck

| Symptom                   | Cause                                   |
| ------------------------- | --------------------------------------- |
| `Failed to find link`   | misspelt parent or child                |
| xacro tags left in output | `xmlns:xacro` missing                 |
| meshes missing            | relative path, or not installed         |
| `No transform from …`  | no `/joint_states`: start the sliders |
| one part huge             | mm mesh without scale                   |
