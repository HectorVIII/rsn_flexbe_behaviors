"""FlexBE state: announce the current surgical phase.

For now this only writes to the FlexBE App log; when a TTS backend is
wired up it can also publish the announcement text.
"""

from flexbe_core import EventState, Logger


class AnnouncePhaseState(EventState):
    """
    Announce a phase by logging its id, name, description and tool list.

    -- phase_id      int      Phase index (1..N).
    -- phase_name    string   Human-readable phase name.
    -- phase_desc    string   Longer description.
    -- allowed_tools list     List of tool ids allowed in this phase.
    """

    def __init__(self, phase_id, phase_name, phase_desc="", allowed_tools=None):
        super().__init__(outcomes=["announced"])
        self._phase_id = int(phase_id)
        self._phase_name = str(phase_name)
        self._phase_desc = str(phase_desc)
        self._allowed_tools = list(allowed_tools or [])

    def on_enter(self, userdata):
        tools = ", ".join(self._allowed_tools) if self._allowed_tools else "(no handover)"
        Logger.loginfo(
            f"── Phase {self._phase_id}: {self._phase_name} ─────────"
        )
        if self._phase_desc:
            Logger.loginfo(f"   {self._phase_desc}")
        Logger.loginfo(f"   tools: {tools}")

    def execute(self, userdata):
        return "announced"
