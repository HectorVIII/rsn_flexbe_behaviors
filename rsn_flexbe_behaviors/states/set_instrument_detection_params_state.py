"""FlexBE state for setting instrument_detection_node runtime parameters."""

from flexbe_core import EventState, Logger
from flexbe_core.proxy import ProxyServiceCaller
from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
from rcl_interfaces.srv import SetParameters


class SetInstrumentDetectionParamsState(EventState):
    """
    Sets calibration offsets on instrument_detection_node.

    Currently exposes x_offset_m so it can be tuned at behavior start
    without editing YAML or restarting the perception node.

    -- service_name   string  Parameter service name.
    -- x_offset_m     float   Residual camera->base x offset in meters.
    -- timeout_sec    float   Maximum time to wait for service/result.

    <= done           Parameter was accepted.
    <= failed         Parameter service rejected the value.
    <= unavailable    Service was unavailable or timed out.
    """

    def __init__(
        self,
        service_name='/instrument_detection_node/set_parameters',
        x_offset_m=-0.008,
        timeout_sec=10.0
    ):
        super().__init__(outcomes=['done', 'failed', 'unavailable'])

        self._service_name = service_name
        self._x_offset_m = float(x_offset_m)
        self._timeout_sec = float(timeout_sec)

        self._srv = None
        self._start_time = None
        self._called = False

    def on_enter(self, userdata):
        self._start_time = self._now()
        self._called = False

        if self._srv is None:
            if ProxyServiceCaller._node is None:
                ProxyServiceCaller.initialize(EventState._node)
            self._srv = ProxyServiceCaller(
                {self._service_name: SetParameters},
                wait_duration=0.0
            )

        self._call_if_available()

    def execute(self, userdata):
        if self._timed_out():
            Logger.logwarn(f'Timeout waiting for {self._service_name}.')
            return 'unavailable'

        if not self._called:
            self._call_if_available()
            return None

        if not self._srv.done(self._service_name):
            return None

        try:
            response = self._srv.result(self._service_name)
        except Exception as exc:  # pylint: disable=broad-except
            Logger.logerr(
                f'Failed to set instrument detection parameters: {exc}'
            )
            return 'failed'

        for result in response.results:
            if not result.successful:
                Logger.logwarn(
                    'instrument_detection_node parameter update rejected: '
                    f'{result.reason}'
                )
                return 'failed'

        Logger.loginfo(
            'Set instrument_detection_node parameters: '
            f'x_offset_m={self._x_offset_m}'
        )
        return 'done'

    def _call_if_available(self):
        if not self._srv.is_available(self._service_name, wait_duration=0.001):
            Logger.logwarn(f'Service {self._service_name} is not available.')
            return

        request = SetParameters.Request()
        request.parameters = [
            self._double_parameter('x_offset_m', self._x_offset_m),
        ]

        self._srv.call_async(
            self._service_name,
            request,
            wait_duration=0.001
        )
        self._called = True
        Logger.loginfo(f'Called service {self._service_name}.')

    def _timed_out(self):
        return self._now() - self._start_time > self._timeout_sec

    @staticmethod
    def _double_parameter(name, value):
        parameter = Parameter()
        parameter.name = name
        parameter.value = ParameterValue(
            type=ParameterType.PARAMETER_DOUBLE,
            double_value=float(value)
        )
        return parameter

    @staticmethod
    def _now():
        return EventState._node.get_clock().now().nanoseconds * 1e-9
