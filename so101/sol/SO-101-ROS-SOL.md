

# ros2 with so101

## Set up
Clone relevant packages
```
mkdir -p ~/repos/cas_26_YOUR_NAME/ros_ws/src
cd ~/repos/cas_26_YOUR_NAME/ros_ws/src
git clone https://github.com/ros-physical-ai/ros2_so_arm.git
git clone https://github.com/JafarAbdi/feetech_ros2_driver.git

```

Compile packages
```
cd ~/repos/cas_26_YOUR_NAME/ros_ws
rosdep install --from-paths src --ignore-src -r -y

source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
source install/setup.bash

```

## Simple Ros task

Visualize arm in rviz
```
ros2 launch so_arm101_description view_description.launch.py rviz:=true
```


Control the joints individually (be careful)
```
ros2 launch so_arm101_description controllers_bringup.launch.py \
  hardware_type:=real usb_port:=/dev/ttyACM0
```

```
ros2 run rqt_joint_trajectory_controller rqt_joint_trajectory_controller
```

Check the joint states
```
ros2 topic echo /joint_states
```

Start Moveit ( you might have to debug why something is not working)
```
ros2 launch so_arm101_description controllers_bringup.launch.py   hardware_type:=real usb_port:=/dev/ttyACM0
```