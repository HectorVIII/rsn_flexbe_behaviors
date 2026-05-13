#!/usr/bin/env python3
"""FlexBE behavior for the RSN handover demo."""

from flexbe_core import Autonomy, Behavior, OperatableStateMachine
from flexbe_states.wait_state import WaitState

from rsn_flexbe_behaviors.states.return_instrument_to_source_state import (
    ReturnInstrumentToSourceState
)
from rsn_flexbe_behaviors.states.grasp_and_lift_state import (
    GraspAndLiftState
)
from rsn_flexbe_behaviors.states.move_to_hand_state import (
    MoveToHandState
)
from rsn_flexbe_behaviors.states.move_to_instrument_hover_state import (
    MoveToInstrumentHoverState
)
from rsn_flexbe_behaviors.states.move_to_p0_state import (
    MoveToP0State
)
from rsn_flexbe_behaviors.states.open_gripper_state import (
    OpenGripperState
)
from rsn_flexbe_behaviors.states.retreat_after_release_state import (
    RetreatAfterReleaseState
)
from rsn_flexbe_behaviors.states.start_hand_detection_state import (
    StartHandDetectionState
)
from rsn_flexbe_behaviors.states.start_instrument_detection_state import (
    StartInstrumentDetectionState
)
from rsn_flexbe_behaviors.states.wait_for_release_service_state import (
    WaitForReleaseState
)
from rsn_flexbe_behaviors.states.visual_servo_to_instrument_state import (
    VisualServoToInstrumentState
)
from rsn_flexbe_behaviors.states.set_xarm_motion_params_state import (
    SetXArmMotionParamsState
)
from rsn_flexbe_behaviors.states.wait_for_voice_target_state import (
    WaitForVoiceTargetState
)


