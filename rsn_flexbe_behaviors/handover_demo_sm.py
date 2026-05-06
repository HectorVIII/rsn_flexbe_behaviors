#!/usr/bin/env python3
"""FlexBE behavior for the RSN handover demo."""

from ament_index_python.packages import (
    PackageNotFoundError,
    get_package_share_directory
)
from flexbe_core import Autonomy, Behavior, OperatableStateMachine
from flexbe_states.wait_state import WaitState

from rsn_flexbe_behaviors.states.launch_hand_node_state import (
    LaunchHandNodeState
)
from rsn_flexbe_behaviors.states.trigger_service_state import (
    TriggerServiceState
)
from rsn_flexbe_behaviors.states.wait_for_voice_target_state import (
    WaitForVoiceTargetState
)


class HandoverDemoSM(Behavior):
    """FlexBE behavior for the RSN handover demo."""

    def __init__(self, node):
        """Initialize the behavior and its FlexBE parameters."""
        super(HandoverDemoSM, self).__init__()
        self.name = 'RSN Handover Demo'
        self.node = node

        TriggerServiceState.initialize_ros(node)
        WaitForVoiceTargetState.initialize_ros(node)
        LaunchHandNodeState.initialize_ros(node)
        WaitState.initialize_ros(node)
        OperatableStateMachine.initialize_ros(node)

        self.add_parameter('service_timeout_sec', 10.0)
        self.add_parameter('voice_timeout_sec', 30.0)
        self.add_parameter('instrument_move_retry_count', 39)
        self.add_parameter('instrument_move_retry_delay_sec', 0.5)
        self.add_parameter('hand_move_retry_count', 19)
        self.add_parameter('hand_move_retry_delay_sec', 1.0)
        self.add_parameter('wait_for_release_timeout_sec', 120.0)
        self.add_parameter('instrument_node_exit_delay_sec', 1.5)
        self.add_parameter('hand_node_package', 'rsn')
        self.add_parameter('hand_node_executable', 'zed_hand_node')
        self.add_parameter('hand_node_startup_delay_sec', 0.5)
        self.add_parameter('hand_node_service_timeout_sec', 20.0)
        self.add_parameter('hand_node_params_file', '')

    def create(self):
        """Create the handover state machine with basic recovery paths."""
        # x:3050 y:40, x:3050 y:260
        state_machine = OperatableStateMachine(outcomes=['finished', 'failed'])
        state_machine.userdata.target_class = ''
        state_machine.userdata.response_message = ''

        with state_machine:
            # x:30 y:40
            OperatableStateMachine.add(
                'Move To P0',
                TriggerServiceState(
                    '/move_to_p0',
                    timeout_sec=self.service_timeout_sec
                ),
                transitions={'done': 'Open Gripper',
                             'failed': 'failed',
                             'unavailable': 'failed'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:230 y:40
            OperatableStateMachine.add(
                'Open Gripper',
                TriggerServiceState(
                    '/open_gripper',
                    timeout_sec=self.service_timeout_sec
                ),
                transitions={'done': 'Wait For Voice Target',
                             'failed': 'failed',
                             'unavailable': 'failed'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:430 y:40
            OperatableStateMachine.add(
                'Wait For Voice Target',
                WaitForVoiceTargetState(timeout_sec=self.voice_timeout_sec),
                transitions={'received': 'Start Instrument Detection',
                             'timeout': 'Abort Return To P0',
                             'unavailable': 'Abort Return To P0'},
                autonomy={'received': Autonomy.Off,
                          'timeout': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'target_class': 'target_class'}
            )

            # x:630 y:40
            OperatableStateMachine.add(
                'Start Instrument Detection',
                TriggerServiceState(
                    '/start_instrument_detection',
                    timeout_sec=self.service_timeout_sec
                ),
                transitions={'done': 'Move To Instrument',
                             'failed': 'Abort Return To P0',
                             'unavailable': 'Abort Return To P0'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:830 y:40
            OperatableStateMachine.add(
                'Move To Instrument',
                TriggerServiceState(
                    '/move_to_instrument',
                    timeout_sec=self._retry_timeout(
                        self.instrument_move_retry_count,
                        self.instrument_move_retry_delay_sec
                    ),
                    retry_count=self.instrument_move_retry_count,
                    retry_delay_sec=self.instrument_move_retry_delay_sec
                ),
                transitions={'done': 'Close Gripper',
                             'failed': 'Abort Return To P0',
                             'unavailable': 'Abort Return To P0'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:1030 y:40
            OperatableStateMachine.add(
                'Close Gripper',
                TriggerServiceState(
                    '/close_gripper',
                    timeout_sec=self.service_timeout_sec
                ),
                transitions={'done': 'Lift After Grasp',
                             'failed': 'Abort Open Gripper',
                             'unavailable': 'Abort Open Gripper'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:1230 y:40
            OperatableStateMachine.add(
                'Lift After Grasp',
                TriggerServiceState(
                    '/lift_after_grasp',
                    timeout_sec=self.service_timeout_sec
                ),
                transitions={'done': 'Wait For Instrument Camera Release',
                             'failed': 'Abort Open Gripper',
                             'unavailable': 'Abort Open Gripper'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:1430 y:40
            OperatableStateMachine.add(
                'Wait For Instrument Camera Release',
                WaitState(wait_time=self.instrument_node_exit_delay_sec),
                transitions={'done': 'Launch Hand Node'},
                autonomy={'done': Autonomy.Off}
            )

            # x:1630 y:40
            OperatableStateMachine.add(
                'Launch Hand Node',
                LaunchHandNodeState(
                    package_name=self.hand_node_package,
                    executable=self.hand_node_executable,
                    params_file=self._hand_node_params_file(),
                    startup_delay_sec=self.hand_node_startup_delay_sec,
                    required_service_name='/start_hand_detection',
                    service_timeout_sec=self.hand_node_service_timeout_sec
                ),
                transitions={'launched': 'Start Hand Detection',
                             'failed': 'Return Instrument To Source',
                             'service_unavailable': 'Return Instrument To Source'},
                autonomy={'launched': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'service_unavailable': Autonomy.Off}
            )

            # x:1830 y:40
            OperatableStateMachine.add(
                'Start Hand Detection',
                TriggerServiceState(
                    '/start_hand_detection',
                    timeout_sec=self.service_timeout_sec
                ),
                transitions={'done': 'Move To Hand',
                             'failed': 'Return Instrument To Source',
                             'unavailable': 'Return Instrument To Source'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:2030 y:40
            OperatableStateMachine.add(
                'Move To Hand',
                TriggerServiceState(
                    '/move_to_hand',
                    timeout_sec=self._retry_timeout(
                        self.hand_move_retry_count,
                        self.hand_move_retry_delay_sec
                    ),
                    retry_count=self.hand_move_retry_count,
                    retry_delay_sec=self.hand_move_retry_delay_sec
                ),
                transitions={'done': 'Wait For Release',
                             'failed': 'Return Instrument To Source',
                             'unavailable': 'Return Instrument To Source'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:2230 y:40
            OperatableStateMachine.add(
                'Wait For Release',
                TriggerServiceState(
                    '/wait_for_release',
                    timeout_sec=self.wait_for_release_timeout_sec
                ),
                transitions={'done': 'Open Gripper For Release',
                             'failed': 'Return Instrument To Source',
                             'unavailable': 'Return Instrument To Source'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:2430 y:40
            OperatableStateMachine.add(
                'Open Gripper For Release',
                TriggerServiceState(
                    '/open_gripper',
                    timeout_sec=self.service_timeout_sec
                ),
                transitions={'done': 'Retreat After Release',
                             'failed': 'Recovery Return To P0',
                             'unavailable': 'Recovery Return To P0'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:2630 y:40
            OperatableStateMachine.add(
                'Retreat After Release',
                TriggerServiceState(
                    '/retreat_after_release',
                    timeout_sec=self.service_timeout_sec
                ),
                transitions={'done': 'Return To P0',
                             'failed': 'Recovery Return To P0',
                             'unavailable': 'Recovery Return To P0'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:2830 y:40
            OperatableStateMachine.add(
                'Return To P0',
                TriggerServiceState(
                    '/move_to_p0',
                    timeout_sec=self.service_timeout_sec
                ),
                transitions={'done': 'finished',
                             'failed': 'failed',
                             'unavailable': 'failed'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:1030 y:260
            OperatableStateMachine.add(
                'Abort Open Gripper',
                TriggerServiceState(
                    '/open_gripper',
                    timeout_sec=self.service_timeout_sec
                ),
                transitions={'done': 'Abort Return To P0',
                             'failed': 'Abort Return To P0',
                             'unavailable': 'Abort Return To P0'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:1230 y:260
            OperatableStateMachine.add(
                'Abort Return To P0',
                TriggerServiceState(
                    '/move_to_p0',
                    timeout_sec=self.service_timeout_sec
                ),
                transitions={'done': 'failed',
                             'failed': 'failed',
                             'unavailable': 'failed'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:1830 y:260
            OperatableStateMachine.add(
                'Return Instrument To Source',
                TriggerServiceState(
                    '/return_instrument_to_source',
                    timeout_sec=self._return_instrument_timeout()
                ),
                transitions={'done': 'failed',
                             'failed': 'failed',
                             'unavailable': 'failed'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:2630 y:260
            OperatableStateMachine.add(
                'Recovery Return To P0',
                TriggerServiceState(
                    '/move_to_p0',
                    timeout_sec=self.service_timeout_sec
                ),
                transitions={'done': 'failed',
                             'failed': 'failed',
                             'unavailable': 'failed'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

        return state_machine

    @staticmethod
    def _retry_timeout(retry_count, retry_delay_sec):
        return 10.0 + (float(retry_count) * float(retry_delay_sec))

    def _return_instrument_timeout(self):
        return max(self.service_timeout_sec, 30.0)

    def _hand_node_params_file(self):
        if self.hand_node_params_file:
            return self.hand_node_params_file

        try:
            package_share = get_package_share_directory('rsn')
            return package_share + '/config/zed_hand_params.yaml'
        except PackageNotFoundError:
            return ''
