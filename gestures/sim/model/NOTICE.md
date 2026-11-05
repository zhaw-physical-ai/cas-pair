# Model credits

`so101.xml` and `assets/*.stl`: SO-101 arm from [MuJoCo Menagerie](https://github.com/google-deepmind/mujoco_menagerie/tree/main/robotstudio_so101)
(`robotstudio_so101`, commit 98a70c5), itself derived from
[TheRobotStudio/SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100/tree/main/Simulation/SO101).
Both are Apache-2.0, see [`LICENSE`](LICENSE).

Changes made here:
- meshes decimated (pymeshlab quadric edge collapse: at most 2500 faces per visual mesh, 600 per
  collision mesh; 18 MB -> 1.7 MB). Unused meshes dropped.
- `so101.xml` unchanged.
- `scene.xml` is new: table, floor, cube, target square.
