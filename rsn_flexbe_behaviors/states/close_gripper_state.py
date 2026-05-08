"""Semantic state for closing the xArm gripper."""

from flexbe_core import EventState
from rsn_flexbe_behaviors.states.trigger_service_state import TriggerServiceState


class CloseGripperState(EventState):
    """
    Closes the xArm gripper.

    -- timeout_sec float   Maximum time to wait for service/result.

    #> response_message string  Service response message.

    <= done                    Gripper closed.
    <= failed                  Gripper command failed.
    <= unavailable             Service was unavailable or timed out.
    """

    def __init__(self, timeout_sec=10.0):
        """Initialize the close-gripper state."""
        super().__init__(
            outcomes=['done', 'failed', 'unavailable'],
            output_keys=['response_message']
        )
        self._delegate = TriggerServiceState(
            '/close_gripper',
            timeout_sec=timeout_sec
        )

    def on_enter(self, userdata):
        """Enter the delegated service state."""
        self._delegate.on_enter(userdata)

    def execute(self, userdata):
        """Execute the delegated service state."""
        return self._delegate.execute(userdata)
