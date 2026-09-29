import pytest

from projectg.application.ports.outbound.target_gateway import (
    TargetImportContext,
    TargetOperationResult,
    TargetPresetContext,
)
from projectg.application.targets.errors import TargetOperationError
from projectg.application.use_cases.targets.activate_target_preset import (
    ActivateTargetPreset,
    ActivateTargetPresetRequest,
)
from projectg.application.use_cases.targets.commit_targets import CommitTargetRequest, CommitTargets
from projectg.application.use_cases.targets.create_target_preset import (
    CreateTargetPreset,
    CreateTargetPresetRequest,
)
from projectg.application.use_cases.targets.preview_target_file import (
    PreviewTargetFile,
    PreviewTargetFileRequest,
)
from projectg.application.use_cases.targets.preview_target_payload import (
    PreviewTargetPayload,
    PreviewTargetPayloadRequest,
)


def _target():
    return {
        "level": 80,
        "ascension": 5,
        "importance": {"level": 0.8, "ascension": 0.8},
        "talents": {
            name: {"enabled": False, "target": 1, "importance": 0.0}
            for name in ("normal", "skill", "burst")
        },
        "weapon": {"targetLevel": 1, "importance": 0.0},
        "artifact": {
            "enabled": False,
            "targetQuality": "GOOD",
            "importance": 0.0,
            "primarySets": [],
            "alternativeSets": [],
            "gate": {},
        },
        "notes": "",
    }


class FakeDocumentSource:
    def __init__(self, payload=None):
        self.payload = payload
        self.path = None

    def read(self, path):
        self.path = path
        return self.payload

    def encoded_size(self, payload):
        return 128


class FakeGateway:
    def __init__(self):
        self.commit_request = None
        self.created = None
        self.activated = None
        self.context = TargetImportContext(frozenset({"Amber"}), {}, True)
        self.preset = TargetPresetContext(
            "Amber",
            True,
            _target(),
            "default",
            frozenset({"default"}),
        )

    def import_context(self):
        return self.context

    def commit_validated(self, **kwargs):
        self.commit_request = kwargs
        return TargetOperationResult({"saved": sorted(kwargs["selected_targets"])})

    def preset_context(self, character_key):
        return self.preset

    def create_preset(self, **kwargs):
        self.created = kwargs
        return TargetOperationResult({"presetKey": kwargs["preset_key"]})

    def activate_preset(self, character_key, preset_key):
        self.activated = (character_key, preset_key)
        return TargetOperationResult({"presetKey": preset_key})


def test_target_file_preview_reads_document_then_applies_application_policy():
    payload = {"version": 1, "targets": {"Amber": _target()}}
    gateway = FakeGateway()
    source = FakeDocumentSource(payload)

    result = PreviewTargetFile(gateway, source).execute(PreviewTargetFileRequest("targets.json"))

    assert source.path == "targets.json"
    assert result.payload == payload
    assert result.preview["validTargets"] == ["Amber"]


def test_target_payload_preview_uses_account_context_without_persistence_validation():
    payload = {"version": 1, "targets": {"Amber": _target()}}
    gateway = FakeGateway()

    result = PreviewTargetPayload(gateway, FakeDocumentSource()).execute(
        PreviewTargetPayloadRequest(payload)
    )

    assert result.preview["canImport"] is True
    assert result.preview["willCreateOrUpdate"] == 1


def test_target_commit_validates_and_passes_only_selected_normalized_targets():
    payload = {"version": 1, "targets": {"Amber": _target()}}
    gateway = FakeGateway()
    request = CommitTargetRequest(payload, frozenset({"Amber"}), "operation-key-123456")

    result = CommitTargets(gateway, FakeDocumentSource()).execute(request)

    assert gateway.commit_request["operation_id"] == "operation-key-123456"
    assert list(gateway.commit_request["selected_targets"]) == ["Amber"]
    assert gateway.commit_request["selected_targets"]["Amber"]["level"] == 80
    assert result.values == {"saved": ["Amber"]}


def test_target_commit_rejects_missing_account_before_mutation():
    gateway = FakeGateway()
    gateway.context = TargetImportContext(frozenset(), {}, False)
    request = CommitTargetRequest(
        {"version": 1, "targets": {"Amber": _target()}},
        frozenset({"Amber"}),
        "operation-key-123456",
    )

    with pytest.raises(TargetOperationError) as error:
        CommitTargets(gateway, FakeDocumentSource()).execute(request)

    assert error.value.code == "ACCOUNT_NOT_IMPORTED"
    assert gateway.commit_request is None


def test_create_preset_generates_collision_free_key_in_domain_before_persisting():
    gateway = FakeGateway()
    gateway.preset = TargetPresetContext(
        "Amber",
        True,
        _target(),
        "default",
        frozenset({"default", "on-field", "on-field-2"}),
    )

    result = CreateTargetPreset(gateway).execute(CreateTargetPresetRequest("Amber", "On field"))

    assert gateway.created["preset_key"] == "on-field-3"
    assert gateway.created["label"] == "On field"
    assert gateway.created["cloned_from_preset"] == "default"
    assert result.values["presetKey"] == "on-field-3"


def test_activate_preset_rejects_unknown_preset_before_write():
    gateway = FakeGateway()

    with pytest.raises(TargetOperationError) as error:
        ActivateTargetPreset(gateway).execute(ActivateTargetPresetRequest("Amber", "missing"))

    assert error.value.code == "TARGET_PRESET_NOT_FOUND"
    assert gateway.activated is None
