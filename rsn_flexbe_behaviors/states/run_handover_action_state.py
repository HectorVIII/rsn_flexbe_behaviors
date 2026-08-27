"""FlexBE state: run one handover episode via the L2 BT action server.

Wrapper over the /run_handover action exposed by handover_bt_node.
Uses the same ProxyActionClient class-method pattern as the other
action-driven states in this package (start_hand_detection_state.py).

Outcomes
--------
- ``released``  Handover succeeded (result.reason == "released").
- ``canceled``  Goal was canceled.
- ``failed``    Any other failure.
"""

from action_msgs.msg import GoalStatus
from flexbe_core import EventState, Logger
from flexbe_core.proxy import ProxyActionClient
from std_msgs.msg import String

from rsn_interfaces.action import RunHandover


class RunHandoverActionState(EventState):
    """
    Drive one L2 handover BT episode.

    -- action_topic     string  Action name.
    -- timeout_sec      float   Per-episode timeout passed to the BT
                                (0 means use BT node's default).
    -- source_slot      string  Optional grasp_table slot override.

    ># tool_name        string  Instrument to hand over.
    #> reason           string  Final result.reason from the BT.
    """

    def __init__(
        self,
        action_topic='/run_handover',
        timeout_sec=0.0,
        source_slot='',
        operator_topic='/rsn/operator_cmd',
    ):
        super().__init__(
            outcomes=['released', 'canceled', 'failed'],
            input_keys=['tool_name'],
            output_keys=['reason'],
        )
        self._action_topic = action_topic
        self._timeout_sec = float(timeout_sec)
        self._source_slot = source_slot
        self._operator_topic = operator_topic
        self._client = None
        self._sent = False
        self._last_phase = ''
        self._op_sub = None
        # Set by the subscription; consumed by execute() to trigger a cancel.
        self._cancel_requested = False

    # ------------------------------------------------------------------
    def on_enter(self, userdata):
        userdata.reason = ''
        self._sent = False
        self._last_phase = ''
        self._cancel_requested = False

        # Subscribe once (per state instance) to the operator channel so
        # a spoken "cancel" while a handover is running preempts the goal.
        if self._op_sub is None:
            try:
                self._op_sub = EventState._node.create_subscription(
                    String, self._operator_topic, self._on_op_msg, 10
                )
            except Exception as exc:  # pylint: disable=broad-except
                Logger.logwarn(
                    f'Subscribe {self._operator_topic} failed: {exc}'
                )

        if self._client is None:
            if ProxyActionClient._node is None:
                ProxyActionClient.initialize(EventState._node)
            self._client = ProxyActionClient(
                {self._action_topic: RunHandover},
                wait_duration=0.0,
            )

        ProxyActionClient.remove_result(self._action_topic)
        ProxyActionClient.remove_feedback(self._action_topic)

        if not ProxyActionClient.is_available(self._action_topic):
            Logger.logwarn(
                f'Action {self._action_topic} is not available.'
            )
            return

        goal = RunHandover.Goal()
        goal.tool_name = str(getattr(userdata, 'tool_name', '') or '').strip()
        goal.source_slot = self._source_slot
        goal.timeout_sec = self._timeout_sec

        try:
            ProxyActionClient.send_goal(self._action_topic, goal)
            self._sent = True
            Logger.loginfo(f"Handover start: tool='{goal.tool_name}'")
        except Exception as exc:  # pylint: disable=broad-except
            Logger.logerr(f'send_goal failed: {exc}')

    # ------------------------------------------------------------------
    def execute(self, userdata):
        if not self._sent:
            userdata.reason = 'aborted'
            return 'failed'

        # Operator "cancel" arrived while the handover was running: send
        # one cancel and keep polling — final outcome comes from the
        # action result (reason='canceled').
        if self._cancel_requested:
            self._cancel_requested = False
            if ProxyActionClient.is_active(self._action_topic):
                try:
                    ProxyActionClient.cancel(self._action_topic)
                    Logger.loginfo('Operator cancel: sent cancel to /run_handover.')
                except Exception as exc:  # pylint: disable=broad-except
                    Logger.logwarn(f'Operator cancel failed: {exc}')

        if ProxyActionClient.has_feedback(self._action_topic):
            fb = ProxyActionClient.get_feedback(self._action_topic)
            ProxyActionClient.remove_feedback(self._action_topic)
            if hasattr(fb, 'feedback'):
                fb = fb.feedback
            phase = getattr(fb, 'phase', '') or ''
            progress = float(getattr(fb, 'progress', 0.0) or 0.0)
            if phase and phase != self._last_phase:
                self._last_phase = phase
                Logger.loginfo(
                    f'Handover phase -> {phase} ({int(progress * 100)} pct)'
                )

        if not ProxyActionClient.has_result(self._action_topic):
            return None

        status = self._get_action_status()
        result = ProxyActionClient.get_result(self._action_topic)
        ProxyActionClient.remove_result(self._action_topic)
        reason = getattr(result, 'reason', '') or ''
        userdata.reason = reason

        if status == GoalStatus.STATUS_CANCELED or reason == 'canceled':
            Logger.logwarn('Handover canceled.')
            return 'canceled'

        if getattr(result, 'success', False):
            Logger.loginfo(f'Handover done: {reason}')
            return 'released'

        # retreat_failed: tool was actually delivered + released; only the
        # arm's return leg failed. Don't block the workflow — surface a
        # warning but let the phase move on as if released.
        if reason == 'retreat_failed':
            Logger.logwarn(
                'Handover delivered but retreat failed — arm may not be at P0. '
                'Continuing.'
            )
            return 'released'

        Logger.logwarn(f'Handover failed: {reason}')
        return 'failed'

    # ------------------------------------------------------------------
    def on_exit(self, userdata):
        if self._sent and ProxyActionClient.is_active(self._action_topic):
            try:
                ProxyActionClient.cancel(self._action_topic)
                Logger.loginfo('Sent cancel on RunHandover exit.')
            except Exception as exc:  # pylint: disable=broad-except
                Logger.logwarn(f'cancel on exit failed: {exc}')

    # ------------------------------------------------------------------
    def _get_action_status(self):
        if hasattr(ProxyActionClient, 'get_status'):
            return ProxyActionClient.get_status(self._action_topic)
        return ProxyActionClient.get_state(self._action_topic)

    # ------------------------------------------------------------------
    def _on_op_msg(self, msg):
        cmd = (msg.data or '').strip().lower()
        if cmd == 'cancel':
            self._cancel_requested = True
