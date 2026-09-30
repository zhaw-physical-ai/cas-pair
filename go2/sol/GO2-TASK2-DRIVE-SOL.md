# Task 2: Move the dog with ROS

Setup first: `GO2-TASK1-SETUP-SOL.md`. Remote in your hand, 2-3 m clear.

#ATTENTION: the Go2 keeps executing the last velocity it was given. If your node stops
sending, crashes, or its terminal closes, the dog keeps walking. `L2+B` on the remote is the
stop that always works.


## The keyboard is a package, the bridge is yours

```
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Hold `i` / `,` to walk, `j` / `l` to turn, `k` to stop. It publishes `geometry_msgs/Twist` on
`/cmd_vel` and nothing else. **A Go2 has no `/cmd_vel`**, so on its own this moves nothing.

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

## Dry run before the dog moves

Remap the command topic so nothing reaches the robot:

```
ros2 run <your_pkg> <your_node> --ros-args -r /api/sport/request:=/dryrun
```

in a second terminal:

```
ros2 topic echo /dryrun
```

Holding a key gives `api_id: 1008` repeatedly. Releasing it gives **nothing at first** -
`teleop_twist_keyboard` sends only on a key press, so your node sees silence - and then one
`api_id: 1003` once your watchdog fires, about a second later.

That second of delay is the whole point of the task. The dog does not stop on its own; it
stops because *your* node noticed the silence and said so. Get this visible in the dry run
before the robot is involved.

When that is right, drop the remap and run it for real.

## If nothing moves

```
ros2 topic echo /lf/sportmodestate --field mode
```

| value | meaning | walks? |
|---|---|---|
| 0 | idle | no |
| 1 | balance stand | **yes** |
| 5 | lie down | no - from Unitree's docs, not confirmed here |
| 7 | damping | no |

`L2+B` drops the dog into damping, `L2+A` stands it back up. The dog ignores Move in every
mode but balance stand, and looks broken while doing it.

Also check the dog's own answer:

```
ros2 topic echo /api/sport/response
```

# Troubleshooting

The bridge runs, teleop runs, the dog does not move:
- does the bridge print or publish anything about a second after you tap `i`? If not, the
  keyboard is not reaching it - check `ros2 topic hz /cmd_vel`
- is it still remapped to `/dryrun`? `ros2 node info <your_node>` shows what it publishes
- is the dog in balance stand? See the mode table above
- is a phone app connected? It takes priority

The dog keeps walking after you stop your node:
- your StopMove never went out. Ctrl+C tears down the ROS context by default, and a message
  published after that goes nowhere

Nothing in `ros2 topic list`, or types show as unknown:
- see `GO2-TASK1-SETUP-SOL.md`, the troubleshooting there covers it
