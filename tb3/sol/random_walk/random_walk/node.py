"""random_walk: drive forward, turn away from obstacles, never drive blind.

Store, then act: the scan callback only stores the latest scan and when it arrived. A timer
decides and publishes - so it also notices when scans stop arriving, and sends zero.
"""
import math
import random

import rclpy
from geometry_msgs.msg import Twist, TwistStamped
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
        self.declare_parameter('stamped', True)            # Jazzy sim: TwistStamped
        p = {n: self.get_parameter(n).value for n in (
            'forward_speed', 'turn_speed', 'stop_distance', 'clear_distance',
            'half_angle_deg', 'scan_timeout', 'rate_hz', 'stamped')}
        self.p = p

        # Relative names: namespaces and remapping apply. Sensor QoS connects to the real
        # robot's best-effort lidar driver as well as to the reliable Gazebo bridge.
        self.pub = self.create_publisher(
            TwistStamped if p['stamped'] else Twist, 'cmd_vel', 10)
        self.sub = self.create_subscription(
            LaserScan, 'scan', self.on_scan, qos_profile_sensor_data)

        # The watchdog runs on a steady clock, not ROS time: with use_sim_time a stopped
        # simulator also stops ROS time, and a timer on it would never fire to say so.
        self.steady = Clock(clock_type=ClockType.STEADY_TIME)
        self.timer = self.create_timer(1.0 / p['rate_hz'], self.tick, clock=self.steady)
        self.scan = None
        self.scan_at = None
        self.turn = 0

    def on_scan(self, msg):
        self.scan = msg
        self.scan_at = self.steady.now()

    def tick(self):
        p = self.p
        if self.scan_at is None or \
                (self.steady.now() - self.scan_at).nanoseconds * 1e-9 > p['scan_timeout']:
            if self.turn or self.scan_at is not None:
                self.get_logger().warn('no recent scan - stopping', throttle_duration_sec=2.0)
            self.turn = 0
            self.send(0.0, 0.0)
            return

        s = self.scan
        nearest = nearest_ahead(s.angle_min, s.angle_increment, s.ranges,
                                s.range_min, s.range_max, math.radians(p['half_angle_deg']))
        turn = next_turn(self.turn, nearest, p['stop_distance'], p['clear_distance'],
                         lambda: random.choice((-1, 1)))
        if turn != self.turn:
            self.get_logger().info(
                f'nearest ahead {nearest}: ' + ('drive' if turn == 0 else
                                                'turn ' + ('left' if turn > 0 else 'right')))
        self.turn = turn
        if turn:
            self.send(0.0, turn * p['turn_speed'])
        else:
            self.send(p['forward_speed'], 0.0)

    def send(self, linear, angular):
        if self.p['stamped']:
            msg = TwistStamped()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = 'base_link'
            t = msg.twist
        else:
            msg = t = Twist()
        t.linear.x = linear
        t.angular.z = angular
        self.pub.publish(msg)


def main(args=None):
    # No ROS signal handler: by default Ctrl+C shuts the context down before we get a
    # chance to publish. Here it arrives as KeyboardInterrupt, the stop goes out, then
    # shutdown. The robot keeps its last command otherwise.
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = RandomWalk()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.send(0.0, 0.0)
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
