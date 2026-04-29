"""Launch mock services for RSN FlexBE dry tests."""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    """Generate the mock dry-test launch description."""
    return LaunchDescription([
        Node(
            package='rsn_flexbe_behaviors',
            executable='mock_core_services_node',
            name='rsn_flexbe_mock_core_services',
            output='screen'
        ),
    ])
