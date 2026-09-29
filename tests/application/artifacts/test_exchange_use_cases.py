from projectg.application.artifacts.errors import ArtifactExchangeError
from projectg.application.ports.outbound.artifact_document_parser import ParsedArtifactEvaluation
from projectg.application.ports.outbound.artifact_exchange_gateway import (
    ArtifactCharacterContext,
    ArtifactExchangeCommit,
    ArtifactExchangeContext,
)
from projectg.application.use_cases.artifacts.confirm_exchange import (
    ConfirmArtifactExchange,
    ConfirmArtifactExchangeRequest,
)
from projectg.application.use_cases.artifacts.preview_exchange import (
    PreviewArtifactExchange,
    PreviewArtifactExchangeRequest,
)
from projectg.domain.artifacts.models import ArtifactQualityConfig


QUALITY = ArtifactQualityConfig(
    version=4,
    adapter_type="rv",
    thresholds={"POOR": 100, "ACCEPTABLE": 200, "GOOD": 300, "EXCELLENT": 400},
)


def _context(*, snapshot_id="snapshot-1", owned=("Amber",), existing=False):
    return ArtifactExchangeContext(
        snapshot_id=snapshot_id,
        owned_character_keys=frozenset(owned),
        quality_config=QUALITY,
        characters={
            key: ArtifactCharacterContext(
                character_key=key,
                artifact_fingerprint=f"fp-{key}",
                target_quality="GOOD",
                target_version=3,
                existing_evaluation=existing,
            )
            for key in owned
        },
    )


class FakeParser:
    def __init__(self, rows):
        self.rows = tuple(rows)
        self.payload = None

    def parse(self, payload):
        self.payload = payload
        return self.rows


class FakeGateway:
    def __init__(self, context=None):
        self.context = context or _context()
        self.command = None

    def load_context(self):
        return self.context

    def commit_validated(self, command):
        self.command = command
        return ArtifactExchangeCommit(({"evaluation": "saved"},))


def test_preview_parses_external_payload_and_enriches_quality_in_application():
    parser = FakeParser((ParsedArtifactEvaluation(0, "Amber", {"rv": 250.0}),))
    gateway = FakeGateway(_context(existing=True))

    result = PreviewArtifactExchange(gateway, parser).execute(
        PreviewArtifactExchangeRequest({"format": "AEF"})
    )

    assert parser.payload == {"format": "AEF"}
    assert result.snapshot_id == "snapshot-1"
    assert result.valid_count == 1
    row = result.evaluations[0]
    assert row["valid"] is True
    assert row["quality"]["qualityStatus"] == "BELOW_TARGET"
    assert row["quality"]["targetVersion"] == 3
    assert "creates a new version" in row["warnings"][0]


def test_preview_marks_unowned_character_invalid_without_persistence_policy():
    parser = FakeParser((ParsedArtifactEvaluation(0, "Diluc", {"rv": 250.0}),))
    result = PreviewArtifactExchange(FakeGateway(), parser).execute(
        PreviewArtifactExchangeRequest({})
    )

    assert result.valid_count == 0
    assert result.evaluations[0]["errors"][0]["code"] == "UNKNOWN_CHARACTER_KEY"


def test_confirm_builds_validated_decision_before_gateway_commit():
    gateway = FakeGateway()
    request = ConfirmArtifactExchangeRequest(({
        "characterKey": "Amber",
        "metrics": {"rv": 350.0, "extraMetrics": {}},
        "manuallyCorrected": True,
    },), "snapshot-1")

    result = ConfirmArtifactExchange(gateway).execute(request)

    decision = gateway.command.evaluations[0]
    assert gateway.command.expected_snapshot_id == "snapshot-1"
    assert decision.character_key == "Amber"
    assert decision.metrics["rv"] == 350.0
    assert decision.quality.status.value == "COMPLETE"
    assert decision.normalized_metrics["qualityConfigVersion"] == 4
    assert decision.normalized_metrics["manuallyCorrected"] is True
    assert result.evaluations == ({"evaluation": "saved"},)


def test_confirm_rejects_duplicate_character_before_gateway_mutation():
    gateway = FakeGateway()
    request = ConfirmArtifactExchangeRequest((
        {"characterKey": "Amber", "metrics": {"rv": 350}},
        {"characterKey": "Amber", "metrics": {"rv": 360}},
    ), "snapshot-1")

    try:
        ConfirmArtifactExchange(gateway).execute(request)
        assert False, "duplicate evaluation must be rejected"
    except ArtifactExchangeError as exc:
        assert "duplicate" in str(exc).lower()
    assert gateway.command is None


def test_confirm_normalizes_character_key_before_duplicate_check():
    gateway = FakeGateway()
    request = ConfirmArtifactExchangeRequest((
        {"characterKey": "Amber", "metrics": {"rv": 350}},
        {"characterKey": " Amber ", "metrics": {"rv": 360}},
    ), "snapshot-1")

    try:
        ConfirmArtifactExchange(gateway).execute(request)
        assert False, "normalized duplicate evaluation must be rejected"
    except ArtifactExchangeError as exc:
        assert "duplicate" in str(exc).lower()
    assert gateway.command is None


def test_confirm_rejects_stale_preview_snapshot_before_gateway_mutation():
    gateway = FakeGateway(_context(snapshot_id="snapshot-2"))
    request = ConfirmArtifactExchangeRequest((
        {"characterKey": "Amber", "metrics": {"rv": 350}},
    ), "snapshot-1")

    try:
        ConfirmArtifactExchange(gateway).execute(request)
        assert False, "stale preview must be rejected"
    except ArtifactExchangeError as exc:
        assert "snapshot changed" in str(exc).lower()
    assert gateway.command is None
