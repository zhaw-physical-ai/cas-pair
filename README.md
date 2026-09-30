# CAS Physical AI - lab material

Robots, the machines that drive them, and the tasks. Two labs share the same hardware:
a Unitree Go2 quadruped, and an SO-101 arm pair.

## Start here

Every lab runs on a Jetson Orin Nano with a screen, keyboard and mouse - one per group.

**[`JETSONS-SETUP.md`](JETSONS-SETUP.md)** - which machine is yours, how to reach it, what is
already on it, and how to shut it down. Read this before either lab.

## The labs

| | |
|---|---|
| **[`go2/`](go2/)** | the quadruped: drive it from your own code, visualize it, record it, avoid obstacles |
| **[`so101/`](so101/)** | the arm pair: teleoperation, imitation learning, and ROS control |

Each folder has a task description, and a `sol/` folder with hints and commands for when you
get stuck.

[`LINKS.md`](LINKS.md) has the tools and upstream repositories both labs use.

## Where you work

On the Jetson, in a folder of your own - the machines are shared:

```
mkdir -p ~/repos/cas_26_YOUR_NAME
```

Clone your repos there. Push your work: the machines are reimaged between courses, and
anything only on a Jetson is temporary.

## What is not here

The robots themselves are not toys. Both labs have a safety section - read it before anything
moves, and keep a remote control in your hand.