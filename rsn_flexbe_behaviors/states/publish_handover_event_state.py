"""One-shot publisher of a HandoverEvent.

Reusable across the SM. Constructed with a fixed event_type; reads
tool_class from userdata.target_class each time it runs.

Used to feed workflow_state_estimator so it can advance the surgical step
belief. Fires and returns 'done' in a single execute() call.
"""

from flexbe_core import EventState, Logger

from rsn_interfaces.msg import HandoverEvent


class PublishHandoverEventState(EventState):
    """
    Publish a single rsn_interfaces/HandoverEvent.

    -- event_type  int8    HandoverEvent.REQUESTED / GRASPED / ... constant.
    -- topic       string  Event topic (default matches workflow estimator).

    ># target_class string  Tool class name published as the event's tool_class.

    <= done                Event published.
    """

    def __init__(self, event_type, topic='/handover_event'):
        """Initialize with a fixed event_type."""
        super().__init__(outcomes=['done'], input_keys=['target_class'])
        self._event_type = int(event_type)
        self._topic = topic
        self._event_pub = None
        self._fired = False

    def on_enter(self, userdata):
        """Reset and publish the event once."""
        self._fired = False
        if self._event_pub is None:
            self._event_pub = EventState._node.create_publisher(
                HandoverEvent, self._topic, 10
            )

        msg = HandoverEvent()
        msg.header.stamp = EventState._node.get_clock().now().to_msg()
        msg.event_type = self._event_type
        msg.tool_class = str(userdata.target_class or '').strip()
        msg.reason = ''
        self._event_pub.publish(msg)
        self._fired = True
        Logger.loginfo(
            f'Published HandoverEvent(type={self._event_type}, '
            f'tool={msg.tool_class!r}) on {self._topic}'
        )

    def execute(self, userdata):
        """Return done immediately after publish."""
        return 'done' if self._fired else None
