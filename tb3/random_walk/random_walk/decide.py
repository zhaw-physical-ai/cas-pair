"""The decision, without ROS: which way to drive, given a scan.

Kept apart from the node so it can be tested with plain pytest - no simulator, no rclpy:
    cd ~/rap/ros2_ws/src/<...>/random_walk && python3 -m pytest test/
"""
import math


def nearest_ahead(angle_min, angle_increment, ranges, range_min, range_max, half_angle):
    """Closest valid range within +-half_angle (rad) of straight ahead, or None.

    Rays are selected by angle, not by index: index 0 is not always straight ahead, and
    the number of rays differs between the simulated and the real lidar.
    """
    nearest = None
    for i, r in enumerate(ranges):
        # TODO: skip invalid ranges: outside [range_min, range_max]. That check also drops
        # inf and NaN.

        # TODO: the angle of ray i, from angle_min and angle_increment, wrapped to [-pi, pi]:
        # math.atan2(math.sin(a), math.cos(a)). The TurtleBot3 scan runs 0..2pi, so without
        # the wrap a ray just right of straight ahead is at almost 2pi.

        # TODO: within +-half_angle and closer than the nearest so far: keep it
        pass
    return nearest


def next_turn(turn, nearest, stop_distance, clear_distance, pick_direction):
    """Turn direction for this tick: 0 drives on, +1 turns left, -1 turns right.

    turn is the direction of the last tick. pick_direction() returns -1 or +1 at random.

    Hysteresis: a turn starts below stop_distance and ends only above clear_distance,
    and keeps the direction it picked at the start. That is what stops the wriggle.
    None (nothing valid ahead, e.g. all rays beyond range_max) counts as clear.
    """
    # TODO: already turning: keep turning in the same direction, until clear

    # TODO: not turning: start a turn when something is closer than stop_distance. Its
    # direction comes from pick_direction() - random, not always the same side

    return 0
