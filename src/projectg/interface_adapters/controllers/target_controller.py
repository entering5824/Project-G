"""Translate target import and preset operations for the desktop."""

from projectg.application.use_cases.targets.activate_target_preset import (
    ActivateTargetPreset,
    ActivateTargetPresetRequest,
)
from projectg.application.use_cases.targets.commit_targets import CommitTargetRequest, CommitTargets
from projectg.application.use_cases.targets.create_target_preset import (
    CreateTargetPreset,
    CreateTargetPresetRequest,
)
from projectg.application.use_cases.targets.preview_target_file import PreviewTargetFile, PreviewTargetFileRequest
from projectg.application.use_cases.targets.preview_target_payload import (
    PreviewTargetPayload,
    PreviewTargetPayloadRequest,
)


class TargetController:
    def __init__(self, preview_file: PreviewTargetFile, preview_payload: PreviewTargetPayload,
                 commit: CommitTargets, create_preset: CreateTargetPreset,
                 activate_preset: ActivateTargetPreset):
        self._preview_file, self._preview_payload = preview_file, preview_payload
        self._commit, self._create_preset = commit, create_preset
        self._activate_preset = activate_preset

    def preview_file(self, path: str) -> dict:
        result = self._preview_file.execute(PreviewTargetFileRequest(path))
        return {"payload": result.payload, "preview": result.preview}

    def preview_payload(self, payload: object) -> dict:
        result = self._preview_payload.execute(PreviewTargetPayloadRequest(payload))
        return {"payload": result.payload, "preview": result.preview}

    def commit(self, payload: object, selected: set[str], operation_id: str) -> dict:
        return self._commit.execute(CommitTargetRequest(payload, frozenset(selected), operation_id)).values

    def create_preset(self, character_key: str, label: str) -> dict:
        return self._create_preset.execute(CreateTargetPresetRequest(character_key, label)).values

    def activate_preset(self, character_key: str, preset_key: str) -> dict:
        return self._activate_preset.execute(
            ActivateTargetPresetRequest(character_key, preset_key)).values
