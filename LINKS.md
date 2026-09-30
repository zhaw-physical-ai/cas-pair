# Links and tools

Tools both labs can use. **Not instructions** - what to install, and in what order, is in the
task files themselves.

## Viewers - either lab

| | |
|---|---|
| [Lichtblick](https://github.com/lichtblick-suite/lichtblick) | desktop app, connects to `foxglove_bridge`. **No account needed** - start here |
| [Foxglove Studio](https://foxglove.dev) | the same thing, but **requires signing up for an account** before you can use it |

Both speak the same websocket, so one bridge serves either.

## Other tools people use - either lab

Not part of either lab. If you want to go further, these are where to start:

| | |
|---|---|
| [PlotJuggler](https://github.com/facontidavide/PlotJuggler) | plotting values over time; needs no frames or transforms |
| [RosBoard](https://github.com/dheera/rosboard) | a web dashboard - nothing to install on the machine you look from |
| [rqt](https://docs.ros.org/en/jazzy/Concepts/Intermediate/About-RQt.html) | the standard ROS plugin GUI, already installed with `ros-jazzy-desktop` |

## Reference

- [SO-101 instructions](so101/SO-101-TASK-DESCRIPTION.md) and
  [Go2 instructions](go2/GO2-TASK-DESCRIPTION.md)

- [ROS 2 Jazzy installation](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)
- [rosbag2](https://docs.ros.org/en/jazzy/Tutorials/Beginner-CLI-Tools/Recording-And-Playing-Back-Data/Recording-And-Playing-Back-Data.html)
- [tf2 static transforms](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Static-Broadcaster-Py.html)
