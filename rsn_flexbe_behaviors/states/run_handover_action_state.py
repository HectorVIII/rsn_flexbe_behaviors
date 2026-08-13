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
    ):
        super().__init__(
            outcomes=['released', 'canceled', 'failed'],
            input_keys=['tool_name'],
            output_keys=['reason'],
        )
        self._action_topic = action_topic
        self._timeout_sec = float(timeout_sec)
        self._source_slot = source_slot
        self._client = None
        self._sent = False
        self._last_phase = ''

    # ------------------------------------------------------------------
    def on_enter(self, userdata):
        userdata.reason = ''
        self._sent = False
        self._last_phase = ''

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
