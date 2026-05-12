"""Semantic state for grasping and immediately lifting an instrument."""

from flexbe_core import EventState
from rsn_flexbe_behaviors.states.trigger_service_state import TriggerServiceState


class GraspAndLiftState(EventState):
    """
    Closes the xArm gripper and lifts the instrument as one low-level action.

    -- timeout_sec float   Maximum time to wait for service/result.

    #> response_message string  Service response message.

    <= done                    Grasp-and-lift succeeded.
    <= failed                  Grasp or lift failed.
    <= unavailable             Service was unavailable or timed out.
    """

    def __init__(self, timeout_sec=10.0):
        """Initialize the grasp-and-lift state."""
        super().__init__(
            outcomes=['done', 'failed', 'unavailable'],
            output_keys=['response_message']
        )
        self._delegate = TriggerServiceState(
            '/grasp_and_lift',
            timeout_sec=timeout_sec
        )

    def on_enter(self, userdata):
        """Enter the delegated service state."""
        self._delegate.on_enter(userdata)

    def execute(self, userdata):
        """Execute the delegated service state."""
        return self._delegate.execute(userdata)
