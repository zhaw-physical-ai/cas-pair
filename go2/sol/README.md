# Solutions and hints for the Go2 tasks

Guidance, not answers. Each task below says how to approach it, what the robot will do to you
along the way, and which file has the commands.

**No node code here, on purpose.** Tasks 2 and 5 ask you to write a node, and writing it is
the point. If you are stuck on the programming itself rather than on the robot, come and ask -
working code exists and you will be handed it. Come with what you tried.

| file | covers |
|---|---|
| [`GO2-TASK1-SETUP-SOL.md`](GO2-TASK1-SETUP-SOL.md) | install ROS, build the Unitree messages, cable up, talk to the dog |
| [`GO2-TASK2-DRIVE-SOL.md`](GO2-TASK2-DRIVE-SOL.md) | teleop, the bridge node, the dry run, the modes |
| [`GO2-TASK3-TOOLS-SOL.md`](GO2-TASK3-TOOLS-SOL.md) | topics, rviz, Foxglove and Lichtblick |
| [`GO2-TASK4-BAGS-SOL.md`](GO2-TASK4-BAGS-SOL.md) | record, replay, comparing the two |
| [`GO2-TASK5-OBSTACLES-SOL.md`](GO2-TASK5-OBSTACLES-SOL.md) | the lidar, filtering, stopping in time |
| [`GO2-REPOS-SOL.md`](GO2-REPOS-SOL.md) | what to pull, and what not to |

## How to approach each task

### Task 1 - set up ROS and talk to the dog

Do it in this order, and check each step before the next. Most of the lost time in this task
comes from debugging three things at once.

1. **Cable and address before ROS.** `ping 192.168.123.161` has to answer. If it does not, no
   amount of ROS will help.
2. **ROS installed and running at all.** `ros2 topic list` in a terminal with nothing else set
   should at least not error.
3. **The middleware.** The dog does not speak your default. Until you match it you get an
   empty list, which looks exactly like a switched-off robot.
4. **The message types.** Once topics appear, their types still have to be built or everything
   shows as unknown.

A robot that answers `ping` is not a robot ready to talk ROS - its network comes up in
seconds, its ROS topics take substantially longer. Wait before you conclude anything.

### Task 2 - move the dog with ROS

The trap is assuming the interface. Look at what the dog actually offers before you write a
line: `ros2 topic list`, then `ros2 topic info` and `ros2 interface show` on anything that
sounds like a command.

Then build it in this order:

1. **Work out the message.** What exactly does a walk command look like? Read the interface
   definition, not a tutorial for another robot.
2. **Dry-run it.** Send your messages to a harmless topic and echo them. You should be able to
   see, in plain text, that holding a key produces a stream of move commands and releasing it
   produces one stop. Get this right before the dog is involved at all.
3. **Then the robot.** Short commands, low speeds, remote in your hand.

Three things the robot will do to you:

- **it only accepts movement in one of its modes.** Everything can be correct and nothing
  moves. Its mode is published - watch it
- **the keyboard tool only sends on a key press.** One message is not a walk
- **silence is not a stop.** Whatever you write, make it stop the dog when it exits - and
  assume one day it will not exit cleanly

### Task 3 - use the tools

Start from the data, not from the tool. List the topics, pick one number that changes when the
robot moves, and get that number on screen. Then open a second tool and put the same number on
screen there. The comparison is the task.

Do not spend an hour trying to make a 3D view draw a dog. A real Go2 publishes no model and no
transform tree, so it never will - that is a fact about the robot, not a mistake you made.

### Task 4 - record and replay

Record a short, simple route the first time - a few metres and one turn. Record few topics:
the lidar alone will fill the disk faster than you expect.

Then replay it, and **stand back**: nothing downstream can tell a replayed command from a live
one, so the dog walks with nobody touching a key.

The interesting part is not that it works, it is where the differences come from. Look at what
you commanded against what the robot measured. If the two do not line up at all on a time
axis, look at the timestamps before you blame your code.

### Task 5 - avoid obstacles

Build it in layers and test each one without the robot moving:

1. **Can you read the lidar at all?** Print how many points arrive per message. If nothing
   arrives, it is almost certainly the quality-of-service settings, not your maths
2. **Which way is forward?** Do not assume. Put something in front of the dog and look at
   which coordinate changes
3. **Can you count the points in a box in front?** Print the count, walk a chair towards the
   dog by hand, and watch the number rise. Still no movement involved
4. **Now act on it.** Stop first. Turning away is the next step, not the first one

The floor is also points, and so are the dog's own legs. A filter that ignores height will
find an obstacle everywhere.

Drive through the node you wrote in task 2 rather than talking to the robot's API again. If
your layering is right this is a few lines; if it is wrong, you will notice here.
