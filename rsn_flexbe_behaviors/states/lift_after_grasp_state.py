"""Semantic state for lifting the instrument after grasp."""

from flexbe_core import EventState
from rsn_flexbe_behaviors.states.trigger_service_state import TriggerServiceState


class LiftAfterGraspState(EventState):
    """
    Lifts the instrument after grasping it.

    -- timeout_sec float   Maximum time to wait for service/result.

    #> response_message string  Service response message.

    <= done                    Lift succeeded.
    <= failed                  Lift failed.
    <= unavailable             Service was unavailable or timed out.
    """

    def __init__(self, timeout_sec=10.0):
        """Initialize the lift-after-grasp state."""
        super().__init__(
            outcomes=['done', 'failed', 'unavailable'],
            output_keys=['response_message']
        )
        self._delegate = TriggerServiceState(
            '/lift_after_grasp',
            timeout_sec=timeout_sec
        )

    def on_enter(self, userdata):
        """Enter the delegated service state."""
        self._delegate.on_enter(userdata)

    def execute(self, userdata):
        """Execute the delegated service state."""
        return self._delegate.execute(userdata)
