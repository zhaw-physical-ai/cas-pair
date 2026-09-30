# Everything a terminal needs to talk to the Go2.  Source it, do not run it:
#
#     source ~/go2env.sh
#
# Set WS to your own workspace - the one holding the built Unitree messages.
WS="$HOME/repos/cas_26_johm/jazzy_test"

source /opt/ros/jazzy/setup.bash
[ -f "$WS/install/setup.bash" ] && source "$WS/install/setup.bash" \
  || echo "go2env: no workspace at $WS/install - edit WS in this file"

export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# The port to the dog is whichever one holds a 192.168.123.x address. Found by
# address, not by name, so a USB adapter (enx...) works too.
IFACE=$(ip -o -4 addr show | awk '$4 ~ /^192\.168\.123\./ {print $2; exit}')
if [ -n "$IFACE" ]; then
  export CYCLONEDDS_URI="<CycloneDDS><Domain><General><Interfaces><NetworkInterface name=\"$IFACE\"/></Interfaces></General></Domain></CycloneDDS>"
  echo "go2env: ros=jazzy  ws=$WS  iface=$IFACE"
else
  echo "go2env: no 192.168.123.x address - the dog's cable is not up. Fix that first."
fi
