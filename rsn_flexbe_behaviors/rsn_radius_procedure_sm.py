#!/usr/bin/env python3
"""FlexBE behavior — surgical L1 FSM for the distal radius (volar FCR)
procedure. 10 phases, each an inline sub-SM defined at ``create`` scope
(FlexBE App parser requires sub-SMs to live OUTSIDE the outer ``with``
block, so keep that layout).

Per-phase pattern:

    Announce → Wait ──tool_selected──→ RunHandover ─┐
                │                                    │
                │←────────── (released/canceled/failed) ──┘
                ├── next  → next phase
                ├── back  → previous phase
                └── done  → case_done

NOTE: tool whitelists MUST stay in sync with
      rsn/config/procedure_distal_radius.yaml (which is docs-only for
      the App-visualizable version).
"""

from flexbe_core import Autonomy, Behavior, OperatableStateMachine

from rsn_flexbe_behaviors.states.announce_phase_state import (
    AnnouncePhaseState,
)
from rsn_flexbe_behaviors.states.run_handover_action_state import (
    RunHandoverActionState,
)
from rsn_flexbe_behaviors.states.wait_for_operator_command_state import (
    WaitForOperatorCommandState,
)


class RSNRadiusProcedureSM(Behavior):
    """L1 procedural FSM: one inline sub-SM per surgical phase."""

    def __init__(self, node):
        super(RSNRadiusProcedureSM, self).__init__()
        self.name = 'RSN Radius Procedure'
        self.node = node

        RunHandoverActionState.initialize_ros(node)
        WaitForOperatorCommandState.initialize_ros(node)
        AnnouncePhaseState.initialize_ros(node)
        OperatableStateMachine.initialize_ros(node)

        self.add_parameter('run_handover_action', '/run_handover')
        self.add_parameter('handover_timeout_sec', 120.0)

    def create(self):
        # x:30 y:40, x:1830 y:40
        _state_machine = OperatableStateMachine(outcomes=['case_done', 'aborted'])

        # ==============================================================
        # Sub-SM: Phase 01 — Position
        # ==============================================================
        _sm_phase_01_0 = OperatableStateMachine(outcomes=['next', 'back', 'done', 'aborted'])
        _sm_phase_01_0.userdata.tool_name = ''
        _sm_phase_01_0.userdata.reason = ''
        with _sm_phase_01_0:
            OperatableStateMachine.add('Announce',
                                       AnnouncePhaseState(phase_id=1,
                                                          phase_name='Position',
                                                          phase_desc='Supine, arm on hand table, tourniquet.',
                                                          allowed_tools=[]),
                                       transitions={'announced': 'Wait'},
                                       autonomy={'announced': Autonomy.Off})
            OperatableStateMachine.add('Wait',
                                       WaitForOperatorCommandState(allowed_tools=[]),
                                       transitions={'tool_selected': 'RunHandover',
                                                    'next': 'next',
                                                    'back': 'back',
                                                    'done': 'done'},
                                       autonomy={'tool_selected': Autonomy.Off,
                                                 'next': Autonomy.Off,
                                                 'back': Autonomy.Off,
                                                 'done': Autonomy.Off},
                                       remapping={'tool_name': 'tool_name'})
            OperatableStateMachine.add('RunHandover',
                                       RunHandoverActionState(action_topic=self.run_handover_action,
                                                              timeout_sec=self.handover_timeout_sec),
                                       transitions={'released': 'Wait',
                                                    'canceled': 'Wait',
                                                    'failed': 'Wait'},
                                       autonomy={'released': Autonomy.Off,
                                                 'canceled': Autonomy.Off,
                                                 'failed': Autonomy.Off},
                                       remapping={'tool_name': 'tool_name',
                                                  'reason': 'reason'})

        # ==============================================================
        # Sub-SM: Phase 02 — Skin
        # ==============================================================
        _sm_phase_02_1 = OperatableStateMachine(outcomes=['next', 'back', 'done', 'aborted'])
        _sm_phase_02_1.userdata.tool_name = ''
        _sm_phase_02_1.userdata.reason = ''
        with _sm_phase_02_1:
            OperatableStateMachine.add('Announce',
                                       AnnouncePhaseState(phase_id=2,
                                                          phase_name='Skin',
                                                          phase_desc='6-8 cm longitudinal over FCR.',
                                                          allowed_tools=['scalpel_handle']),
                                       transitions={'announced': 'Wait'},
                                       autonomy={'announced': Autonomy.Off})
            OperatableStateMachine.add('Wait',
                                       WaitForOperatorCommandState(allowed_tools=['scalpel_handle']),
                                       transitions={'tool_selected': 'RunHandover',
                                                    'next': 'next',
                                                    'back': 'back',
                                                    'done': 'done'},
                                       autonomy={'tool_selected': Autonomy.Off,
                                                 'next': Autonomy.Off,
                                                 'back': Autonomy.Off,
                                                 'done': Autonomy.Off},
                                       remapping={'tool_name': 'tool_name'})
            OperatableStateMachine.add('RunHandover',
                                       RunHandoverActionState(action_topic=self.run_handover_action,
                                                              timeout_sec=self.handover_timeout_sec),
                                       transitions={'released': 'Wait',
                                                    'canceled': 'Wait',
                                                    'failed': 'Wait'},
                                       autonomy={'released': Autonomy.Off,
                                                 'canceled': Autonomy.Off,
                                                 'failed': Autonomy.Off},
                                       remapping={'tool_name': 'tool_name',
                                                  'reason': 'reason'})

        # ==============================================================
        # Sub-SM: Phase 03 — Subcutaneous
        # ==============================================================
        _sm_phase_03_2 = OperatableStateMachine(outcomes=['next', 'back', 'done', 'aborted'])
        _sm_phase_03_2.userdata.tool_name = ''
        _sm_phase_03_2.userdata.reason = ''
        with _sm_phase_03_2:
            OperatableStateMachine.add('Announce',
                                       AnnouncePhaseState(phase_id=3,
                                                          phase_name='Subcutaneous',
                                                          phase_desc='Dissect to FCR sheath, protect nerves.',
                                                          allowed_tools=['tissue_forceps', 'retractor']),
                                       transitions={'announced': 'Wait'},
                                       autonomy={'announced': Autonomy.Off})
            OperatableStateMachine.add('Wait',
                                       WaitForOperatorCommandState(allowed_tools=['tissue_forceps', 'retractor']),
                                       transitions={'tool_selected': 'RunHandover',
                                                    'next': 'next',
                                                    'back': 'back',
                                                    'done': 'done'},
                                       autonomy={'tool_selected': Autonomy.Off,
                                                 'next': Autonomy.Off,
                                                 'back': Autonomy.Off,
                                                 'done': Autonomy.Off},
                                       remapping={'tool_name': 'tool_name'})
            OperatableStateMachine.add('RunHandover',
                                       RunHandoverActionState(action_topic=self.run_handover_action,
                                                              timeout_sec=self.handover_timeout_sec),
                                       transitions={'released': 'Wait',
                                                    'canceled': 'Wait',
                                                    'failed': 'Wait'},
                                       autonomy={'released': Autonomy.Off,
                                                 'canceled': Autonomy.Off,
                                                 'failed': Autonomy.Off},
                                       remapping={'tool_name': 'tool_name',
                                                  'reason': 'reason'})

        # ==============================================================
        # Sub-SM: Phase 04 — FCR sheath (roof)
        # ==============================================================
        _sm_phase_04_3 = OperatableStateMachine(outcomes=['next', 'back', 'done', 'aborted'])
        _sm_phase_04_3.userdata.tool_name = ''
        _sm_phase_04_3.userdata.reason = ''
        with _sm_phase_04_3:
            OperatableStateMachine.add('Announce',
                                       AnnouncePhaseState(phase_id=4,
                                                          phase_name='FCR sheath (roof)',
                                                          phase_desc='Open sheath roof, retract FCR ulnarly.',
                                                          allowed_tools=['metzenbaum_scissors', 'tissue_forceps', 'retractor']),
                                       transitions={'announced': 'Wait'},
                                       autonomy={'announced': Autonomy.Off})
            OperatableStateMachine.add('Wait',
                                       WaitForOperatorCommandState(allowed_tools=['metzenbaum_scissors', 'tissue_forceps', 'retractor']),
                                       transitions={'tool_selected': 'RunHandover',
                                                    'next': 'next',
                                                    'back': 'back',
                                                    'done': 'done'},
                                       autonomy={'tool_selected': Autonomy.Off,
                                                 'next': Autonomy.Off,
                                                 'back': Autonomy.Off,
                                                 'done': Autonomy.Off},
                                       remapping={'tool_name': 'tool_name'})
            OperatableStateMachine.add('RunHandover',
                                       RunHandoverActionState(action_topic=self.run_handover_action,
                                                              timeout_sec=self.handover_timeout_sec),
                                       transitions={'released': 'Wait',
                                                    'canceled': 'Wait',
                                                    'failed': 'Wait'},
                                       autonomy={'released': Autonomy.Off,
                                                 'canceled': Autonomy.Off,
                                                 'failed': Autonomy.Off},
                                       remapping={'tool_name': 'tool_name',
                                                  'reason': 'reason'})

        # ==============================================================
        # Sub-SM: Phase 05 — FCR sheath (floor)
        # ==============================================================
        _sm_phase_05_4 = OperatableStateMachine(outcomes=['next', 'back', 'done', 'aborted'])
        _sm_phase_05_4.userdata.tool_name = ''
        _sm_phase_05_4.userdata.reason = ''
        with _sm_phase_05_4:
            OperatableStateMachine.add('Announce',
                                       AnnouncePhaseState(phase_id=5,
                                                          phase_name='FCR sheath (floor)',
                                                          phase_desc='Open sheath floor, expose FPL.',
                                                          allowed_tools=['metzenbaum_scissors', 'tissue_forceps', 'scalpel_handle']),
                                       transitions={'announced': 'Wait'},
                                       autonomy={'announced': Autonomy.Off})
            OperatableStateMachine.add('Wait',
                                       WaitForOperatorCommandState(allowed_tools=['metzenbaum_scissors', 'tissue_forceps', 'scalpel_handle']),
                                       transitions={'tool_selected': 'RunHandover',
                                                    'next': 'next',
                                                    'back': 'back',
                                                    'done': 'done'},
                                       autonomy={'tool_selected': Autonomy.Off,
                                                 'next': Autonomy.Off,
                                                 'back': Autonomy.Off,
                                                 'done': Autonomy.Off},
                                       remapping={'tool_name': 'tool_name'})
            OperatableStateMachine.add('RunHandover',
                                       RunHandoverActionState(action_topic=self.run_handover_action,
                                                              timeout_sec=self.handover_timeout_sec),
                                       transitions={'released': 'Wait',
                                                    'canceled': 'Wait',
                                                    'failed': 'Wait'},
                                       autonomy={'released': Autonomy.Off,
                                                 'canceled': Autonomy.Off,
                                                 'failed': Autonomy.Off},
                                       remapping={'tool_name': 'tool_name',
                                                  'reason': 'reason'})

        # ==============================================================
        # Sub-SM: Phase 06 — Deep interval
        # ==============================================================
        _sm_phase_06_5 = OperatableStateMachine(outcomes=['next', 'back', 'done', 'aborted'])
        _sm_phase_06_5.userdata.tool_name = ''
        _sm_phase_06_5.userdata.reason = ''
        with _sm_phase_06_5:
            OperatableStateMachine.add('Announce',
                                       AnnouncePhaseState(phase_id=6,
                                                          phase_name='Deep interval',
                                                          phase_desc='Retract FPL ulnarly, radial artery radial, reach PQ.',
                                                          allowed_tools=['retractor']),
                                       transitions={'announced': 'Wait'},
                                       autonomy={'announced': Autonomy.Off})
            OperatableStateMachine.add('Wait',
                                       WaitForOperatorCommandState(allowed_tools=['retractor']),
                                       transitions={'tool_selected': 'RunHandover',
                                                    'next': 'next',
                                                    'back': 'back',
                                                    'done': 'done'},
                                       autonomy={'tool_selected': Autonomy.Off,
                                                 'next': Autonomy.Off,
                                                 'back': Autonomy.Off,
                                                 'done': Autonomy.Off},
                                       remapping={'tool_name': 'tool_name'})
            OperatableStateMachine.add('RunHandover',
                                       RunHandoverActionState(action_topic=self.run_handover_action,
                                                              timeout_sec=self.handover_timeout_sec),
                                       transitions={'released': 'Wait',
                                                    'canceled': 'Wait',
                                                    'failed': 'Wait'},
                                       autonomy={'released': Autonomy.Off,
                                                 'canceled': Autonomy.Off,
                                                 'failed': Autonomy.Off},
                                       remapping={'tool_name': 'tool_name',
                                                  'reason': 'reason'})

        # ==============================================================
        # Sub-SM: Phase 07 — Pronator quadratus
        # ==============================================================
        _sm_phase_07_6 = OperatableStateMachine(outcomes=['next', 'back', 'done', 'aborted'])
        _sm_phase_07_6.userdata.tool_name = ''
        _sm_phase_07_6.userdata.reason = ''
        with _sm_phase_07_6:
            OperatableStateMachine.add('Announce',
                                       AnnouncePhaseState(phase_id=7,
                                                          phase_name='Pronator quadratus',
                                                          phase_desc='L-incision, elevate subperiosteal, keep flap.',
                                                          allowed_tools=['scalpel_handle', 'tissue_forceps']),
                                       transitions={'announced': 'Wait'},
                                       autonomy={'announced': Autonomy.Off})
            OperatableStateMachine.add('Wait',
                                       WaitForOperatorCommandState(allowed_tools=['scalpel_handle', 'tissue_forceps']),
                                       transitions={'tool_selected': 'RunHandover',
                                                    'next': 'next',
                                                    'back': 'back',
                                                    'done': 'done'},
                                       autonomy={'tool_selected': Autonomy.Off,
                                                 'next': Autonomy.Off,
                                                 'back': Autonomy.Off,
                                                 'done': Autonomy.Off},
                                       remapping={'tool_name': 'tool_name'})
            OperatableStateMachine.add('RunHandover',
                                       RunHandoverActionState(action_topic=self.run_handover_action,
                                                              timeout_sec=self.handover_timeout_sec),
                                       transitions={'released': 'Wait',
                                                    'canceled': 'Wait',
                                                    'failed': 'Wait'},
                                       autonomy={'released': Autonomy.Off,
                                                 'canceled': Autonomy.Off,
                                                 'failed': Autonomy.Off},
                                       remapping={'tool_name': 'tool_name',
                                                  'reason': 'reason'})

        # ==============================================================
        # Sub-SM: Phase 08 — Expose
        # ==============================================================
        _sm_phase_08_7 = OperatableStateMachine(outcomes=['next', 'back', 'done', 'aborted'])
        _sm_phase_08_7.userdata.tool_name = ''
        _sm_phase_08_7.userdata.reason = ''
        with _sm_phase_08_7:
            OperatableStateMachine.add('Announce',
                                       AnnouncePhaseState(phase_id=8,
                                                          phase_name='Expose',
                                                          phase_desc='Subperiosteal exposure, place retractors.',
                                                          allowed_tools=['retractor', 'tissue_forceps', 'scalpel_handle']),
                                       transitions={'announced': 'Wait'},
                                       autonomy={'announced': Autonomy.Off})
            OperatableStateMachine.add('Wait',
                                       WaitForOperatorCommandState(allowed_tools=['retractor', 'tissue_forceps', 'scalpel_handle']),
                                       transitions={'tool_selected': 'RunHandover',
                                                    'next': 'next',
                                                    'back': 'back',
                                                    'done': 'done'},
                                       autonomy={'tool_selected': Autonomy.Off,
                                                 'next': Autonomy.Off,
                                                 'back': Autonomy.Off,
                                                 'done': Autonomy.Off},
                                       remapping={'tool_name': 'tool_name'})
            OperatableStateMachine.add('RunHandover',
                                       RunHandoverActionState(action_topic=self.run_handover_action,
                                                              timeout_sec=self.handover_timeout_sec),
                                       transitions={'released': 'Wait',
                                                    'canceled': 'Wait',
                                                    'failed': 'Wait'},
                                       autonomy={'released': Autonomy.Off,
                                                 'canceled': Autonomy.Off,
                                                 'failed': Autonomy.Off},
                                       remapping={'tool_name': 'tool_name',
                                                  'reason': 'reason'})

        # ==============================================================
        # Sub-SM: Phase 09 — Fix
        # ==============================================================
        _sm_phase_09_8 = OperatableStateMachine(outcomes=['next', 'back', 'done', 'aborted'])
        _sm_phase_09_8.userdata.tool_name = ''
        _sm_phase_09_8.userdata.reason = ''
        with _sm_phase_09_8:
            OperatableStateMachine.add('Announce',
                                       AnnouncePhaseState(phase_id=9,
                                                          phase_name='Fix',
                                                          phase_desc='Reduce, K-wires, volar locking plate under C-arm. Robot passive; hand tissue_forceps on demand.',
                                                          allowed_tools=['tissue_forceps']),
                                       transitions={'announced': 'Wait'},
                                       autonomy={'announced': Autonomy.Off})
            OperatableStateMachine.add('Wait',
                                       WaitForOperatorCommandState(allowed_tools=['tissue_forceps']),
                                       transitions={'tool_selected': 'RunHandover',
                                                    'next': 'next',
                                                    'back': 'back',
                                                    'done': 'done'},
                                       autonomy={'tool_selected': Autonomy.Off,
                                                 'next': Autonomy.Off,
                                                 'back': Autonomy.Off,
                                                 'done': Autonomy.Off},
                                       remapping={'tool_name': 'tool_name'})
            OperatableStateMachine.add('RunHandover',
                                       RunHandoverActionState(action_topic=self.run_handover_action,
                                                              timeout_sec=self.handover_timeout_sec),
                                       transitions={'released': 'Wait',
                                                    'canceled': 'Wait',
                                                    'failed': 'Wait'},
                                       autonomy={'released': Autonomy.Off,
                                                 'canceled': Autonomy.Off,
                                                 'failed': Autonomy.Off},
                                       remapping={'tool_name': 'tool_name',
                                                  'reason': 'reason'})

        # ==============================================================
        # Sub-SM: Phase 10 — Close
        # ==============================================================
        _sm_phase_10_9 = OperatableStateMachine(outcomes=['next', 'back', 'done', 'aborted'])
        _sm_phase_10_9.userdata.tool_name = ''
        _sm_phase_10_9.userdata.reason = ''
        with _sm_phase_10_9:
            OperatableStateMachine.add('Announce',
                                       AnnouncePhaseState(phase_id=10,
                                                          phase_name='Close',
                                                          phase_desc='PQ over plate, subcutaneous + skin closure.',
                                                          allowed_tools=['needle_holder', 'tissue_forceps']),
                                       transitions={'announced': 'Wait'},
                                       autonomy={'announced': Autonomy.Off})
            OperatableStateMachine.add('Wait',
                                       WaitForOperatorCommandState(allowed_tools=['needle_holder', 'tissue_forceps']),
                                       transitions={'tool_selected': 'RunHandover',
                                                    'next': 'next',
                                                    'back': 'back',
                                                    'done': 'done'},
                                       autonomy={'tool_selected': Autonomy.Off,
                                                 'next': Autonomy.Off,
                                                 'back': Autonomy.Off,
                                                 'done': Autonomy.Off},
                                       remapping={'tool_name': 'tool_name'})
            OperatableStateMachine.add('RunHandover',
                                       RunHandoverActionState(action_topic=self.run_handover_action,
                                                              timeout_sec=self.handover_timeout_sec),
                                       transitions={'released': 'Wait',
                                                    'canceled': 'Wait',
                                                    'failed': 'Wait'},
                                       autonomy={'released': Autonomy.Off,
                                                 'canceled': Autonomy.Off,
                                                 'failed': Autonomy.Off},
                                       remapping={'tool_name': 'tool_name',
                                                  'reason': 'reason'})

        # ==============================================================
        # Top-level assembly
        # ==============================================================
        with _state_machine:
            OperatableStateMachine.add('Phase_01_Position',
                                       _sm_phase_01_0,
                                       transitions={'next': 'Phase_02_Skin',
                                                    'back': 'Phase_01_Position',
                                                    'done': 'case_done',
                                                    'aborted': 'aborted'},
                                       autonomy={'next': Autonomy.Off,
                                                 'back': Autonomy.Off,
                                                 'done': Autonomy.Off,
                                                 'aborted': Autonomy.Off})
            OperatableStateMachine.add('Phase_02_Skin',
                                       _sm_phase_02_1,
                                       transitions={'next': 'Phase_03_Subcutaneous',
                                                    'back': 'Phase_01_Position',
                                                    'done': 'case_done',
                                                    'aborted': 'aborted'},
                                       autonomy={'next': Autonomy.Off,
                                                 'back': Autonomy.Off,
                                                 'done': Autonomy.Off,
                                                 'aborted': Autonomy.Off})
            OperatableStateMachine.add('Phase_03_Subcutaneous',
                                       _sm_phase_03_2,
                                       transitions={'next': 'Phase_04_FCR_sheath_roof',
                                                    'back': 'Phase_02_Skin',
                                                    'done': 'case_done',
                                                    'aborted': 'aborted'},
                                       autonomy={'next': Autonomy.Off,
                                                 'back': Autonomy.Off,
                                                 'done': Autonomy.Off,
                                                 'aborted': Autonomy.Off})
            OperatableStateMachine.add('Phase_04_FCR_sheath_roof',
                                       _sm_phase_04_3,
                                       transitions={'next': 'Phase_05_FCR_sheath_floor',
                                                    'back': 'Phase_03_Subcutaneous',
                                                    'done': 'case_done',
                                                    'aborted': 'aborted'},
                                       autonomy={'next': Autonomy.Off,
                                                 'back': Autonomy.Off,
                                                 'done': Autonomy.Off,
                                                 'aborted': Autonomy.Off})
            OperatableStateMachine.add('Phase_05_FCR_sheath_floor',
                                       _sm_phase_05_4,
                                       transitions={'next': 'Phase_06_Deep_interval',
                                                    'back': 'Phase_04_FCR_sheath_roof',
                                                    'done': 'case_done',
                                                    'aborted': 'aborted'},
                                       autonomy={'next': Autonomy.Off,
                                                 'back': Autonomy.Off,
                                                 'done': Autonomy.Off,
                                                 'aborted': Autonomy.Off})
            OperatableStateMachine.add('Phase_06_Deep_interval',
                                       _sm_phase_06_5,
                                       transitions={'next': 'Phase_07_Pronator_quadratus',
                                                    'back': 'Phase_05_FCR_sheath_floor',
                                                    'done': 'case_done',
                                                    'aborted': 'aborted'},
                                       autonomy={'next': Autonomy.Off,
                                                 'back': Autonomy.Off,
                                                 'done': Autonomy.Off,
                                                 'aborted': Autonomy.Off})
            OperatableStateMachine.add('Phase_07_Pronator_quadratus',
                                       _sm_phase_07_6,
                                       transitions={'next': 'Phase_08_Expose',
                                                    'back': 'Phase_06_Deep_interval',
                                                    'done': 'case_done',
                                                    'aborted': 'aborted'},
                                       autonomy={'next': Autonomy.Off,
                                                 'back': Autonomy.Off,
                                                 'done': Autonomy.Off,
                                                 'aborted': Autonomy.Off})
            OperatableStateMachine.add('Phase_08_Expose',
                                       _sm_phase_08_7,
                                       transitions={'next': 'Phase_09_Fix',
                                                    'back': 'Phase_07_Pronator_quadratus',
                                                    'done': 'case_done',
                                                    'aborted': 'aborted'},
                                       autonomy={'next': Autonomy.Off,
                                                 'back': Autonomy.Off,
                                                 'done': Autonomy.Off,
                                                 'aborted': Autonomy.Off})
            OperatableStateMachine.add('Phase_09_Fix',
                                       _sm_phase_09_8,
                                       transitions={'next': 'Phase_10_Close',
                                                    'back': 'Phase_08_Expose',
                                                    'done': 'case_done',
                                                    'aborted': 'aborted'},
                                       autonomy={'next': Autonomy.Off,
                                                 'back': Autonomy.Off,
                                                 'done': Autonomy.Off,
                                                 'aborted': Autonomy.Off})
            OperatableStateMachine.add('Phase_10_Close',
                                       _sm_phase_10_9,
                                       transitions={'next': 'Phase_10_Close',
                                                    'back': 'Phase_09_Fix',
                                                    'done': 'case_done',
                                                    'aborted': 'aborted'},
                                       autonomy={'next': Autonomy.Off,
                                                 'back': Autonomy.Off,
                                                 'done': Autonomy.Off,
                                                 'aborted': Autonomy.Off})

        return _state_machine
