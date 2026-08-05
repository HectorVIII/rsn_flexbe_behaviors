"""Semantic state for moving the xArm to the preload staging pose."""

from flexbe_core import EventState
from rsn_flexbe_behaviors.states.trigger_service_state import TriggerServiceState


class MoveToStagingState(EventState):
    """
    Move the xArm to the preload 'waiting' pose above the current instrument
    (i.e. the tool that instrument_detection just localised).

    Requires FlexBE to have run StartInstrumentDetection for the predicted
    tool first so xarm_controller_node.latest_instrument_pose points at it.

    -- timeout_sec float   Maximum time to wait for service/result.

    #> response_message string  Service response message.

    <= done                    Move succeeded.
    <= failed                  Move failed.
    <= unavailable             Service was unavailable or timed out.
    """

    def __init__(self, timeout_sec=30.0):
        """Initialize the move-to-staging state."""
        super().__init__(
            outcomes=['done', 'failed', 'unavailable'],
            output_keys=['response_message']
        )
        self._delegate = TriggerServiceState(
            '/move_to_staging',
            timeout_sec=timeout_sec
        )

    def on_enter(self, userdata):
        """Enter the delegated service state."""
        self._delegate.on_enter(userdata)

    def execute(self, userdata):
        """Execute the delegated service state."""
        return self._delegate.execute(userdata)
