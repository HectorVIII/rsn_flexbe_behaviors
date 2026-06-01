"""Semantic state for moving to the detected instrument."""

from flexbe_core import EventState
from rsn_flexbe_behaviors.states.trigger_service_state import TriggerServiceState


class MoveToInstrumentState(EventState):
    """
    Moves the xArm to the detected instrument pose.

    -- timeout_sec     float  Maximum time to wait for service/result.

    #> response_message string  Service response message.

    <= done                    Move succeeded.
    <= failed                  Move failed.
    <= unavailable             Service was unavailable or timed out.
    """

    def __init__(self, timeout_sec=10.0):
        """Initialize the move-to-instrument state."""
        super().__init__(
            outcomes=['done', 'failed', 'unavailable'],
            output_keys=['response_message']
        )
        self._delegate = TriggerServiceState(
            '/move_to_instrument',
            timeout_sec=timeout_sec
        )

    def on_enter(self, userdata):
        """Enter the delegated service state."""
        self._delegate.on_enter(userdata)

    def execute(self, userdata):
        """Execute the delegated service state."""
        return self._delegate.execute(userdata)
