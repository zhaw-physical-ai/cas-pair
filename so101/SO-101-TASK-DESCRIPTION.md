# High level task description for so-101

## Task 1: Teleoperation and Imitation learning
Basic:
- set up the two arms
- connect with jetson
- calibrate it
- teleoperate it with the lerobot library

Advanced:
- collect data samples and push to hugging face
- train a policy on runpod
- run trained policy on arm
  
Hints:
- mkdir -p ~/repos/cas_26_YOUR_NAME # clone your repos here
- use the lerobot library (https://huggingface.co/docs/lerobot/so101)
- use uv as python package manager


## Task 2: Steer robot with ROS
Basic:
- visualize arm in rivz
- control the joints individually with simple ros controller
- echo the joint states


Advanced:
- get the MoveIt package running to contro lthe robot


Hints:

```
mkdir -p ~/repos/cas_26_YOUR_NAME/ros_ws/src
cd ~/repos/cas_26_YOUR_NAME/ros_ws/src
git clone https://github.com/ros-physical-ai/ros2_so_arm.git
git clone https://github.com/JafarAbdi/feetech_ros2_driver.git

```