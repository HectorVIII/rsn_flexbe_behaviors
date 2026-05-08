"""Semantic state for moving to the detected handover pose."""

from flexbe_core import EventState
from rsn_flexbe_behaviors.states.trigger_service_state import TriggerServiceState


class MoveToHandState(EventState):
    """
    Moves the xArm to the detected handover pose.

    -- timeout_sec     float  Maximum time to wait for service/result.
    -- retry_count     int    Retries after success=False responses.
    -- retry_delay_sec float  Delay between retries.

    #> response_message string  Service response message.

    <= done                    Move succeeded.
    <= failed                  Move failed.
    <= unavailable             Service was unavailable or timed out.
    """

    def __init__(self, timeout_sec=29.0, retry_count=19, retry_delay_sec=1.0):
        """Initialize the move-to-hand state."""
        super().__init__(
            outcomes=['done', 'failed', 'unavailable'],
            output_keys=['response_message']
        )
        self._delegate = TriggerServiceState(
            '/move_to_hand',
            timeout_sec=timeout_sec,
            retry_count=retry_count,
            retry_delay_sec=retry_delay_sec
        )

    def on_enter(self, userdata):
        """Enter the delegated service state."""
        self._delegate.on_enter(userdata)

    def execute(self, userdata):
        """Execute the delegated service state."""
        return self._delegate.execute(userdata)
