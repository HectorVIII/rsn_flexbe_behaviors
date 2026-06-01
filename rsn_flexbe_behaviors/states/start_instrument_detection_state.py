"""Semantic state for starting instrument detection."""

from action_msgs.msg import GoalStatus
from flexbe_core import EventState, Logger
from flexbe_core.proxy import ProxyActionClient
from rsn_interfaces.action import DetectInstrument


class StartInstrumentDetectionState(EventState):
    """
    Runs instrument detection for the current voice target.

    -- action_topic string Action topic to call.
    -- timeout_sec  float  Maximum time to wait for action result.

    ># target_class     string  Target class received from voice.
    #> response_message string  Service response message.

    <= done                    Detection finished and published a pose.
    <= failed                  Detection failed.
    <= unavailable             Action server was unavailable or timed out.
    """

    def __init__(self, action_topic='/start_instrument_detection', timeout_sec=30.0):
        """Initialize the start-instrument-detection state."""
        super().__init__(
            outcomes=['done', 'failed', 'unavailable'],
            input_keys=['target_class'],
            output_keys=['response_message']
        )
        self._action_topic = action_topic
        self._timeout_sec = float(timeout_sec)
        self._client = None
        self._start_time = None
        self._sent = False

    def on_enter(self, userdata):
        """Send the detection action goal when the server is available."""
        userdata.response_message = ''
        self._start_time = self._now()
        self._sent = False

        if self._client is None:
            if ProxyActionClient._node is None:
                ProxyActionClient.initialize(EventState._node)
            self._client = ProxyActionClient(
                {self._action_topic: DetectInstrument},
                wait_duration=0.0
            )

        ProxyActionClient.remove_result(self._action_topic)
        ProxyActionClient.remove_feedback(self._action_topic)
        self._send_goal_if_available(userdata)

    def execute(self, userdata):
        """Wait for the action result and map it to a FlexBE outcome."""
        if self._timed_out():
            userdata.response_message = (
                f'Timeout waiting for {self._action_topic}'
            )
            if self._sent and ProxyActionClient.is_active(self._action_topic):
                ProxyActionClient.cancel(self._action_topic)
            return 'unavailable'

        if not self._sent:
            self._send_goal_if_available(userdata)
            return None

        if ProxyActionClient.has_feedback(self._action_topic):
            feedback = ProxyActionClient.get_feedback(self._action_topic)
            ProxyActionClient.remove_feedback(self._action_topic)
            if hasattr(feedback, 'feedback'):
                feedback = feedback.feedback
            Logger.loginfo(
                'Instrument detection feedback: '
                f'{feedback.state} '
                f'({feedback.stable_frames}/'
                f'{feedback.stable_frames_required})'
            )

        if not ProxyActionClient.has_result(self._action_topic):
            return None

        status = self._get_action_status()
        result = ProxyActionClient.get_result(self._action_topic)
        ProxyActionClient.remove_result(self._action_topic)
        userdata.response_message = result.message

        if status != GoalStatus.STATUS_SUCCEEDED:
            Logger.logwarn(
                f'Instrument detection action ended with status={status}: '
                f'{result.message}'
            )
            return 'failed'

        if result.success:
            Logger.loginfo(
                f'Instrument detection succeeded: {result.message}'
            )
            return 'done'

        Logger.logwarn(f'Instrument detection failed: {result.message}')
        return 'failed'

    def on_exit(self, userdata):
        """Cancel the action if the state exits while it is still active."""
        if self._sent and ProxyActionClient.is_active(self._action_topic):
            ProxyActionClient.cancel(self._action_topic)

    def _send_goal_if_available(self, userdata):
        if not ProxyActionClient.is_available(self._action_topic):
            Logger.logwarn(f'Action {self._action_topic} is not available.')
            return

        goal = DetectInstrument.Goal()
        goal.target_class = str(userdata.target_class).strip()
        goal.timeout_sec = float(self._timeout_sec)
        ProxyActionClient.send_goal(
            self._action_topic,
            goal,
            wait_duration=0.001
        )
        self._sent = True
        Logger.loginfo(
            f'Sent instrument detection action goal for: {goal.target_class}'
        )

    def _get_action_status(self):
        if hasattr(ProxyActionClient, 'get_status'):
            return ProxyActionClient.get_status(self._action_topic)
        return ProxyActionClient.get_state(self._action_topic)

    def _timed_out(self):
        return self._now() - self._start_time > self._timeout_sec

    @staticmethod
    def _now():
        return EventState._node.get_clock().now().nanoseconds * 1e-9
