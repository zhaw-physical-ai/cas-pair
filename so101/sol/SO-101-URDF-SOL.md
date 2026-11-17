# Solutions for the so-101 URDF tasks

Look after you have tried.

| Path | What |
|---|---|
| `urdf/checkpoint1/pendulum.urdf` | slide 17: box + cylinder, one revolute joint |
| `urdf/checkpoint2/pendulum.urdf.xacro` | slide 46: `link_segment` macro, `two_arms:=true` |
| `urdf/so101_description/` | task 2: complete package, prefix and wrist camera |

## Task 3

`urdf_to_graphviz` draws the file. `view_frames` draws what is published now: without
`/joint_states` only the fixed joints appear and the tree splits at every moving joint.

## Meshes

Not in git. Copy them from the upstream clone (task 2) before building:

```bash
mkdir -p so101/sol/urdf/so101_description/meshes
cp ~/rap/SO-ARM100/Simulation/SO101/assets/*.stl so101/sol/urdf/so101_description/meshes/
```
