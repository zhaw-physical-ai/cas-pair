"""ros2 launch random_walk random_walk.launch.py stop_distance:=0.8"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('stop_distance', default_value='0.5'),
        # TODO: launch arguments for the other parameters you want to set from the command line

        Node(
            package='random_walk',
            executable='random_walk',
            output='screen',
            parameters=[{
                # TODO: pass each launch argument on as a parameter. A launch argument is a
                # string; the node declared a float. Wrap it:
                # ParameterValue(LaunchConfiguration(...), value_type=float)
            }],
        ),
    ])
