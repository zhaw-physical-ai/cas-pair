#!/bin/bash
# RunPod start command for the Summit XL simulation (image johnsmic/rap-pod).
#
# Template "Container Start Command":
#   bash -c 'curl -fsSL https://raw.githubusercontent.com/zhaw-physical-ai/cas-pair/main/summit/runpod_start.sh | bash'
#
# Runs the image's normal desktop start-up, with three changes for RunPod:
# - ~/rap is the pod's volume. RunPod mounts it as root, so hand it to the ros user.
# - x11vnc gets -noshm. The entrypoint starts it as root; when Xvfb (below) is the X server it
#   runs as ros, refuses root's shared memory, and x11vnc exits: noVNC "Failed to connect".
# - On some hosts the GPU Xorg dies with "no screens found". Then Xvfb on :0 takes over
#   (software rendering), and the entrypoint carries on with VNC, noVNC and XFCE.

sudo chown ros:ros /home/ros/rap
sudo sed -i '/-noshm/!s/-rfbport 5900/-noshm -rfbport 5900/' /etc/entrypoint.sh

(
  until [ -f /var/log/Xorg.0.log ]; do sleep 2; done   # Xorg has been started
  sleep 15
  [ -S /tmp/.X11-unix/X0 ] && exit 0                    # GPU Xorg is up, nothing to do

  echo "=== summit: GPU Xorg failed. Errors from /var/log/Xorg.0.log:"
  grep -E '\(EE\)|NVIDIA\(' /var/log/Xorg.0.log | head -30
  echo "=== summit: starting Xvfb on :0 instead (software rendering)"
  sudo apt-get update -qq && sudo apt-get install -y -qq xvfb >/dev/null
  Xvfb :0 -screen 0 1920x1080x24 +extension GLX -nolisten tcp -ac &
) &

# </dev/null: the entrypoint ends with `read`, which would otherwise swallow the next line of
# this piped script, and RunPod would restart the container in a loop.
/etc/entrypoint.sh 2>&1 </dev/null
sleep infinity
