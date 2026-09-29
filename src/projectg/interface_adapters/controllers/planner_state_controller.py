"""Translate planner run and pin actions for desktop presentation."""

from projectg.application.use_cases.planner_state.preview_pin import PreviewPin, PreviewPinRequest
from projectg.application.use_cases.planner_state.set_pin import SetPin, SetPinRequest
from projectg.application.use_cases.planner_state.list_plan_runs import ListPlanRuns, ListPlanRunsRequest
from projectg.application.use_cases.planner_state.replay_plan_run import ReplayPlanRun, ReplayPlanRunRequest


class PlannerStateController:
    def __init__(self, list_runs: ListPlanRuns, replay_run: ReplayPlanRun,
                 preview_pin: PreviewPin, set_pin: SetPin):
        self._list_runs, self._replay_run = list_runs, replay_run
        self._preview_pin, self._set_pin = preview_pin, set_pin

    def list_runs(self, limit: int = 50) -> list[dict]:
        return [{"id": row.id, "createdAt": row.created_at, "kind": row.kind,
                 "snapshotId": row.snapshot_id, "plannerConfigVersion": row.planner_config_version,
                 "primaryTask": row.primary_task}
                for row in self._list_runs.execute(ListPlanRunsRequest(limit))]

    def replay_run(self, run_id: str) -> dict:
        row = self._replay_run.execute(ReplayPlanRunRequest(run_id))
        return {"planRunId": row.plan_run_id, "recordedAt": row.recorded_at,
                "result": row.result, "normalizedInput": row.normalized_input,
                "targetVersions": row.target_versions,
                "plannerConfigVersion": row.planner_config_version,
                "sourceAvailability": row.source_availability, "context": row.context,
                "hysteresisState": row.hysteresis_state, "engineVersion": row.engine_version,
                "gameDataVersion": row.game_data_version, "rvFormulaVersion": row.rv_formula_version,
                "switchThreshold": row.switch_threshold}

    def preview_pin(self, character_key: str) -> dict:
        row = self._preview_pin.execute(PreviewPinRequest(character_key))
        return {"characterKey": row.character_key, "candidate": row.candidate,
                "strategicTask": row.strategic_task, "conflicts": list(row.conflicts),
                "requiresConfirmation": row.requires_confirmation, "status": row.status}

    def set_pin(self, character_key: str | None) -> dict:
        row = self._set_pin.execute(SetPinRequest(character_key))
        return {"pinnedCharacterKey": row.pinned_character_key}
