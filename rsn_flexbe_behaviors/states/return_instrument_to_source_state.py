"""Semantic FlexBE state for returning the grasped instrument to its source."""

from flexbe_core import EventState, Logger
from flexbe_core.proxy import ProxyServiceCaller
from std_srvs.srv import Trigger


class ReturnInstrumentToSourceState(EventState):
    """
    Calls the xArm return-to-source recovery service.

    -- timeout_sec float   Maximum time to wait for service/result.

    #> response_message string  Service response message.

    <= done                    Instrument was placed back and arm returned.
    <= failed                  Return sequence failed or was rejected.
    <= unavailable             Service was unavailable or timed out.
    """

    def __init__(self, timeout_sec=30.0):
        """Initialize the semantic return-to-source state."""
        super().__init__(
            outcomes=['done', 'failed', 'unavailable'],
            output_keys=['response_message']
        )

        self._service_name = '/return_instrument_to_source'
        self._timeout_sec = float(timeout_sec)
        self._srv = None
        self._start_time = None
        self._called = False

    def on_enter(self, userdata):
        """Reset state and call the return-to-source service if available."""
        userdata.response_message = ''
        self._start_time = self._now()
        self._called = False

        if self._srv is None:
            if ProxyServiceCaller._node is None:
                ProxyServiceCaller.initialize(EventState._node)
            self._srv = ProxyServiceCaller(
                {self._service_name: Trigger},
                wait_duration=0.0
            )

        self._call_if_available(userdata)

    def execute(self, userdata):
        """Wait for return-to-source completion."""
        if self._timed_out():
            userdata.response_message = (
                f'Timeout waiting for {self._service_name}'
            )
            Logger.logwarn(userdata.response_message)
            return 'unavailable'

        if not self._called:
            self._call_if_available(userdata)
            return None

        if not self._srv.done(self._service_name):
            return None

        try:
            response = self._srv.result(self._service_name)
        except Exception as exc:  # pylint: disable=broad-except
            userdata.response_message = str(exc)
            Logger.logerr(
                f'Return instrument service failed: {exc}'
            )
            return 'failed'

        userdata.response_message = response.message
        if response.success:
            Logger.loginfo(
                f'Returned instrument to source: {response.message}'
            )
            return 'done'

        Logger.logwarn(
            f'Return instrument to source was rejected: {response.message}'
        )
        return 'failed'

    def _call_if_available(self, userdata):
        if not self._srv.is_available(self._service_name, wait_duration=0.001):
            Logger.logwarn(f'Service {self._service_name} is not available.')
            return

        try:
            self._srv.call_async(
                self._service_name,
                Trigger.Request(),
                wait_duration=0.001
            )
            self._called = True
            Logger.loginfo(f'Called service {self._service_name}.')
        except Exception as exc:  # pylint: disable=broad-except
            userdata.response_message = str(exc)
            Logger.logerr(
                f'Failed to call service {self._service_name}: {exc}'
            )

    def _timed_out(self):
        return self._now() - self._start_time > self._timeout_sec

    @staticmethod
    def _now():
        return EventState._node.get_clock().now().nanoseconds * 1e-9
