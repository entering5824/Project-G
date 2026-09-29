from sqlalchemy.orm import sessionmaker

from projectg.infrastructure.persistence.sqlite.data_health_gateway import SqliteDataHealthFactsGateway
from projectg.infrastructure.persistence.sqlite.models import (
    Account,
    ArtifactQualityConfigVersion,
    Snapshot,
    SnapshotCharacter,
    SnapshotWeapon,
)
from projectg.infrastructure.persistence.sqlite.session import DatabaseMaintenanceGate


def test_data_health_gateway_returns_only_persisted_account_and_quality_facts(db_session):
    snapshot = Snapshot(
        id="snap-1",
        account_id="default",
        good_format="GOOD",
        good_version=1,
        good_db_version=60,
        raw_file_hash="raw",
        canonical_state_hash="state",
        previous_snapshot_id=None,
        importer_version="1",
        raw_path="snapshot.json",
    )
    account = Account(
        id="default",
        name="Traveler",
        server_region="ASIA",
        current_snapshot_id="snap-1",
    )
    db_session.add_all([
        account,
        snapshot,
        SnapshotCharacter(
            snapshot_id="snap-1",
            character_key="Amber",
            level=80,
            ascension=5,
            constellation=0,
            talent_auto=8,
            talent_skill=8,
            talent_burst=8,
            equipped_weapon_instance_id="weapon-1",
        ),
        SnapshotWeapon(
            snapshot_id="snap-1",
            weapon_instance_id="weapon-1",
            weapon_key="FavoniusWarbow",
            level=80,
            ascension=5,
            refinement=1,
            location="Amber",
        ),
        ArtifactQualityConfigVersion(
            version=1,
            config_json={
                "adapterType": "rv",
                "thresholds": {
                    "POOR": 0.1,
                    "ACCEPTABLE": 0.3,
                    "GOOD": 0.6,
                    "EXCELLENT": 0.8,
                },
            },
        ),
    ])
    db_session.commit()

    factory = sessionmaker(bind=db_session.get_bind(), expire_on_commit=False)
    facts = SqliteDataHealthFactsGateway(
        factory, DatabaseMaintenanceGate(), "default"
    ).load_facts()

    assert facts.account_available is True
    assert facts.artifact_quality_configured is True
    assert facts.character_keys == ("Amber",)
    assert facts.equipped_weapon_keys == ("FavoniusWarbow",)
