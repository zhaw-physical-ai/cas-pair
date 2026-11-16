"""ros2 launch random_walk random_walk.launch.py stop_distance:=0.8 stamped:=false"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    args = {'stop_distance': '0.5', 'clear_distance': '0.7', 'forward_speed': '0.15',
            'stamped': 'true'}
    return LaunchDescription([
        *[DeclareLaunchArgument(n, default_value=v) for n, v in args.items()],
        Node(
            package='random_walk',
            executable='random_walk',
            output='screen',
            parameters=[{
                'stop_distance': ParameterValue(LaunchConfiguration('stop_distance'), value_type=float),
                'clear_distance': ParameterValue(LaunchConfiguration('clear_distance'), value_type=float),
                'forward_speed': ParameterValue(LaunchConfiguration('forward_speed'), value_type=float),
                'stamped': ParameterValue(LaunchConfiguration('stamped'), value_type=bool),
            }],
        ),
    ])
