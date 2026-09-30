# Everything a terminal needs to talk to the Go2.  Source it, do not run it:
#
#     source ~/go2env.sh
#
# It finds your workspace by looking for the built Unitree messages under ~/repos.
# If you keep yours somewhere else, say so before sourcing:
#
#     export GO2_WS=~/somewhere/else/ros_ws
#     source ~/go2env.sh

source /opt/ros/jazzy/setup.bash

if [ -z "$GO2_WS" ]; then
  _hits=$(find "$HOME" -maxdepth 6 -type d -path '*/install/unitree_api' 2>/dev/null)
  _n=$(printf '%s' "$_hits" | grep -c .)
  if [ "$_n" -gt 1 ]; then
    echo "go2env: found $_n workspaces with the Unitree messages:"
    printf '%s\n' "$_hits" | sed 's|/install/unitree_api||; s|^|          |'
    echo "        using the first. To choose: export GO2_WS=<one of them>"
  fi
  [ -n "$_hits" ] && GO2_WS=$(dirname "$(dirname "$(printf '%s\n' "$_hits" | head -1)")")
  unset _hits _n
fi

if [ -n "$GO2_WS" ] && [ -f "$GO2_WS/install/setup.bash" ]; then
  source "$GO2_WS/install/setup.bash"
else
  echo "go2env: no workspace with the Unitree messages found."
  echo "        Build them (task 1), or: export GO2_WS=~/path/to/your/ros_ws"
fi

export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# The port to the dog is whichever one holds a 192.168.123.x address. Found by
# address, not by name, so a USB adapter (enx...) works too.
IFACE=$(ip -o -4 addr show | awk '$4 ~ /^192\.168\.123\./ {print $2; exit}')
if [ -n "$IFACE" ]; then
  export CYCLONEDDS_URI="<CycloneDDS><Domain><General><Interfaces><NetworkInterface name=\"$IFACE\"/></Interfaces></General></Domain></CycloneDDS>"
  echo "go2env: ros=jazzy  ws=${GO2_WS:-none}  iface=$IFACE"
else
  echo "go2env: no 192.168.123.x address - the dog's cable is not up. Fix that first."
fi
