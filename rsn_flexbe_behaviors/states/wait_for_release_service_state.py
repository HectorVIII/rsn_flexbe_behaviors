"""Semantic state for waiting for release detection."""

from flexbe_core import EventState, Logger
from flexbe_core.proxy import ProxyServiceCaller
from std_srvs.srv import Trigger


class WaitForReleaseState(EventState):
    """
    Waits until release is detected by the xArm force-torque sensor.

    -- timeout_sec float   Maximum time to wait for service/result.

    #> response_message string  Service response message.

    <= released                Release was detected.
    <= timeout                 Release was not detected before timeout.
    <= sensor_error            FT sensor setup/read failed.
    <= unavailable             Service was unavailable or timed out.
    """

    def __init__(self, timeout_sec=120.0):
        """Initialize the wait-for-release state."""
        super().__init__(
            outcomes=['released', 'timeout', 'sensor_error', 'unavailable'],
            output_keys=['response_message']
        )
        self._service_name = '/wait_for_release'
        self._timeout_sec = float(timeout_sec)
        self._srv = None
        self._start_time = None
        self._called = False

    def on_enter(self, userdata):
        """Call the wait-for-release service."""
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

        self._call_if_available()

    def execute(self, userdata):
        """Wait for the release result and classify the failure reason."""
        if self._timed_out():
            userdata.response_message = (
                f'Timeout waiting for {self._service_name}'
            )
            return 'unavailable'

        if not self._called:
            self._call_if_available()
            return None

        if not self._srv.done(self._service_name):
            return None

        try:
            response = self._srv.result(self._service_name)
        except Exception as exc:  # pylint: disable=broad-except
            userdata.response_message = str(exc)
            Logger.logerr(f'Service {self._service_name} failed: {exc}')
            return 'unavailable'

        userdata.response_message = response.message
        if response.success:
            Logger.loginfo(f'Release detected: {response.message}')
            return 'released'

        message = response.message.lower()
        if 'sensor error' in message or 'ft' in message:
            Logger.logwarn(f'Release sensor error: {response.message}')
            return 'sensor_error'

        if 'timeout' in message:
            Logger.logwarn(f'Release timeout: {response.message}')
            return 'timeout'

        Logger.logwarn(f'Release failed: {response.message}')
        return 'sensor_error'

    def _call_if_available(self):
        if not self._srv.is_available(self._service_name, wait_duration=0.001):
            Logger.logwarn(f'Service {self._service_name} is not available.')
            return

        self._srv.call_async(
            self._service_name,
            Trigger.Request(),
            wait_duration=0.001
        )
        self._called = True
        Logger.loginfo(f'Called service {self._service_name}.')

    def _timed_out(self):
        return self._now() - self._start_time > self._timeout_sec

    @staticmethod
    def _now():
        return EventState._node.get_clock().now().nanoseconds * 1e-9
