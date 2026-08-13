"""FlexBE state: wait for the next operator command in a phase.

Sources (whichever arrives first wins):

- ``/voice_target_instrument`` (std_msgs/String) — instrument name from
  voice_command_node. Ignored unless on this phase's ``allowed_tools``
  whitelist.

- ``/rsn/operator_cmd`` (std_msgs/String) — one of ``next`` / ``back``
  / ``done``.
"""

from flexbe_core import EventState, Logger
from std_msgs.msg import String


class WaitForOperatorCommandState(EventState):
    """
    Block until an operator command or a whitelisted tool request arrives.

    -- allowed_tools     list    Tool ids permitted in this phase.
    -- tool_topic        string  Voice instrument topic.
    -- operator_topic    string  Operator command topic.

    #> tool_name         string  Selected tool (raw casing preserved).
    """

    _OP_OUTCOMES = ('next', 'back', 'done')

    def __init__(
        self,
        allowed_tools=None,
        tool_topic='/voice_target_instrument',
        operator_topic='/rsn/operator_cmd',
    ):
        super().__init__(
            outcomes=['tool_selected', 'next', 'back', 'done'],
            output_keys=['tool_name'],
        )
        self._allowed = {str(t).strip().lower() for t in (allowed_tools or []) if t}
        self._tool_topic = tool_topic
        self._operator_topic = operator_topic
        self._tool_sub = None
        self._op_sub = None
        self._latest_tool = None
        self._latest_op = None

    def on_enter(self, userdata):
        userdata.tool_name = ''
        # Drop anything left from a previous phase.
        self._latest_tool = None
        self._latest_op = None

        node = EventState._node
        if self._tool_sub is None:
            try:
                self._tool_sub = node.create_subscription(
                    String, self._tool_topic, self._on_tool_msg, 10
                )
            except Exception as exc:  # pylint: disable=broad-except
                Logger.logwarn(f'Subscribe {self._tool_topic} failed: {exc}')
        if self._op_sub is None:
            try:
                self._op_sub = node.create_subscription(
                    String, self._operator_topic, self._on_op_msg, 10
                )
            except Exception as exc:  # pylint: disable=broad-except
                Logger.logwarn(f'Subscribe {self._operator_topic} failed: {exc}')

        Logger.loginfo(
            'Waiting for operator command '
            f'(tools allowed: {sorted(self._allowed) or "-"}; '
            'or say next / back / done)'
        )

    def execute(self, userdata):
        # Operator commands take priority to make abort/advance snappy.
        if self._latest_op is not None:
            msg, self._latest_op = self._latest_op, None
            cmd = (msg.data or '').strip().lower()
            if cmd in self._OP_OUTCOMES:
                Logger.loginfo(f'Operator command: {cmd}')
                return cmd
            Logger.logwarn(f'Ignoring unknown operator command: "{cmd}"')

        if self._latest_tool is not None:
            msg, self._latest_tool = self._latest_tool, None
            requested = (msg.data or '').strip()
            if requested.lower() in self._allowed:
                userdata.tool_name = requested
                Logger.loginfo(f'Tool requested: {requested}')
                return 'tool_selected'
            Logger.logwarn(
                f'Tool "{requested}" not permitted in this phase '
                f'(allowed: {sorted(self._allowed) or "-"}); ignoring.'
            )

        return None

    # -- callbacks --------------------------------------------------------
    def _on_tool_msg(self, msg):
        self._latest_tool = msg

    def _on_op_msg(self, msg):
        self._latest_op = msg
