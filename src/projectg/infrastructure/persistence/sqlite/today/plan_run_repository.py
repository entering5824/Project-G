"""Persistence primitive for immutable Today PlanRun records."""

from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from projectg.application.ports.outbound.id_generator import IdGenerator
from projectg.domain.game_catalog.models import GameData
from projectg.infrastructure.persistence.sqlite.models import CharacterTargetVersion, PlanRun
from projectg.infrastructure.persistence.sqlite.planner_config import config_payload


class TodayPlanRunRepository:
    def __init__(self, id_generator: IdGenerator, game_data: GameData):
        self._ids = id_generator
        self._game = game_data

    @staticmethod
    def _target_versions(db: Session, account_id: str) -> dict[str, int]:
        rows = db.scalars(
            select(CharacterTargetVersion)
            .where(CharacterTargetVersion.account_id == account_id)
            .order_by(CharacterTargetVersion.character_key, CharacterTargetVersion.version.desc())
        ).all()
        versions: dict[str, int] = {}
        for row in rows:
            versions.setdefault(row.character_key, row.version)
        return versions

    @staticmethod
    def _source_availability(output: dict) -> dict:
        return {
            task["id"]: {
                "availability": task.get("availability"),
                "source": task.get("source"),
                "nextAvailableDate": task.get("nextAvailableDate"),
            }
            for section in ("quickActions", "farming", "unavailable", "blocked")
            for task in output[section]
        }

    @staticmethod
    def _normalized_input(planner_input, planner_config) -> dict:
        return {
            "characters": {key: asdict(value) for key, value in planner_input.characters.items()},
            "targets": planner_input.character_targets,
            "tiers": {key: asdict(value) for key, value in planner_input.tiers.items()},
            "tierAssignments": planner_input.tier_assignments,
            "priorityOverrides": planner_input.priority_overrides,
            "savedTeamMembers": sorted(planner_input.saved_team_members),
            "primaryTeamMembers": sorted(planner_input.primary_team_members),
            "plannerConfig": config_payload(planner_config),
            "artifactEvaluations": planner_input.artifact_evaluations,
            "artifactQualityConfig": (
                planner_input.artifact_quality_config.to_dict()
                if planner_input.artifact_quality_config
                else None
            ),
            "artifactDomains": planner_input.artifact_domains,
            "repositoryIssues": [],
        }

    def add(
        self,
        db: Session,
        *,
        account_id: str,
        snapshot_id: str | None,
        output: dict,
        result,
        planner_input,
        planner_config,
        config_version: str,
        dataset_hashes: dict,
    ) -> str:
        run_id = self._ids.next_id()
        output["planRunId"] = run_id
        output["datasetHashes"] = dict(dataset_hashes)
        db.add(
            PlanRun(
                id=run_id,
                account_id=account_id,
                kind="TODAY",
                snapshot_id=snapshot_id,
                normalized_input_json=self._normalized_input(planner_input, planner_config),
                target_versions_json=self._target_versions(db, account_id),
                planner_config_version=config_version,
                source_availability_json=self._source_availability(output),
                context_json={
                    "serverRegion": output["serverRegion"],
                    "gameDate": output["gameDate"],
                    "weekday": output["weekday"],
                    "accountSettings": output.get("accountSettings", {}),
                    "datasetHashes": output["datasetHashes"],
                },
                hysteresis_state_json=output["todayState"],
                engine_version=result.planner_version,
                game_data_version=self._game.metadata.get("data_version"),
                rv_formula_version="artifact-rv-1",
                switch_threshold=planner_config.reorder_threshold,
                result_json=output,
            )
        )
        return run_id
