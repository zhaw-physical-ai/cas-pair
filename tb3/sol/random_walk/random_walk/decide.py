"""The decision, without ROS: which way to drive, given a scan.

Kept apart from the node so it can be tested with plain pytest - no simulator, no rclpy.
"""
import math


def nearest_ahead(angle_min, angle_increment, ranges, range_min, range_max, half_angle):
    """Closest valid range within +-half_angle (rad) of straight ahead, or None.

    Rays are selected by angle, not by index: index 0 is not always straight ahead, and
    the number of rays differs between the simulated and the real lidar.
    """
    nearest = None
    for i, r in enumerate(ranges):
        if not (range_min <= r <= range_max):   # also drops inf and NaN
            continue
        a = angle_min + i * angle_increment
        a = math.atan2(math.sin(a), math.cos(a))   # wrap to [-pi, pi]: 0..2pi scans
        if abs(a) <= half_angle and (nearest is None or r < nearest):
            nearest = r
    return nearest


def next_turn(turn, nearest, stop_distance, clear_distance, pick_direction):
    """Turn direction for this tick: 0 drives on, +1 turns left, -1 turns right.

    Hysteresis: a turn starts below stop_distance and ends only above clear_distance,
    and keeps the direction it picked at the start. That is what stops the wriggle.
    None (nothing valid ahead, e.g. all rays beyond range_max) counts as clear.
    """
    if turn:
        return 0 if nearest is None or nearest > clear_distance else turn
    if nearest is not None and nearest < stop_distance:
        return pick_direction()
    return 0
