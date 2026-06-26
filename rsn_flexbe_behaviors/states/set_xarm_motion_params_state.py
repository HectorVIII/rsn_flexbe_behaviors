"""FlexBE state for setting xArm controller motion parameters."""

from flexbe_core import EventState, Logger
from flexbe_core.proxy import ProxyServiceCaller
from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
from rcl_interfaces.srv import SetParameters


class SetXArmMotionParamsState(EventState):
    """
    Sets MoveIt velocity/acceleration scaling on xarm_controller_node.

    Motion is now planned by MoveIt, so the relevant knobs are scaling
    factors in (0, 1] — NOT the legacy SDK mm/s units. 1.0 = robot's max
    joint speed; 0.1 = 10%.

    -- service_name           string  Parameter service name.
    -- velocity_scaling       float   MoveIt velocity scaling in (0, 1].
    -- acceleration_scaling   float   MoveIt acceleration scaling in (0, 1].
    -- timeout_sec            float   Maximum time to wait for service/result.

    <= done                   Parameters were accepted.
    <= failed                 Parameter service rejected at least one value.
    <= unavailable            Service was unavailable or timed out.
    """

    def __init__(
        self,
        service_name='/xarm_controller_node/set_parameters',
        velocity_scaling=0.1,
        acceleration_scaling=0.1,
        timeout_sec=10.0
    ):
        """Initialize the parameter-setting state."""
        super().__init__(outcomes=['done', 'failed', 'unavailable'])

        self._service_name = service_name
        self._velocity_scaling = float(velocity_scaling)
        self._acceleration_scaling = float(acceleration_scaling)
        self._timeout_sec = float(timeout_sec)

        self._srv = None
        self._start_time = None
        self._called = False

    def on_enter(self, userdata):
        """Create the service caller and send the parameter request."""
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
        """Wait for the SetParameters response."""
        if self._timed_out():
            Logger.logwarn(
                f'Timeout waiting for {self._service_name}.'
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
            Logger.logerr(
                f'Failed to set xArm motion parameters: {exc}'
            )
            return 'failed'

        for result in response.results:
            if not result.successful:
                Logger.logwarn(
                    'xArm motion parameter update rejected: '
                    f'{result.reason}'
                )
                return 'failed'

        Logger.loginfo(
            'Set xArm motion parameters: '
            f'velocity_scaling={self._velocity_scaling}, '
            f'acceleration_scaling={self._acceleration_scaling}'
        )
        return 'done'

    def _call_if_available(self):
        if not self._srv.is_available(self._service_name, wait_duration=0.001):
            Logger.logwarn(f'Service {self._service_name} is not available.')
            return

        request = SetParameters.Request()
        request.parameters = [
            self._double_parameter('velocity_scaling', self._velocity_scaling),
            self._double_parameter(
                'acceleration_scaling', self._acceleration_scaling
            ),
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
