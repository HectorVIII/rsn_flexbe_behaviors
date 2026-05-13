"""Semantic state for visual-servo alignment to the instrument."""

from flexbe_core import EventState
from rsn_flexbe_behaviors.states.trigger_service_state import TriggerServiceState


class VisualServoToInstrumentState(EventState):
    """
    Aligns the xArm to the detected instrument target pose.

    This first version is a placeholder service boundary for future
    closed-loop visual servoing. The low-level service currently descends from
    hover to the target pose using the latest or cached instrument pose.

    -- timeout_sec float   Maximum time to wait for service/result.

    #> response_message string  Service response message.

    <= done                    Alignment succeeded.
    <= failed                  Alignment failed.
    <= unavailable             Service was unavailable or timed out.
    """

    def __init__(self, timeout_sec=10.0):
        """Initialize the visual-servo-to-instrument state."""
        super().__init__(
            outcomes=['done', 'failed', 'unavailable'],
            output_keys=['response_message']
        )
        self._delegate = TriggerServiceState(
            '/visual_servo_to_instrument',
            timeout_sec=timeout_sec
        )

    def on_enter(self, userdata):
        """Enter the delegated service state."""
        self._delegate.on_enter(userdata)

    def execute(self, userdata):
        """Execute the delegated service state."""
        return self._delegate.execute(userdata)
