#!/bin/bash
# RunPod start command for the TurtleBot3 simulation (image johnsmic/rap-pod, as in summit/).
#
# Template "Container Start Command":
#   bash -c 'curl -fsSL https://raw.githubusercontent.com/zhaw-physical-ai/cas-pair/main/tb3/runpod_start.sh | bash'
#
# The image is the Summit one, so the desktop start-up and its RunPod fixes are summit's
# runpod_start.sh, run at the end. This adds two things:
# - The TurtleBot3 packages. The image does not have them, and the container disk is reset
#   on every start, so they are installed in the background on each start (about 1-2 min).
# - The lab's environment in ~/.bashrc, so every desktop terminal has it.

grep -q '^# --- tb3 lab' /home/ros/.bashrc || cat >> /home/ros/.bashrc <<'EOF'

# --- tb3 lab (tb3/runpod_start.sh) ---
export TURTLEBOT3_MODEL=burger
export GZ_IP=127.0.0.1                         # Gazebo transport stays inside the pod
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST # ROS discovery stays inside the pod
[ -d /opt/ros/jazzy/share/turtlebot3_gazebo ] || \
  echo "TurtleBot3 is still installing - tail -f /tmp/tb3-install.log, then open a new terminal"
EOF

# Retried: the first index fetched at pod start can be stale (seen 2026-11-16: an install
# that asked for package versions no longer on packages.ros.org, 404). A second update fixes it.
(
  for try in 1 2 3; do
    sudo apt-get -o DPkg::Lock::Timeout=300 update -qq &&
    sudo apt-get -o DPkg::Lock::Timeout=300 install -y -qq \
      ros-jazzy-turtlebot3-gazebo ros-jazzy-turtlebot3-teleop &&
    { echo "=== tb3: TurtleBot3 installed"; exit 0; }
    echo "=== tb3: install attempt $try failed, retrying in 10 s"
    sleep 10
  done
  echo "=== tb3: install FAILED - run: sudo apt-get update && sudo apt-get install -y ros-jazzy-turtlebot3-gazebo ros-jazzy-turtlebot3-teleop"
) > /tmp/tb3-install.log 2>&1 &

curl -fsSL https://raw.githubusercontent.com/zhaw-physical-ai/cas-pair/main/summit/runpod_start.sh | bash
