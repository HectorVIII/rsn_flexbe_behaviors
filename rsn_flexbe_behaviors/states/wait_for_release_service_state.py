"""Semantic state for waiting for release detection."""

from flexbe_core import EventState
from rsn_flexbe_behaviors.states.trigger_service_state import TriggerServiceState


class WaitForReleaseState(EventState):
    """
    Waits until release is detected by the xArm force-torque sensor.

    -- timeout_sec float   Maximum time to wait for service/result.

    #> response_message string  Service response message.

    <= done                    Release was detected.
    <= failed                  Release failed or timed out in the xArm node.
    <= unavailable             Service was unavailable or timed out.
    """

    def __init__(self, timeout_sec=120.0):
        """Initialize the wait-for-release state."""
        super().__init__(
            outcomes=['done', 'failed', 'unavailable'],
            output_keys=['response_message']
        )
        self._delegate = TriggerServiceState(
            '/wait_for_release',
            timeout_sec=timeout_sec
        )

    def on_enter(self, userdata):
        """Enter the delegated service state."""
        self._delegate.on_enter(userdata)

    def execute(self, userdata):
        """Execute the delegated service state."""
        return self._delegate.execute(userdata)
