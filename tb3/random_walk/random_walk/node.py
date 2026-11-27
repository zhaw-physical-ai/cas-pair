"""random_walk: drive forward, turn away from obstacles, never drive blind.

Store, then act: the scan callback only stores the latest scan and when it arrived. A timer
decides and publishes - so it also notices when scans stop arriving, and sends zero.
"""
import math
import random

import rclpy
from geometry_msgs.msg import TwistStamped
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from sensor_msgs.msg import LaserScan

from random_walk.decide import nearest_ahead, next_turn


class RandomWalk(Node):

    def __init__(self):
        super().__init__('random_walk')
        self.declare_parameter('forward_speed', 0.15)      # m/s, burger max is 0.22
        self.declare_parameter('turn_speed', 1.0)          # rad/s
        self.declare_parameter('stop_distance', 0.5)       # m, start turning below this
        self.declare_parameter('clear_distance', 0.7)      # m, stop turning above this
        self.declare_parameter('half_angle_deg', 30.0)     # "ahead" = +-30 deg
        self.declare_parameter('scan_timeout', 0.5)        # s without a scan -> zero
        self.declare_parameter('rate_hz', 10.0)
        self.p = {n: self.get_parameter(n).value for n in (
            'forward_speed', 'turn_speed', 'stop_distance', 'clear_distance',
            'half_angle_deg', 'scan_timeout', 'rate_hz')}

        # TODO: a publisher of TwistStamped on the relative topic 'cmd_vel'

        # TODO: a subscription to LaserScan on 'scan' that calls self.on_scan, with
        # qos_profile_sensor_data - the real robot's lidar publishes best effort

        # The watchdog runs on a steady clock, not ROS time: with use_sim_time a stopped
        # simulator also stops ROS time, and a timer on it would never fire to say so.
        self.steady = Clock(clock_type=ClockType.STEADY_TIME)
        # TODO: a timer that calls self.tick every 1 / rate_hz seconds, on clock=self.steady

        self.scan = None
        self.scan_at = None
        self.turn = 0

    def on_scan(self, msg):
        # TODO: store the scan, and when it arrived (self.steady.now()). Nothing else.
        pass

    def tick(self):
        p = self.p
        # TODO: no scan yet, or the last one older than scan_timeout: self.turn = 0, send zero,
        # return. (self.steady.now() - self.scan_at).nanoseconds * 1e-9 is its age in seconds.

        s = self.scan
        nearest = nearest_ahead(s.angle_min, s.angle_increment, s.ranges,
                                s.range_min, s.range_max, math.radians(p['half_angle_deg']))
        turn = next_turn(self.turn, nearest, p['stop_distance'], p['clear_distance'],
                         lambda: random.choice((-1, 1)))
        if turn != self.turn:
            self.get_logger().info(f'nearest ahead {nearest}: turn {turn}')
        self.turn = turn

        # TODO: turning: send zero forward speed and turn * turn_speed. Otherwise drive forward.

    def send(self, linear, angular):
        msg = TwistStamped()
        # TODO: fill in msg.header.stamp (the node's clock, now, as a message) and
        # msg.header.frame_id = 'base_link'

        # TODO: the velocities go in msg.twist: linear.x in m/s, angular.z in rad/s

        # TODO: publish it


def main(args=None):
    # TODO: rclpy.init, without ROS's own signal handler (SignalHandlerOptions.NO). With it,
    # Ctrl+C shuts ROS down before your `finally` runs, the stop below goes nowhere, and the
    # robot keeps driving its last command.
    node = RandomWalk()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        # TODO: send the stop, then destroy the node and shut down (rclpy.try_shutdown)
        pass


if __name__ == '__main__':
    main()
