# Task 3: Move the dog with ROS

Every terminal needs the environment first - `source ~/go2env.sh`, or the block in
`GO2-TASK1-SETUP-SOL.md`. A terminal without it shows empty topic lists and unknown types.

Setup first: `GO2-TASK1-SETUP-SOL.md`. Remote in your hand, 2-3 m clear.

#ATTENTION: the Go2 keeps executing the last velocity it was given. If your node stops
sending, crashes, or its terminal closes, the dog keeps walking. `L2+B` on the remote is the
stop that always works.

## Look before you build

```
ros2 node list
ros2 topic list
ros2 topic info /api/sport/request -v
ros2 interface show unitree_api/msg/Request
```

The dog is not a ROS node - it speaks DDS without running `rcl` - so `ros2 node list` shows
your nodes, not the robot's. The topics are real all the same.

## Drive it from the command line, before any code

Everything a walk command needs is in one `ros2 topic pub`. **api_id 1008 is Move**, and
`parameter` is a JSON string with forward, sideways and yaw-rate.

#ATTENTION: dog standing and woken with `Start` on the remote, remote in your hand,
2-3 m clear. There is no
watchdog here - whatever you publish, the dog keeps doing.

```
ros2 topic pub -r 10 -t 20 /api/sport/request unitree_api/msg/Request \
  "{header: {identity: {api_id: 1008}}, parameter: '{\"x\": 0.2, \"y\": 0.0, \"z\": 0.0}'}"
```

`-r 10` sends at 10 Hz, `-t 20` sends twenty messages and exits - about two seconds of
walking. The full long form, if you want to see every field:

```
ros2 topic pub -r 10 /api/sport/request unitree_api/msg/Request 'header:
  identity:
    id: 0
    api_id: 1008
  lease:
    id: 0
  policy:
    priority: 0
    noreply: false
parameter: "{\"x\": 0.2, \"y\": 0.0, \"z\": 0.0}"
binary: []'
```

**And the stop. Learn this one first, not second:**

```
ros2 topic pub -1 /api/sport/request unitree_api/msg/Request \
  "{header: {identity: {api_id: 1003}}}"
```

api_id **1003 is StopMove**. Note what happens when the `-t 20` run finishes, or when you
Ctrl+C the `-r 10` one: the publishing stops and **the dog carries on walking**, because
nothing told it otherwise. That is the lesson the whole task is built on, and it is why the
node in the advanced part needs a watchdog.

`L2+B` on the remote is always there and always works. Use it.

## Why the command line works and teleop does not

The difference is the topic and the type:

|                           | topic                  | type                        | who listens       |
| ------------------------- | ---------------------- | --------------------------- | ----------------- |
| `ros2 topic pub`        | `/api/sport/request` | `unitree_api/msg/Request` | **the dog** |
| `teleop_twist_keyboard` | `/cmd_vel`           | `geometry_msgs/Twist`     | nobody            |

The dog has never heard of `/cmd_vel` and does not know what a `Twist` is. Nothing in ROS
connects two topics by itself. So teleop publishes into a topic with no other end, and the
messages simply stop there.

They can see it rather than take it on faith:

```
ros2 topic info /cmd_vel
```

With teleop running and no bridge: `Publisher count: 1`, `Subscription count: 0`. That zero
is the entire explanation, and it is the reason the next section exists.

## Write your own go2 bridge

(there exists a solution but try it first to solve it on your own)

**The bridge is a ROS node that subscribes to `/cmd_vel` and publishes to
`/api/sport/request`.** That is the whole job: it is the only thing in the system that knows
both languages. It takes the `geometry_msgs/Twist` teleop produces and turns each one into the
`unitree_api/msg/Request` the dog understands - the same message you sent by hand with
`ros2 topic pub`, just built in code and sent continuously.

```
teleop_twist_keyboard  ->  /cmd_vel  ->  your bridge  ->  /api/sport/request  ->  the dog
      Twist                              (translator)          Request
```

Once it runs, `ros2 topic info /cmd_vel` shows `Subscription count: 1` - that subscriber is
your node, and it is the link that was missing.

What you write is the node in between. It has to:

- subscribe to `geometry_msgs/Twist` on `/cmd_vel`
- publish `unitree_api/msg/Request` on `/api/sport/request`
- fill `header.identity.api_id` and `parameter`
- **api_id 1008** is Move, **api_id 1003** is StopMove
- for Move, `parameter` is a JSON string: `{"x": <forward>, "y": <sideways>, "z": <yaw rate>}`
- resend the last command at about 10 Hz, because `teleop_twist_keyboard` only publishes on a
  key press - otherwise the dog gets one message and stops
- send StopMove when no `Twist` has arrived for about a second, and on a zero `Twist`
- clamp the speeds: 0.3 m/s forward, 0.2 sideways, 0.6 rad/s turning is plenty
- send StopMove when the node exits, and make sure Ctrl+C does not kill the ROS context
  before that message is actually on the wire

Look at the message first:

```
ros2 interface show unitree_api/msg/Request
```

## Running the dog

**Start the bridge before teleop.** ROS discovery is dynamic, so the other order does connect
eventually  Bridge first, check`ros2 topic info /cmd_vel` reads 1 and 1, then the keyboard.

### 1. Starting your node

Two ways, depending on how you wrote it. Both need `source ~/go2env.sh` in that terminal
first.

**A single file** - quickest to get going:

```
python3 ~/repos/cas_26_YOUR_NAME/my_bridge.py
```

**A package** - what you want once there is more than one node:

```
ros2 run <your_package> <your_executable>
```

### 2. Starting Teleopartion

