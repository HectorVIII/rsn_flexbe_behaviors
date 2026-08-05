"""Read the latest WorkflowState from workflow_state_estimator.

Extracts predicted_next_tool and writes it to userdata.target_class so the
downstream preload chain (StartInstrumentDetection + MoveToStaging) can act
on it.

Returns 'no_prediction' when the estimator has nothing to preload
(end-of-workflow), or when the /workflow_state topic yields no message
within timeout_sec (typical cause: estimator not launched). In either case
the SM should fall back to the plain 'Return To P0' path.
"""

from flexbe_core import EventState, Logger
from rclpy.qos import QoSProfile, QoSDurabilityPolicy, QoSReliabilityPolicy

from rsn_interfaces.msg import WorkflowState


class QueryPredictedNextState(EventState):
    """
    Query workflow_state_estimator for the next tool to preload.

    -- timeout_sec float   Max time to wait for the first message.

    #> target_class string  Predicted next tool (empty when no prediction).

    <= has_prediction   predicted_next_tool was non-empty.
    <= no_prediction    Estimator reports empty prediction, or timed out
                        waiting for the first message.
    """

    WORKFLOW_STATE_TOPIC = '/workflow_state'

    def __init__(self, timeout_sec=2.0):
        """Initialize the query state."""
        super().__init__(
            outcomes=['has_prediction', 'no_prediction'],
            output_keys=['target_class']
        )
        self._timeout_sec = float(timeout_sec)
        self._workflow_sub = None
        self._latest = None
        self._start_time = None

    def on_enter(self, userdata):
        """Reset cache and connect subscriber on first entry."""
        userdata.target_class = ''
        self._latest = None
        self._start_time = self._now()
        if self._workflow_sub is None:
            qos = QoSProfile(
                depth=1,
                reliability=QoSReliabilityPolicy.RELIABLE,
                durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
            )
            self._workflow_sub = EventState._node.create_subscription(
                WorkflowState, self.WORKFLOW_STATE_TOPIC, self._cb, qos
            )

    def execute(self, userdata):
        """Return once we have a message or the timeout fires."""
        if self._latest is not None:
            msg = self._latest
            self._latest = None
            tool = (msg.predicted_next_tool or '').strip()
            if tool:
                userdata.target_class = tool
                Logger.loginfo(
                    f'Preload target from estimator: {tool!r} '
                    f'(step={msg.current_step_id})'
                )
                return 'has_prediction'
            Logger.loginfo(
                f'Estimator reports no prediction (step={msg.current_step_id}); '
                'falling back to Return To P0.'
            )
            return 'no_prediction'

        if self._now() - self._start_time > self._timeout_sec:
            Logger.logwarn(
                f'Timeout waiting for {self.WORKFLOW_STATE_TOPIC}; '
                'assuming no prediction '
                '(estimator not running?).'
            )
            return 'no_prediction'
        return None

    def _cb(self, msg):
        self._latest = msg

    @staticmethod
    def _now():
        return EventState._node.get_clock().now().nanoseconds * 1e-9
