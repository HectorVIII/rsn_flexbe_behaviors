"""Mock zed_hand_node replacement for RSN FlexBE dry tests."""

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger


class MockHandNode(Node):
    """Provide hand-detection services without opening the ZED camera."""

    def __init__(self):
        """Create mock hand services."""
        super().__init__('rsn_flexbe_mock_hand_node')
        self.create_service(
            Trigger,
            'start_hand_detection',
            self._handle_start_hand_detection
        )
        self.create_service(
            Trigger,
            'move_to_hand',
            self._handle_move_to_hand
        )
        self.get_logger().info('RSN FlexBE mock hand node is ready.')

    def _handle_start_hand_detection(self, request, response):
        del request
        response.success = True
        response.message = 'Mock hand detection started'
        self.get_logger().info(response.message)
        return response

    def _handle_move_to_hand(self, request, response):
        del request
        response.success = True
        response.message = 'Mock move to hand succeeded'
        self.get_logger().info(response.message)
        return response


def main(args=None):
    """Run the mock hand node."""
    rclpy.init(args=args)
    node = MockHandNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
