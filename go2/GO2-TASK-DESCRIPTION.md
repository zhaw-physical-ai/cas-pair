# High level task description for go2

A Unitree Go2 quadruped with a Jetson on its back. Read **Safety** before the robot moves.

## Connecting to the dog

The Jetson talks to the dog over **Ethernet**, on a private network with no router and no
DHCP - the Go2 hands out no addresses, so you set yours by hand.

| | |
|---|---|
| The dog's main board | `192.168.123.161` |
| Your Jetson | `192.168.123.99/24` on the wired interface |

```
nmcli -t -f NAME,DEVICE con show                # find the wired profile
sudo nmcli con mod "<profile>" ipv4.method manual ipv4.addresses 192.168.123.99/24
sudo nmcli con up "<profile>"
ping -c2 192.168.123.161
```

A reply means the cable and the robot are fine. It does **not** mean the robot is ready to
talk ROS - that takes longer, and until then you will see almost no topics. The wifi is
separate: it is how you reach the Jetson. The robot link never leaves the cable.

## Safety

- **A remote control in your hand, always.** `L2+B` damps the dog and it lies down softly.
  This is your stop, not the software.
- **2-3 m clear** around it, and nothing underneath.
- **The dog only accepts movement commands in some of its modes.** Lying down, damping or
  mid-transition it ignores them completely and looks broken. Its state is published - find
  it, watch it, and check it before you conclude your code is wrong.
- **Silence is not a stop.** The Go2 keeps executing the last velocity it was given until
  something tells it otherwise. If your program stops sending, or crashes, or its terminal
  closes, the dog keeps going. Whatever you write, make it send a stop when it exits.
- **Cap your speeds** while developing. 0.3 m/s forward and 0.6 rad/s turning is plenty.
- The phone app must not be connected while you are driving. It takes priority.

## Task 1: Set up ROS and talk to the dog

Basic:
- install ROS 2 on the Jetson - natively or in a container, your choice
- connect the Jetson to the dog and ping the main board
- get `ros2 topic list` to show the robot's own topics
- echo the robot's state and watch it change as you move the dog with the remote

Advanced:
- be able to say why you chose native or container
- write down your setup so you can reproduce it in a new terminal tomorrow

Hints:
- `mkdir -p ~/repos/cas_26_YOUR_NAME` # clone your repos here
- a ROS 2 release is tied to an Ubuntu version. The Jetson runs 24.04, so **Jazzy** natively;
  Humble targets 22.04 and exists here only inside a container
- the dog speaks **CycloneDDS**, so your ROS has to as well
- it publishes and accepts **Unitree's own message types**, which you will have to build
  (https://github.com/unitreerobotics/unitree_ros2)
- an empty topic list is usually you, not the robot

## Task 2: Move the dog with ROS

Basic:
- move the robot from a node you wrote
- stop it when you let go of the key

Advanced:
- accept a standard `geometry_msgs/Twist` so the same node could drive a simulation
- cap the speeds in your own code, not just with your fingers

Hints:
- **there is no `/cmd_vel` on a Go2** - walking is a request on the dog's own API
- find out what that request looks like before you write anything
- test with the command topic remapped somewhere harmless first, and watch what you send
- the dog keeps walking if your node dies - make sure it sends a stop on the way out

## Task 3: Use the tools

Basic:
- visualize the robot's data in rviz
- try a second tool - Foxglove Studio or Lichtblick - and compare them
- plot a value while the robot moves

Advanced:
- say which tool you would use for which job, and why they are not equivalent

Hints:
- a real Go2 publishes **no robot model and no transform tree**, so nothing will draw a dog
- what it does publish is state, odometry and lidar
- Foxglove and Lichtblick connect over a websocket bridge you have to run on the Jetson

## Task 4: Record and replay

Basic:
- record the robot doing something with `ros2 bag`
- replay it and watch it in rviz

Advanced:
- compare the commanded motion with the measured one
- say what differs between the recording and the replay, and why

Hints:
- record only the topics you need - the lidar alone fills a disk faster than you expect
- **replaying commands into a live robot makes it move.** Nothing can tell whether a message
  came from your keyboard or from a bag
- check the timestamps. They may not say what you assume

## Task 5: Avoid obstacles

Basic:
- write a node that stops the dog before it hits something, using the lidar
- make it turn away instead of only stopping

Advanced:
- use the camera and react to what something *is*, not only how far away it is

Hints:
- start with: points in front, closer than a threshold, stop
- then decide what "in front" means, which is harder than it sounds
- the floor is also points
- publish to your own node from task 2 rather than talking to the dog's API directly
- **hand on the remote the first time** - a node that drives forward by itself is exactly the
  thing that walks into a wall while you are reading its output

## When something does not work

| symptom | usually |
|---|---|
| almost no topics | the robot is not ready yet, or your ROS is not on CycloneDDS |
| topics exist, nothing moves | the dog is in a mode that ignores commands |
| it worked, now it doesn't | something started before the robot, or before the cable - restart it |
| a node sees nothing | wrong `ROS_DOMAIN_ID`, or a stale `ros2 daemon` - try `--no-daemon` |

`ros2 topic list`, `ros2 topic echo`, `ros2 topic info -v` and `ros2 topic hz` will tell you
which. Use them before changing code.
