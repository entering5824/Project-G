"""SQLite fact adapter for the desktop overview."""

from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from projectg.application.planning.projection import plan_result_to_dict
from projectg.application.ports.outbound.overview_gateway import OverviewCharacterFact, OverviewContext
from projectg.infrastructure.configuration.settings import Settings
from projectg.infrastructure.persistence.sqlite.models import (
    Account,
    PlannerTeam,
    SnapshotArtifact,
    Snapshot,
    SnapshotCharacter,
    SnapshotTeam,
    SnapshotWeapon,
    AccountPlanningIntent,
)
from projectg.infrastructure.persistence.sqlite.repositories.tier_pack import current_tier_pack
from projectg.infrastructure.persistence.sqlite.session import DatabaseMaintenanceGate


class SqliteOverviewGateway:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        maintenance_gate: DatabaseMaintenanceGate,
        configuration: Settings,
        game_data_provider: Callable,
        build_pack_provider: Callable,
        game_clock,
        today_planner_factory,
        planner_factory,
    ):
        self._session_factory = session_factory
        self._maintenance_gate = maintenance_gate
        self._configuration = configuration
        self._game_data_provider = game_data_provider
        self._build_pack_provider = build_pack_provider
        self._game_clock = game_clock
        self._today_planner_factory = today_planner_factory
        self._planner_factory = planner_factory

    def load_context(self) -> OverviewContext:
        with self._maintenance_gate.session():
            with self._session_factory() as db:
                account = db.get(Account, self._configuration.account_id)
                if account is None or not account.current_snapshot_id:
                    return OverviewContext(snapshot_id=None)

                execution = self._planner_factory(db).execute(limit=1_000)
                today = self._today_planner_factory().generate(db)
                roadmap = plan_result_to_dict(execution.result)
                intent = db.get(AccountPlanningIntent, account.id)
                personal_priorities = dict(intent.personal_json or {}) if intent else {}
                theater_config = dict(intent.theater_json or {}) if intent else {}
                roadmap["theaterPreparation"] = {
                    "config": theater_config,
                    "candidateKeys": execution.planner_input.theater_candidate_keys,
                    "selectedKeys": sorted(execution.planner_input.theater_priority_keys),
                    "readiness": execution.planner_input.theater_readiness,
                    "requiredCharacters": execution.planner_input.theater_required_characters,
                }
                snapshot_id = account.current_snapshot_id
                snapshot = db.get(Snapshot, snapshot_id)
                tier_pack = current_tier_pack(db, account.id)
                characters = db.scalars(
                    select(SnapshotCharacter)
                    .where(SnapshotCharacter.snapshot_id == snapshot_id)
                    .order_by(SnapshotCharacter.character_key)
                ).all()
                weapons = {
                    row.weapon_instance_id: row
                    for row in db.scalars(
                        select(SnapshotWeapon).where(SnapshotWeapon.snapshot_id == snapshot_id)
                    ).all()
                }
                artifacts: dict[str, list[dict]] = {}
                for row in db.scalars(
                    select(SnapshotArtifact).where(SnapshotArtifact.snapshot_id == snapshot_id)
                ).all():
                    artifacts.setdefault(row.character_key, []).append({
                        "slot": row.slot_key,
                        "set": row.set_key,
                        "level": row.level,
                        "mainStat": row.main_stat_key,
                        "substats": row.substats_json,
                        "rv": row.rv,
                        "rvStatus": row.rv_status,
                    })

                team_membership: dict[str, list[dict]] = {}
                imported_teams = db.scalars(
                    select(SnapshotTeam).where(SnapshotTeam.snapshot_id == snapshot_id)
                ).all()
                configured_teams = db.scalars(
                    select(PlannerTeam).where(PlannerTeam.account_id == account.id)
                ).all()
                for kind, rows in (("GOOD", imported_teams), ("PLANNER", configured_teams)):
                    for team in rows:
                        for member in team.members_json or []:
                            team_membership.setdefault(member, []).append({
                                "name": team.name or team.team_id,
                                "source": kind,
                                "isPrimary": bool(getattr(team, "is_primary", False)),
                            })

                game = self._game_data_provider()
                build_pack = self._build_pack_provider(set(game.characters))
                facts: list[OverviewCharacterFact] = []
                for row in characters:
                    weapon = weapons.get(row.equipped_weapon_instance_id)
                    facts.append(OverviewCharacterFact(
                        key=row.character_key,
                        priority_override=execution.planner_input.priority_overrides.get(row.character_key, "NORMAL"),
                        level=row.level,
                        ascension=row.ascension,
                        constellation=row.constellation,
                        talents={
                            "normal": row.talent_auto,
                            "skill": row.talent_skill,
                            "burst": row.talent_burst,
                        },
                        weapon=(
                            {
                                "key": weapon.weapon_key,
                                "level": weapon.level,
                                "ascension": weapon.ascension,
                                "refinement": weapon.refinement,
                            }
                            if weapon else None
                        ),
                        artifacts=tuple(sorted(
                            artifacts.get(row.character_key, []),
                            key=lambda item: item["slot"],
                        )),
                        tier_score=tier_pack["ratings"].get(row.character_key, {}).get("score"),
                        build_profiles=tuple({
                            "id": profile["id"],
                            "archetype": profile.get("archetype"),
                            "depth": profile.get("depth"),
                            "status": profile.get("status"),
                        } for profile in build_pack.profiles.get(row.character_key, [])),
                        knowledge_coverage=dict(build_pack.coverage),
                        teams=tuple(team_membership.get(row.character_key, [])),
                        element=(game.characters[row.character_key].element
                                 if row.character_key in game.characters else None),
                    ))

                return OverviewContext(
                    snapshot_id=snapshot_id,
                    today=today,
                    roadmap=roadmap,
                    characters=tuple(facts),
                    personal_priorities=personal_priorities,
                    theater_config=theater_config,
                    snapshot_imported_at=snapshot.imported_at if snapshot else None,
                )
