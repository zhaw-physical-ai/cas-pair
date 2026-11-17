from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    model = PathJoinSubstitution([FindPackageShare('so101_description'), 'urdf', 'so101.urdf.xacro'])
    description = ParameterValue(
        Command(['xacro ', model,
                 ' prefix:=', LaunchConfiguration('prefix'),
                 ' two_arms:=', LaunchConfiguration('two_arms')]),
        value_type=str)

    return LaunchDescription([
        DeclareLaunchArgument('prefix', default_value=''),
        DeclareLaunchArgument('two_arms', default_value='false'),
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'robot_description': description}]),
        Node(package='joint_state_publisher_gui', executable='joint_state_publisher_gui'),
        Node(package='rviz2', executable='rviz2'),
    ])
