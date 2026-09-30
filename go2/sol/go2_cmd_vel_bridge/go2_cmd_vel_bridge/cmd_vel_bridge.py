"""Bridge geometry_msgs/Twist on cmd_vel to the Unitree Go2 sport API."""

import json
import signal
import time

from geometry_msgs.msg import Twist
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.signals import SignalHandlerOptions
from unitree_api.msg import Request

# Sport API ids (see unitree_ros2/example/src/include/common/ros2_sport_client.h)
ROBOT_SPORT_API_ID_STOPMOVE = 1003
ROBOT_SPORT_API_ID_MOVE = 1008


def clamp(value, limit):
    return max(-limit, min(limit, value))


class CmdVelBridge(Node):

    def __init__(self):
        super().__init__('go2_cmd_vel_bridge')

        self.declare_parameter('cmd_vel_topic', 'cmd_vel')
        self.declare_parameter('request_topic', '/api/sport/request')
        self.declare_parameter('max_vx', 0.3)     # m/s
        self.declare_parameter('max_vy', 0.2)     # m/s
        self.declare_parameter('max_vyaw', 0.6)   # rad/s
        self.declare_parameter('timeout', 1.0)    # s without cmd_vel -> StopMove
        self.declare_parameter('rate', 10.0)      # Hz, resend of the last Move

        cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        request_topic = self.get_parameter('request_topic').value
        self.max_vx = self.get_parameter('max_vx').value
        self.max_vy = self.get_parameter('max_vy').value
        self.max_vyaw = self.get_parameter('max_vyaw').value
        self.timeout = self.get_parameter('timeout').value
        rate = self.get_parameter('rate').value

        self.pub = self.create_publisher(Request, request_topic, 10)
        self.sub = self.create_subscription(Twist, cmd_vel_topic, self.on_cmd_vel, 10)

        self.last_cmd_time = None
        self.last_move = None  # (vx, vy, vyaw) while moving, None when stopped
        # teleop_twist_keyboard only publishes on a key press, so the last Move
        # is resent at a fixed rate until a zero Twist or the timeout.
        self.create_timer(1.0 / rate, self.tick)

        self.get_logger().info(
            f'Forwarding {cmd_vel_topic} -> {request_topic} (timeout {self.timeout}s)')

    def on_cmd_vel(self, msg: Twist):
        vx = clamp(msg.linear.x, self.max_vx)
        vy = clamp(msg.linear.y, self.max_vy)
        vyaw = clamp(msg.angular.z, self.max_vyaw)
        self.last_cmd_time = self.get_clock().now()

        if vx == 0.0 and vy == 0.0 and vyaw == 0.0:
            self.stop()
            return

        self.last_move = (vx, vy, vyaw)
        self.send_move()

    def send_move(self):
        vx, vy, vyaw = self.last_move
        req = Request()
        req.header.identity.api_id = ROBOT_SPORT_API_ID_MOVE
        req.parameter = json.dumps({'x': vx, 'y': vy, 'z': vyaw})
        self.pub.publish(req)

    def stop(self, force=False):
        if self.last_move is None and not force:
            return
        req = Request()
        req.header.identity.api_id = ROBOT_SPORT_API_ID_STOPMOVE
        self.pub.publish(req)
        self.last_move = None

    def tick(self):
        if self.last_move is None:
            return
        elapsed = (self.get_clock().now() - self.last_cmd_time).nanoseconds * 1e-9
        if elapsed > self.timeout:
            self.get_logger().warn('cmd_vel timeout, sending StopMove')
            self.stop()
            return
        self.send_move()


def _raise_keyboard_interrupt(signum, frame):
    raise KeyboardInterrupt


def main(args=None):
    # Keep rclpy from shutting the context down on Ctrl+C: we still need it to
    # publish the final StopMove. SIGTERM (e.g. closing the terminal / launch)
    # takes the same path.
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    signal.signal(signal.SIGINT, _raise_keyboard_interrupt)
    signal.signal(signal.SIGTERM, _raise_keyboard_interrupt)
    signal.signal(signal.SIGHUP, _raise_keyboard_interrupt)
    node = CmdVelBridge()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if rclpy.ok():
            node.get_logger().info('Exiting, sending StopMove')
            # Always send it, even if we think we are stopped, and a few
            # times so it reaches the robot before the publisher goes away.
            for _ in range(3):
                node.stop(force=True)
                time.sleep(0.05)
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