class RSNHandoverDemoSM(Behavior):
    """FlexBE behavior for the RSN handover demo."""

    def __init__(self, node):
        """Initialize the behavior and its FlexBE parameters."""
        super(RSNHandoverDemoSM, self).__init__()
        self.name = 'RSN Handover Demo'
        self.node = node

        GraspAndLiftState.initialize_ros(node)
        MoveToHandState.initialize_ros(node)
        MoveToInstrumentHoverState.initialize_ros(node)
        MoveToP0State.initialize_ros(node)
        OpenGripperState.initialize_ros(node)
        RetreatAfterReleaseState.initialize_ros(node)
        StartHandDetectionState.initialize_ros(node)
        StartInstrumentDetectionState.initialize_ros(node)
        WaitForReleaseState.initialize_ros(node)
        VisualServoToInstrumentState.initialize_ros(node)
        WaitForVoiceTargetState.initialize_ros(node)
        ReturnInstrumentToSourceState.initialize_ros(node)
        SetXArmMotionParamsState.initialize_ros(node)
        WaitState.initialize_ros(node)
        OperatableStateMachine.initialize_ros(node)

        self.add_parameter('service_timeout_sec', 10.0)
        self.add_parameter('xarm_speed', 80.0)
        self.add_parameter('xarm_acc', 200.0)
        self.add_parameter(
            'xarm_param_service',
            '/xarm_controller_node/set_parameters'
        )
        self.add_parameter('voice_timeout_sec', 30.0)
        self.add_parameter('instrument_move_retry_count', 39)
        self.add_parameter('instrument_move_retry_delay_sec', 0.5)
        self.add_parameter('hand_move_retry_count', 19)
        self.add_parameter('hand_move_retry_delay_sec', 1.0)
        self.add_parameter('wait_for_release_timeout_sec', 120.0)
        self.add_parameter('instrument_node_exit_delay_sec', 0.5)

    def create(self):
        """Create the handover state machine with basic recovery paths."""
        # x:3050 y:40, x:3050 y:260
        state_machine = OperatableStateMachine(outcomes=['finished', 'failed'])
        state_machine.userdata.target_class = ''
        state_machine.userdata.response_message = ''

        with state_machine:
            # x:30 y:40
            OperatableStateMachine.add(
                'Set XArm Motion Params',
                SetXArmMotionParamsState(
                    service_name=self.xarm_param_service,
                    speed=self.xarm_speed,
                    acc=self.xarm_acc,
                    timeout_sec=self.service_timeout_sec
                ),
                transitions={'done': 'Move To P0',
                             'failed': 'failed',
                             'unavailable': 'failed'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off}
            )

            # x:230 y:40
            OperatableStateMachine.add(
                'Move To P0',
                MoveToP0State(timeout_sec=self.service_timeout_sec),
                transitions={'done': 'Open Gripper',
                             'failed': 'failed',
                             'unavailable': 'failed'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:430 y:40
            OperatableStateMachine.add(
                'Open Gripper',
                OpenGripperState(timeout_sec=self.service_timeout_sec),
                transitions={'done': 'Wait For Voice Target',
                             'failed': 'failed',
                             'unavailable': 'failed'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:630 y:40
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

            # x:830 y:40
            OperatableStateMachine.add(
                'Start Instrument Detection',
                StartInstrumentDetectionState(
                    timeout_sec=self.service_timeout_sec
                ),
                transitions={'done': 'Move To Instrument Hover',
                             'failed': 'Abort Return To P0',
                             'unavailable': 'Abort Return To P0'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:1030 y:40
            OperatableStateMachine.add(
                'Move To Instrument Hover',
                MoveToInstrumentHoverState(
                    timeout_sec=self._retry_timeout(
                        self.instrument_move_retry_count,
                        self.instrument_move_retry_delay_sec
                    ),
                    retry_count=self.instrument_move_retry_count,
                    retry_delay_sec=self.instrument_move_retry_delay_sec
                ),
                transitions={'done': 'Visual Servo To Instrument',
                             'failed': 'Abort Return To P0',
                             'unavailable': 'Abort Return To P0'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:1230 y:40
            OperatableStateMachine.add(
                'Visual Servo To Instrument',
                VisualServoToInstrumentState(
                    timeout_sec=self.service_timeout_sec
                ),
                transitions={'done': 'Grasp And Lift',
                             'failed': 'Abort Open Gripper',
                             'unavailable': 'Abort Open Gripper'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:1430 y:40
            OperatableStateMachine.add(
                'Grasp And Lift',
                GraspAndLiftState(timeout_sec=self.service_timeout_sec),
                transitions={'done': 'Wait For Instrument Camera Release',
                             'failed': 'Abort Open Gripper',
                             'unavailable': 'Abort Open Gripper'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:1630 y:40
            OperatableStateMachine.add(
                'Wait For Instrument Camera Release',
                WaitState(wait_time=self.instrument_node_exit_delay_sec),
                transitions={'done': 'Start Hand Detection'},
                autonomy={'done': Autonomy.Off}
            )

            # x:2030 y:40
            OperatableStateMachine.add(
                'Start Hand Detection',
                StartHandDetectionState(timeout_sec=self.service_timeout_sec),
                transitions={'done': 'Move To Hand',
                             'failed': 'Return Instrument To Source',
                             'unavailable': 'Return Instrument To Source'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:2230 y:40
            OperatableStateMachine.add(
                'Move To Hand',
                MoveToHandState(
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

            # x:2430 y:40
            OperatableStateMachine.add(
                'Wait For Release',
                WaitForReleaseState(
                    timeout_sec=self.wait_for_release_timeout_sec
                ),
                transitions={'released': 'Open Gripper For Release',
                             'timeout': 'Return Instrument To Source',
                             'sensor_error': 'Return Instrument To Source',
                             'unavailable': 'Return Instrument To Source'},
                autonomy={'released': Autonomy.Off,
                          'timeout': Autonomy.Off,
                          'sensor_error': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:2630 y:40
            OperatableStateMachine.add(
                'Open Gripper For Release',
                OpenGripperState(timeout_sec=self.service_timeout_sec),
                transitions={'done': 'Retreat After Release',
                             'failed': 'Recovery Return To P0',
                             'unavailable': 'Recovery Return To P0'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:2830 y:40
            OperatableStateMachine.add(
                'Retreat After Release',
                RetreatAfterReleaseState(timeout_sec=self.service_timeout_sec),
                transitions={'done': 'Return To P0',
                             'failed': 'Recovery Return To P0',
                             'unavailable': 'Recovery Return To P0'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:3030 y:40
            OperatableStateMachine.add(
                'Return To P0',
                MoveToP0State(timeout_sec=self.service_timeout_sec),
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
                OpenGripperState(timeout_sec=self.service_timeout_sec),
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
                MoveToP0State(timeout_sec=self.service_timeout_sec),
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
                ReturnInstrumentToSourceState(
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
                MoveToP0State(timeout_sec=self.service_timeout_sec),
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
