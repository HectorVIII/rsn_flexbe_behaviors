"""Reusable FlexBE state for launching the RSN hand node process."""

import subprocess

from flexbe_core import EventState, Logger
from flexbe_core.proxy import ProxyServiceCaller
from std_srvs.srv import Trigger


class LaunchHandNodeState(EventState):
    """
    Launches rsn zed_hand_node and optionally waits for its start service.

    -- package_name          string  Package containing the executable.
    -- executable            string  Executable to start.
    -- params_file           string  Optional ROS params file.
    -- startup_delay_sec     float   Delay before checking service.
    -- required_service_name string  Service expected after launch.
    -- service_timeout_sec   float   Maximum time to wait for service.

    <= launched                     Process started and service is available.
    <= failed                       Process failed to start or exited early.
    <= service_unavailable          Required service did not become available.
    """

    def __init__(
        self,
        package_name='rsn',
        executable='zed_hand_node',
        params_file='',
        startup_delay_sec=0.5,
        required_service_name='/start_hand_detection',
        service_timeout_sec=20.0,
    ):
        """Initialize the launch state."""
        super().__init__(
            outcomes=['launched', 'failed', 'service_unavailable']
        )

        self._package_name = package_name
        self._executable = executable
        self._params_file = params_file
        self._startup_delay_sec = float(startup_delay_sec)
        self._required_service_name = required_service_name
        self._service_timeout_sec = float(service_timeout_sec)

        self._process = None
        self._start_time = None
        self._srv = None

    def on_enter(self, userdata):
        """Launch the process and prepare the service availability check."""
        self._start_time = self._now()
        self._cleanup_process()

        cmd = ['ros2', 'run', self._package_name, self._executable]
        if self._params_file:
            cmd.extend(['--ros-args', '--params-file', self._params_file])

        try:
            self._process = subprocess.Popen(cmd)
            Logger.loginfo(f'Launched hand node: {" ".join(cmd)}')
        except Exception as exc:  # pylint: disable=broad-except
            Logger.logerr(f'Failed to launch hand node: {exc}')
            self._process = None
            return

        if self._required_service_name:
            if ProxyServiceCaller._node is None:
                ProxyServiceCaller.initialize(EventState._node)
            self._srv = ProxyServiceCaller(
                {self._required_service_name: Trigger},
                wait_duration=0.0
            )

    def execute(self, userdata):
        """Wait for process startup and required service availability."""
        if self._process is None:
            return 'failed'

        exit_code = self._process.poll()
        if exit_code is not None:
            Logger.logerr(f'Hand node exited early with code {exit_code}.')
            return 'failed'

        elapsed = self._now() - self._start_time
        if elapsed < self._startup_delay_sec:
            return None

        if not self._required_service_name:
            return 'launched'

        if self._srv.is_available(
            self._required_service_name,
            wait_duration=0.001
        ):
            Logger.loginfo(
                f'Service {self._required_service_name} is available.'
            )
            return 'launched'

        if elapsed > self._service_timeout_sec:
            Logger.logwarn(
                f'Service {self._required_service_name} unavailable after '
                f'{self._service_timeout_sec:.1f}s.'
            )
            return 'service_unavailable'

        return None

    def on_stop(self):
        """Clean up the launched hand node if the behavior is stopped."""
        self._cleanup_process()

    def _cleanup_process(self):
        if self._process is None:
            return

        exit_code = self._process.poll()
        if exit_code is not None:
            Logger.loginfo(
                f'Hand node process already exited with code {exit_code}.'
            )
            self._process = None
            return

        Logger.loginfo('Terminating launched hand node process...')
        self._process.terminate()

        try:
            self._process.wait(timeout=3.0)
            Logger.loginfo('Hand node process terminated.')
        except subprocess.TimeoutExpired:
            Logger.logwarn(
                'Hand node process did not terminate in time. Killing it...'
            )
            self._process.kill()
            self._process.wait(timeout=3.0)
            Logger.loginfo('Hand node process killed.')
        finally:
            self._process = None

    @staticmethod
    def _now():
        return EventState._node.get_clock().now().nanoseconds * 1e-9
