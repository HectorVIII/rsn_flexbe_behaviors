"""Reusable helper for std_srvs/Trigger service calls.

This is intentionally NOT a FlexBE EventState.  It is meant to be composed
inside an EventState wrapper (e.g. MoveToP0State) which delegates its
``on_enter`` and ``execute`` to this helper.

Why not an EventState:
    EventState.__init__ rebinds ``self.execute`` to ``_event_execute``,
    which auto-fires ``on_enter`` once per activation.  If both the wrapper
    AND this helper inherit EventState, the framework fires ``on_enter``
    twice per state activation (wrapper's own auto-fire + the wrapper
    manually calling ``delegate.on_enter`` inside its own on_enter), and
    the underlying service is invoked twice.  Keeping this class as a
    plain helper means only the outer wrapper is framework-wrapped.

Outcomes and output keys are declared by the wrapping EventState, not here.
"""

from flexbe_core import EventState, Logger
from flexbe_core.proxy import ProxyServiceCaller
from std_srvs.srv import Trigger


class TriggerServiceState:
    """Drive a std_srvs/Trigger service and return outcomes via execute().

    -- service_name     string  Service to call.
    -- timeout_sec      float   Maximum time to wait for availability/result.
    -- retry_count      int     Retries after success=False responses.
    -- retry_delay_sec  float   Delay between retries.

    Outcome strings returned by ``execute`` (the wrapper exposes them):
        'done'         Service returned success=True.
        'failed'       Service returned success=False or raised.
        'unavailable'  Service was unavailable or timed out.
    """

    def __init__(
        self,
        service_name,
        timeout_sec=10.0,
        retry_count=0,
        retry_delay_sec=0.5
    ):
        """Initialize the trigger service helper."""
        self._service_name = service_name
        self._timeout_sec = float(timeout_sec)
        self._retry_count = int(retry_count)
        self._retry_delay_sec = float(retry_delay_sec)
        self._start_time = None
        self._next_call_time = None
        self._attempt = 0
        self._called = False
        self._srv = None

    def on_enter(self, userdata):
        """Reset state and try the first service call."""
        userdata.response_message = ''
        self._called = False
        self._start_time = self._now()
        self._next_call_time = self._start_time
        self._attempt = 0

        if self._srv is None:
            if ProxyServiceCaller._node is None:
                ProxyServiceCaller.initialize(EventState._node)
            self._srv = ProxyServiceCaller(
                {self._service_name: Trigger},
                wait_duration=0.0
            )

        self._call_if_ready(userdata)

    def execute(self, userdata):
        """Wait for service completion and map the response to an outcome."""
        if self._timed_out():
            userdata.response_message = (
                f'Timeout waiting for {self._service_name}'
            )
            return 'unavailable'

        if not self._called:
            if self._call_if_ready(userdata) == 'failed':
                return 'failed'
            return None

        if not self._srv.done(self._service_name):
            return None

        try:
            response = self._srv.result(self._service_name)
        except Exception as exc:  # pylint: disable=broad-except
            userdata.response_message = str(exc)
            Logger.logerr(f'Service {self._service_name} failed: {exc}')
            return 'failed'

        userdata.response_message = response.message
        if response.success:
            Logger.loginfo(
                f'Service {self._service_name} succeeded: {response.message}'
            )
            return 'done'

        if self._attempt <= self._retry_count:
            Logger.logwarn(
                f'Service {self._service_name} returned failure on attempt '
                f'{self._attempt}/{self._retry_count + 1}: {response.message}'
            )
            self._called = False
            self._next_call_time = self._now() + self._retry_delay_sec
            return None

        Logger.logwarn(
            f'Service {self._service_name} returned failure: '
            f'{response.message}'
        )
        return 'failed'

    def _call_if_ready(self, userdata):
        if self._now() < self._next_call_time:
            return None

        if not self._srv.is_available(self._service_name, wait_duration=0.001):
            Logger.logwarn(f'Service {self._service_name} is not available.')
            return None

        try:
            self._srv.call_async(
                self._service_name,
                Trigger.Request(),
                wait_duration=0.001
            )
            self._called = True
            self._attempt += 1
            Logger.loginfo(
                f'Called service {self._service_name} '
                f'(attempt {self._attempt}/{self._retry_count + 1}).'
            )
        except Exception as exc:  # pylint: disable=broad-except
            userdata.response_message = str(exc)
            Logger.logerr(
                f'Failed to call service {self._service_name}: {exc}'
            )
            return 'failed'

        return None

    def _timed_out(self):
        return self._now() - self._start_time > self._timeout_sec

    @staticmethod
    def _now():
        return EventState._node.get_clock().now().nanoseconds * 1e-9
