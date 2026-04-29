"""Reusable FlexBE state for waiting on a voice target topic."""

from flexbe_core import EventState, Logger
from std_msgs.msg import String


class WaitForVoiceTargetState(EventState):
    """
    Waits for a target instrument class on a std_msgs/String topic.

    -- topic       string  Topic that publishes the target class.
    -- timeout_sec float   Maximum time to wait.
    -- clear       bool    Clear old cached messages on enter.

    #> target_class string Received target class.

    <= received           Target class received.
    <= timeout            No target arrived before timeout.
    <= unavailable        Subscription could not be created.
    """

    def __init__(
        self,
        topic='/voice_target_instrument',
        timeout_sec=30.0,
        clear=True
    ):
        """Initialize the voice target wait state."""
        super().__init__(
            outcomes=['received', 'timeout', 'unavailable'],
            output_keys=['target_class']
        )

        self._topic = topic
        self._timeout_sec = float(timeout_sec)
        self._clear = bool(clear)
        self._start_time = None
        self._connected = False
        self._subscription = None
        self._latest_msg = None

    def on_enter(self, userdata):
        """Reset cached output and connect the subscriber if needed."""
        userdata.target_class = ''
        self._start_time = self._now()
        if self._clear:
            self._latest_msg = None

        if not self._connected:
            self._connect()

    def execute(self, userdata):
        """Wait for a target string or timeout."""
        if not self._connected:
            return 'unavailable'

        if self._latest_msg is not None:
            msg = self._latest_msg
            self._latest_msg = None
            userdata.target_class = msg.data.strip()
            Logger.loginfo(f'Received voice target: {userdata.target_class}')
            return 'received'

        if self._now() - self._start_time > self._timeout_sec:
            Logger.logwarn(
                f'Timeout waiting for voice target on {self._topic}.'
            )
            return 'timeout'

        return None

    def _connect(self):
        try:
            self._subscription = EventState._node.create_subscription(
                String,
                self._topic,
                self._voice_target_callback,
                10
            )
            self._connected = True
        except Exception as exc:  # pylint: disable=broad-except
            self._connected = False
            Logger.logwarn(f'Could not subscribe to {self._topic}: {exc}')

    def _voice_target_callback(self, msg):
        self._latest_msg = msg

    @staticmethod
    def _now():
        return EventState._node.get_clock().now().nanoseconds * 1e-9
