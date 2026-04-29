"""Mock core Trigger services for RSN FlexBE dry tests."""

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger


class MockCoreServicesNode(Node):
    """Provide successful Trigger services without touching hardware."""

    SERVICES = [
        'move_to_p0',
        'open_gripper',
        'close_gripper',
        'start_instrument_detection',
        'move_to_instrument',
        'lift_after_grasp',
        'wait_for_release',
        'retreat_after_release',
    ]

    def __init__(self):
        """Create all dry-test service servers."""
        super().__init__('rsn_flexbe_mock_core_services')
        for service_name in self.SERVICES:
            self.create_service(
                Trigger,
                service_name,
                self._make_callback(service_name)
            )
        self.get_logger().info('RSN FlexBE mock core services are ready.')

    def _make_callback(self, service_name):
        def callback(request, response):
            del request
            response.success = True
            response.message = f'Mock success from /{service_name}'
            self.get_logger().info(response.message)
            return response

        return callback


def main(args=None):
    """Run the mock core service node."""
    rclpy.init(args=args)
    node = MockCoreServicesNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