(this is a package you don't have to write it yourselfe)

```
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Hold `i` / `,` to walk, `j` / `l` to turn, `k` to stop. It publishes `geometry_msgs/Twist` on
`/cmd_vel` and nothing else. **A Go2 has no `/cmd_vel`**, so on its own this moves nothing.

The two names are the **package** and the **executable**, and the executable is whatever your
`setup.py` lists under `console_scripts` - often not the file name. `ros2 pkg executables <your_package>` prints it. If `ros2 run` says the package is not found, you have not sourced
the workspace you built it in.

## ! If nothing moves

**Ask the dog.** It answers every request, and the answer says whether it accepted it:

```
ros2 topic echo /api/sport/response
```

#ATTENTION: this is a *reply* topic, not a state topic. On its own it prints **nothing** -
the dog only publishes here when it has just answered a request. Leave it running in one
terminal and send a command from another; the replies appear as you send.

| `status.code` | meaning                                                        |
| --------------- | -------------------------------------------------------------- |
| `0`           | accepted - if it still did not move, look at your parameters   |
| `-1`          | **refused.** The message was fine; the robot declined it |

A `-1` is a robot-state problem, not a code problem. In order:

1. **Press `Start` on the remote.** On 30 Sep 2026 this was the difference between every Move
   being refused with `-1` and the dog walking. Nothing in ROS shows you this is needed
2. **Disconnect the phone app.** It takes priority over the API and everything gets refused
3. **Check the remote is talking to this dog** - `ros2 topic echo /wirelesscontroller`, then
   press buttons and watch for values

#ATTENTION: **do not trust the `mode` field.** It is tempting, and on 30 Sep 2026 it read `0`
on a dog that was standing at `body_height: 0.31` and walking on command. Earlier notes claim
`0 = idle` and `1 = balance stand`; that did not hold on this robot. `/api/sport/response` is
the reliable signal - use it and ignore the number.

## If you are stuck: a working node

Try it yourself first - the whole point of the task is in the writing. This is here so that a
group does not lose the afternoon.

There is a full ROS package version in [`go2_cmd_vel_bridge/`](go2_cmd_vel_bridge) - copy it
into a workspace and build it:

```
cp -r go2_cmd_vel_bridge ~/repos/cas_26_YOUR_NAME/ros_ws/src/
cd ~/repos/cas_26_YOUR_NAME/ros_ws
colcon build --packages-select go2_cmd_vel_bridge \
  --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
source install/setup.bash

ros2 run go2_cmd_vel_bridge cmd_vel_bridge --ros-args -r /api/sport/request:=/dryrun
```

It does everything the listing below does, and three things more that are worth copying into
your own version:

- **it handles SIGHUP as well as SIGINT and SIGTERM**, so closing the terminal stops the dog.
  Ctrl+C is not the only way a node dies
- **it sends StopMove three times, 50 ms apart, on the way out** - once is not reliable when
  the publisher is about to disappear
- **everything is a ROS parameter** - topics, speed caps, timeout, resend rate - so you can
  retune it with `--ros-args -p max_vx:=0.5` instead of editing code

The version below is the smallest thing that works, and is easier to read first.

```python
#!/usr/bin/env python3
"""Turn /cmd_vel into Go2 sport-mode Move requests."""
import json

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from unitree_api.msg import Request

MOVE = 1008
STOPMOVE = 1003


def clamp(value, limit):
    return max(-limit, min(limit, value))


class Bridge(Node):
    def __init__(self):
        super().__init__('go2_bridge')
        self.pub = self.create_publisher(Request, '/api/sport/request', 10)
        self.create_subscription(Twist, '/cmd_vel', self.on_cmd_vel, 10)
        # teleop_twist_keyboard only publishes on a key press, so resend the
        # last command at 10 Hz for as long as it is fresh.
        self.create_timer(0.1, self.tick)
        self.cmd = (0.0, 0.0, 0.0)
        self.last = None
        self.moving = False
        self.get_logger().info('bridge up: /cmd_vel -> /api/sport/request')

    def on_cmd_vel(self, msg):
        self.cmd = (clamp(msg.linear.x, 0.3),
                    clamp(msg.linear.y, 0.2),
                    clamp(msg.angular.z, 0.6))
        self.last = self.get_clock().now()

    def tick(self):
        if self.last is None:
            return
        stale = (self.get_clock().now() - self.last).nanoseconds / 1e9 > 1.0
        if stale or self.cmd == (0.0, 0.0, 0.0):
            if self.moving:
                self.send(STOPMOVE)
                self.moving = False
                self.get_logger().info('stop')
            return
        x, y, z = self.cmd
        self.send(MOVE, json.dumps({'x': x, 'y': y, 'z': z}))
        self.moving = True

    def send(self, api_id, parameter=''):
        req = Request()
        req.header.identity.api_id = api_id
        req.parameter = parameter
        self.pub.publish(req)


def main():
    # Keep the context alive through Ctrl+C so the final StopMove can go out.
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = Bridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.send(STOPMOVE)
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
```


# Troubleshooting

The bridge runs, teleop runs, the dog does not move:

- does the bridge print or publish anything about a second after you tap `i`? If not, the
  keyboard is not reaching it - check `ros2 topic hz /cmd_vel`
- is it still remapped to `/dryrun`? `ros2 node info <your_node>` shows what it publishes
- has the dog been stood up and woken with `Start`? Check `/api/sport/response` - `-1`
  means it was refused, not that your message was wrong
- is a phone app connected? It takes priority

The dog keeps walking after you stop your node:

- your StopMove never went out. Ctrl+C tears down the ROS context by default, and a message
  published after that goes nowhere

Nothing in `ros2 topic list`, or types show as unknown:

- see `GO2-TASK1-SETUP-SOL.md`, the troubleshooting there covers it
