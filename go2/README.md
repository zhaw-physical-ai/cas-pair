# The Go2

A Unitree Go2 quadruped, a Jetson on its back, and five tasks. By the end you should be able
to drive it from your own code, see what it sees, record what it did, and have it avoid
something.

Read [safety](#safety) before the robot moves. The rest you work out.

## Connecting to it

The Jetson talks to the dog over **Ethernet**, on a private network with no router and no
DHCP - the Go2 hands out no addresses, so you set yours by hand.

| | |
|---|---|
| The dog's main board | `192.168.123.161` |
| Your Jetson | `192.168.123.99/24` on the wired interface |

```bash
nmcli -t -f NAME,DEVICE con show                # find the wired profile
sudo nmcli con mod "<profile>" ipv4.method manual ipv4.addresses 192.168.123.99/24
sudo nmcli con up "<profile>"
ping -c2 192.168.123.161
```

A reply means the cable and the robot are fine. It does **not** mean the robot is ready to
talk ROS - that takes longer, and until then you will see almost no topics.

The wifi is separate and unrelated: it is how the Jetson reaches the internet and how you
reach the Jetson. The robot link never leaves the cable.

## Safety

- **A remote control in your hand, always.** `L2+B` damps the dog and it lies down softly.
  This is your stop, not the software.
- **2-3 m clear** around it, and nothing underneath.
- **The dog only accepts movement commands in some of its modes.** Lying down, damping or
  mid-transition it ignores them completely and looks broken. Its state is published - find
  it, watch it, and check it before you conclude your code is wrong.
- **Silence is not a stop.** The Go2 keeps executing the last velocity it was given until
  something tells it otherwise. If your program stops sending, or crashes, or its terminal
  closes, the dog keeps going. Whatever you write, make it send a stop when it exits - and
  keep the remote in your hand anyway.
- **Cap your speeds** while developing. 0.3 m/s forward and 0.6 rad/s turning is plenty and
  leaves you time to react.
- The phone app must not be connected while you are driving. It takes priority.

## Task 1 - get your Jetson ready

Your machine has git, Docker, uv, VS Code and nano on it. It has no ROS. Putting ROS on it is
the first task, and the first decision.

### Native, or in a container

**A ROS 2 distribution is tied to an Ubuntu version.** That is not a detail you can route
around - each release is built against one Ubuntu, and there are simply no packages for the
others.

| | |
|---|---|
| Your Jetson runs | Ubuntu 24.04 |
| The ROS 2 release for 24.04 | **Jazzy** |
| Humble targets | Ubuntu 22.04 |

So **natively, Jazzy is your only option.** There is no `ros-humble-*` package for this
machine and no amount of apt persuasion will produce one.

**A container changes that**, because it brings its own Ubuntu with it. Inside a
`ros:humble` image you are on 22.04 and Humble is simply there. So the real choice is:

- **Native Jazzy** - fewer moving parts, everything is where you expect it, and a mistake is
  yours to unpick. Fastest to a first result.
- **Humble (or Jazzy) in Docker** - the machine stays clean, you can throw a broken attempt
  away and start again, and the setup is reproducible on the next Jetson. More to learn first,
  and a container that cannot reach the robot is a new kind of confusing.

Either works with the dog. Neither is the "right" answer, but **pick one and stay with it** -
half a ROS on the host and half in a container is the one combination that wastes an
afternoon.

Two things your setup has to account for, whichever way you go:

- the dog speaks **CycloneDDS**, so your ROS has to as well
- it publishes and accepts **Unitree's own message types**, which you will have to build

**Done when:** `ros2 topic list` from your setup shows the robot's topics, and you can get
back to that same state in a new terminal tomorrow without guessing. Write down what you did.

## Task 2 - make it walk from your own code

Move the robot from a node you wrote.

The thing you will discover, and it is the point of the task:

- **there is no `/cmd_vel` on a Go2.** Walking is a request on its own API. Finding out what
  that request looks like, and turning a `geometry_msgs/Twist` into one, is the task

**Done when:** you press a key and the dog walks, and releasing it stops.

## Task 3 - see what it sees

Get a view of the robot's data. RViz, Foxglove Studio, Lichtblick - try more than one, they
are not equivalent.

Worth knowing before you spend an hour on it: a real Go2 publishes **no robot model and no
transform tree**. A 3D panel will not draw a dog. What it does publish is state, odometry and
lidar, and those you can plot and render.

**Done when:** you can watch a value change as the robot moves, and explain which tool you
would use for which job.

## Task 4 - record it and play it back

Record the robot doing something with `ros2 bag`, then replay it and watch it in RViz.

Record only the topics you need. The lidar alone will fill a disk faster than you expect, and
a bag you cannot copy off the machine is not much use.

Two things to think about:

- **replaying commands into a live robot makes it move.** Nothing can tell whether a message
  came from your keyboard or from a bag
- **check the timestamps.** They may not say what you assume

**Done when:** you can replay a route and show it in RViz, and say what differs between the
recording and the replay.

## Task 5 - avoid something

Write a node that stops or turns the dog before it hits an obstacle, using the lidar.

Start simple: points in front, closer than a threshold, stop. Then make it turn away instead.
Then decide what "in front" means, which is harder than it sounds.

**Advanced:** use the camera instead, and react to what something *is* rather than only how
far away it is.

**Done when:** you can walk the dog at a wall and it stops itself - with your hand on the
remote the first time.

## When something does not work

Most of it is one of these:

| symptom | usually |
|---|---|
| almost no topics | the robot is not ready yet, or your ROS is not on CycloneDDS |
| topics exist, nothing moves | the dog is in a mode that ignores commands |
| it worked, now it doesn't | something started before the robot, or before the cable - restart it |
| a node sees nothing | wrong `ROS_DOMAIN_ID`, or a stale `ros2 daemon` - try `--no-daemon` |

`ros2 topic list`, `ros2 topic echo`, `ros2 topic info -v` and `ros2 topic hz` will tell you
which. Use them before changing code.
