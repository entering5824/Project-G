"""SQLite facade composing typed planner persistence facts."""
from sqlalchemy.orm import Session
from projectg.application.ports.outbound.planner_gateway import PlannerFacts
from projectg.domain.planning.config import PlannerConfig
from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.persistence.sqlite.planner.snapshot_reader import PlannerSnapshotReader
from projectg.infrastructure.persistence.sqlite.planner.configuration_reader import PlannerConfigurationReader
from projectg.infrastructure.persistence.sqlite.planner.team_reader import PlannerTeamReader
from projectg.infrastructure.persistence.sqlite.planner.tier_reader import PlannerTierReader
from projectg.infrastructure.persistence.sqlite.planner.artifact_evaluation_reader import PlannerArtifactEvaluationReader


class SqlitePlannerGateway:
    def __init__(self, db: Session, configuration: Settings):
        self._account_id = configuration.account_id
        self._snapshot = PlannerSnapshotReader(db)
        self._configuration = PlannerConfigurationReader(db)
        self._teams = PlannerTeamReader(db)
        self._tiers = PlannerTierReader(db)
        self._evaluations = PlannerArtifactEvaluationReader(db)

    def load_config(self) -> PlannerConfig:
        return self._configuration.read_planner()

    def load_facts(self) -> PlannerFacts:
        quality = self._configuration.read_artifact_quality()
        personal, theater = self._configuration.read_build_intents(self._account_id)
        snapshot = self._snapshot.read(self._account_id)
        if snapshot.snapshot_id is None:
            return PlannerFacts(has_snapshot=False, artifact_quality_config=quality,
                                personal_priorities=personal, theater_config=theater)
        return PlannerFacts(
            has_snapshot=True,
            priority_overrides=self._configuration.read_priorities(self._account_id),
            personal_priority_keys=self._configuration.read_personal_priority_keys(self._account_id),
            personal_priorities=personal,
            theater_config=theater,
            characters=snapshot.characters,
            teams=self._teams.read(self._account_id, snapshot.snapshot_id),
            artifact_evaluations=self._evaluations.read(self._account_id),
            artifact_quality_config=quality,
            tier_pack=self._tiers.read(self._account_id),
        )
