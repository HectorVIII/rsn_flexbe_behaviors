#!/usr/bin/env python3
"""FlexBE behavior for the RSN handover demo."""

from flexbe_core import Autonomy, Behavior, OperatableStateMachine, set_node
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
from rsn_flexbe_behaviors.states.move_to_instrument_state import (
    MoveToInstrumentState
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
from rsn_flexbe_behaviors.states.set_instrument_detection_params_state import (
    SetInstrumentDetectionParamsState
)
from rsn_flexbe_behaviors.states.set_xarm_motion_params_state import (
    SetXArmMotionParamsState
)
from rsn_flexbe_behaviors.states.wait_for_voice_target_state import (
    WaitForVoiceTargetState
)
from rsn_flexbe_behaviors.states.publish_handover_event_state import (
    PublishHandoverEventState
)
from rsn_flexbe_behaviors.states.query_predicted_next_state import (
    QueryPredictedNextState
)
from rsn_flexbe_behaviors.states.move_to_staging_state import (
    MoveToStagingState
)

from rsn_interfaces.msg import HandoverEvent


class RSNHandoverDemoSM(Behavior):
    """FlexBE behavior for the RSN handover demo."""

    def __init__(self, node):
        """Initialize the behavior and its FlexBE parameters."""
        super(RSNHandoverDemoSM, self).__init__()
        self.name = 'RSN Handover Demo'
        self.node = node

        set_node(node)
        GraspAndLiftState.initialize_ros(node)
        MoveToHandState.initialize_ros(node)
        MoveToInstrumentState.initialize_ros(node)
        MoveToP0State.initialize_ros(node)
        OpenGripperState.initialize_ros(node)
        RetreatAfterReleaseState.initialize_ros(node)
        StartHandDetectionState.initialize_ros(node)
        StartInstrumentDetectionState.initialize_ros(node)
        WaitForReleaseState.initialize_ros(node)
        WaitForVoiceTargetState.initialize_ros(node)
        ReturnInstrumentToSourceState.initialize_ros(node)
        SetXArmMotionParamsState.initialize_ros(node)
        SetInstrumentDetectionParamsState.initialize_ros(node)
        PublishHandoverEventState.initialize_ros(node)
        QueryPredictedNextState.initialize_ros(node)
        MoveToStagingState.initialize_ros(node)
        WaitState.initialize_ros(node)
        OperatableStateMachine.initialize_ros(node)

        # Must exceed the longest MoveIt service round-trip.  At
        # velocity_scaling=0.1 the instrument-approach (hover + LIN descend)
        # and joint-space MOVE_TO_P0 each take ~13-16 s, so 10 s was tripping
        # 'unavailable' on every call and routing FlexBE down the abort path.
        self.add_parameter('service_timeout_sec', 60.0)
        self.add_parameter('xarm_velocity_scaling', 0.1)
        self.add_parameter('xarm_acceleration_scaling', 0.1)
        self.add_parameter(
            'xarm_param_service',
            '/xarm_controller_node/set_parameters'
        )
        self.add_parameter('voice_timeout_sec', 30.0)
        self.add_parameter('instrument_detection_timeout_sec', 30.0)
        self.add_parameter('hand_move_retry_count', 19)
        self.add_parameter('hand_move_retry_delay_sec', 1.0)
        self.add_parameter('wait_for_release_timeout_sec', 120.0)
        self.add_parameter('instrument_node_exit_delay_sec', 0.5)
        self.add_parameter('instrument_x_offset_m', -0.028)
        self.add_parameter(
            'instrument_param_service',
            '/instrument_detection_node/set_parameters'
        )
        # Preload / workflow-estimator wiring.
        self.add_parameter('query_prediction_timeout_sec', 2.0)
        # Preload detection uses a MUCH shorter timeout than the voice-driven
        # detection: if the predicted tool isn't visible in ~5 s, give up
        # quietly and fall back to Return To P0 so the user's next voice
        # command is heard promptly. The full 30 s tolerance is only for the
        # voice-triggered Start Instrument Detection where the surgeon has
        # explicitly asked for the tool.
        self.add_parameter('preload_detection_timeout_sec', 5.0)

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
                    velocity_scaling=self.xarm_velocity_scaling,
                    acceleration_scaling=self.xarm_acceleration_scaling,
                    timeout_sec=self.service_timeout_sec
                ),
                transitions={'done': 'Set Instrument Detection Params',
                             'failed': 'failed',
                             'unavailable': 'failed'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off}
            )

            # x:130 y:40
            OperatableStateMachine.add(
                'Set Instrument Detection Params',
                SetInstrumentDetectionParamsState(
                    service_name=self.instrument_param_service,
                    x_offset_m=self.instrument_x_offset_m,
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
            # Cold-start: do NOT preload. At boot the scene may not be ready
            # (instruments not yet on tray, surgeon not in position, camera
            # still warming up) and moving the arm without a voice cue is
            # surprising. Only enter the preload chain on the LOOP path (from
            # Retreat After Release), where the previous handover implies the
            # scene is active.
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
            # Timeout self-loops: the arm is already at P0 whether we entered
            # from the initial Open Gripper or from Return To P0, so no need
            # to abort/re-home. `unavailable` is a real ROS subscription
            # failure and still routes to the abort path.
            OperatableStateMachine.add(
                'Wait For Voice Target',
                WaitForVoiceTargetState(timeout_sec=self.voice_timeout_sec),
                transitions={'received': 'Publish Requested Event',
                             'timeout': 'Wait For Voice Target',
                             'unavailable': 'Abort Return To P0'},
                autonomy={'received': Autonomy.Off,
                          'timeout': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'target_class': 'target_class'}
            )

            # x:830 y:40
            # Detection failure/timeout usually means "target not visible",
            # "wrong instrument said", or "ZED failed to open" — not a
            # hardware fault. Arm is still at P0 (never moved), so loop
            # straight back to voice wait instead of aborting the demo.
            OperatableStateMachine.add(
                'Start Instrument Detection',
                StartInstrumentDetectionState(
                    timeout_sec=self.instrument_detection_timeout_sec
                ),
                transitions={'done': 'Move To Instrument',
                             'failed': 'Wait For Voice Target',
                             'unavailable': 'Wait For Voice Target'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'target_class': 'target_class',
                           'response_message': 'response_message'}
            )

            # x:1030 y:40
            OperatableStateMachine.add(
                'Move To Instrument',
                MoveToInstrumentState(timeout_sec=self.service_timeout_sec),
                transitions={'done': 'Grasp And Lift',
                             'failed': 'Abort Return To P0',
                             'unavailable': 'Abort Return To P0'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:1230 y:40
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
            # Instead of unconditionally returning to P0, ask the workflow
            # estimator what the next tool is likely to be and try to preload
            # the arm above it. On any failure of that chain we fall through
            # to Return To P0 as before.
            OperatableStateMachine.add(
                'Retreat After Release',
                RetreatAfterReleaseState(timeout_sec=self.service_timeout_sec),
                transitions={'done': 'Query Predicted Next',
                             'failed': 'Recovery Return To P0',
                             'unavailable': 'Recovery Return To P0'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:3030 y:40
            # Preload chain: consult workflow_state_estimator, if it has a
            # prediction fetch that tool's pose and stage above it; otherwise
            # fall through to plain Return To P0.
            OperatableStateMachine.add(
                'Query Predicted Next',
                QueryPredictedNextState(
                    timeout_sec=self.query_prediction_timeout_sec
                ),
                transitions={'has_prediction': 'Preload Instrument Detection',
                             'no_prediction': 'Return To P0'},
                autonomy={'has_prediction': Autonomy.Off,
                          'no_prediction': Autonomy.Off},
                remapping={'target_class': 'target_class'}
            )

            # x:3230 y:40
            # Runs instrument detection with the estimator's predicted tool
            # so xarm_controller_node.latest_instrument_pose points at it
            # when Move To Staging is called. Any failure falls back to a
            # plain Return To P0 so we never make the loop worse than today.
            OperatableStateMachine.add(
                'Preload Instrument Detection',
                StartInstrumentDetectionState(
                    timeout_sec=self.preload_detection_timeout_sec
                ),
                transitions={'done': 'Move To Staging',
                             'failed': 'Return To P0',
                             'unavailable': 'Return To P0'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'target_class': 'target_class',
                           'response_message': 'response_message'}
            )

            # x:3430 y:40
            # Park above the predicted tool at staging_hover_offset_mm.
            OperatableStateMachine.add(
                'Move To Staging',
                MoveToStagingState(timeout_sec=self.service_timeout_sec),
                transitions={'done': 'Wait For Voice Target',
                             'failed': 'Return To P0',
                             'unavailable': 'Return To P0'},
                autonomy={'done': Autonomy.Off,
                          'failed': Autonomy.Off,
                          'unavailable': Autonomy.Off},
                remapping={'response_message': 'response_message'}
            )

            # x:730 y:140
            # Feed workflow_state_estimator so it can advance step belief.
            # Publishes REQUESTED with the actual voice target (not the
            # preload target), so estimator sees what the surgeon actually
            # asked for regardless of whether our preload was correct.
            OperatableStateMachine.add(
                'Publish Requested Event',
                PublishHandoverEventState(
                    event_type=HandoverEvent.REQUESTED,
                    topic='/handover_event'
                ),
                transitions={'done': 'Start Instrument Detection'},
                autonomy={'done': Autonomy.Off},
                remapping={'target_class': 'target_class'}
            )

            # x:3630 y:40
            # Fallback path when the estimator has no prediction (end of
            # workflow) or is unavailable. Same behaviour as the pre-preload
            # loop-back to Wait For Voice Target.
            OperatableStateMachine.add(
                'Return To P0',
                MoveToP0State(timeout_sec=self.service_timeout_sec),
                transitions={'done': 'Wait For Voice Target',
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
