from projectg.infrastructure.persistence.sqlite.models import (
    Account,
    CharacterTargetPreset,
    CharacterTargetVersion,
)
from projectg.infrastructure.persistence.sqlite.targets.idempotency_repository import (
    TargetIdempotencyRepository,
)
from projectg.infrastructure.persistence.sqlite.targets.preset_repository import (
    TargetPresetRepository,
)
from projectg.infrastructure.persistence.sqlite.targets.target_writer import TargetWriter


def _account() -> Account:
    return Account(id="default", name="Default", server_region="NA")


def test_target_idempotency_fingerprint_is_stable_across_selected_key_order():
    repository = TargetIdempotencyRepository()
    payload = {"version": 1, "targets": {"Fischl": {"level": 80}}}

    first = repository.fingerprint(payload, {"Fischl", "RaidenShogun"})
    second = repository.fingerprint(payload, {"RaidenShogun", "Fischl"})

    assert first == second
    assert len(first) == 64


def test_prepare_preset_activation_is_read_only_until_apply(db_session):
    account = _account()
    db_session.add(account)
    db_session.add_all(
        [
            CharacterTargetPreset(
                account_id=account.id,
                character_key="Fischl",
                preset_key="default",
                label="Default",
                is_active=True,
            ),
            CharacterTargetPreset(
                account_id=account.id,
                character_key="Fischl",
                preset_key="on-field",
                label="On-field",
                is_active=False,
            ),
            CharacterTargetVersion(
                account_id=account.id,
                character_key="Fischl",
                preset_key="default",
                version=1,
                target_json={"level": 80},
            ),
            CharacterTargetVersion(
                account_id=account.id,
                character_key="Fischl",
                preset_key="on-field",
                version=2,
                target_json={"level": 90},
            ),
        ]
    )
    db_session.flush()

    repository = TargetPresetRepository(TargetWriter())
    plan = repository.prepare_activation(db_session, account, "Fischl", "on-field")

    assert plan is not None and plan.changed is True
    assert db_session.get(
        CharacterTargetPreset, (account.id, "Fischl", "default")
    ).is_active is True
    assert db_session.get(
        CharacterTargetPreset, (account.id, "Fischl", "on-field")
    ).is_active is False

    result = repository.activate(db_session, account, "Fischl", "on-field", plan)

    assert result.changed is True
    assert db_session.get(
        CharacterTargetPreset, (account.id, "Fischl", "default")
    ).is_active is False
    assert db_session.get(
        CharacterTargetPreset, (account.id, "Fischl", "on-field")
    ).is_active is True
