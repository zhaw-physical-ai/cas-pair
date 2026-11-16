"""The decision logic, without ROS: python3 -m pytest test/ from the package folder."""
import math

from random_walk.decide import nearest_ahead, next_turn

INF = float('inf')
HALF = math.radians(30)


def scan_360(obstacles):
    """A 360-ray scan from 0 to 2pi (like the TB3 LDS), all inf except {deg: range}."""
    r = [INF] * 360
    for deg, dist in obstacles.items():
        r[deg % 360] = dist
    return dict(angle_min=0.0, angle_increment=math.radians(1), ranges=r,
                range_min=0.12, range_max=3.5, half_angle=HALF)


def test_nothing_ahead():
    assert nearest_ahead(**scan_360({})) is None


def test_ahead_on_both_sides_of_zero():
    # 0..2pi scan: "ahead" wraps around - index 350 is 10 deg to the right
    assert nearest_ahead(**scan_360({350: 0.4})) == 0.4
    assert nearest_ahead(**scan_360({10: 0.6, 350: 0.4})) == 0.4


def test_outside_the_cone_is_ignored():
    assert nearest_ahead(**scan_360({90: 0.2, 180: 0.2})) is None


def test_invalid_ranges_are_ignored():
    assert nearest_ahead(**scan_360({0: 0.05, 1: float('nan'), 2: 9.0})) is None


def test_symmetric_scan_minus_pi_to_pi():
    # the same check must work when the driver publishes -pi..pi
    r = [INF] * 360
    r[180] = 0.3   # angle 0
    assert nearest_ahead(-math.pi, math.radians(1), r, 0.12, 3.5, HALF) == 0.3


def test_hysteresis_no_wriggle():
    left = lambda: 1   # noqa: E731
    assert next_turn(0, 1.0, 0.5, 0.7, left) == 0
    assert next_turn(0, 0.4, 0.5, 0.7, left) == 1     # starts turning
    assert next_turn(1, 0.6, 0.5, 0.7, left) == 1     # between: keeps turning
    assert next_turn(-1, 0.4, 0.5, 0.7, left) == -1   # keeps its own direction
    assert next_turn(1, 0.8, 0.5, 0.7, left) == 0     # clear: drives again
    assert next_turn(1, None, 0.5, 0.7, left) == 0
