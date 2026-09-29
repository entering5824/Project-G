"""Persistence boundary for versioned character targets."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class TargetImportContext:
    available_character_keys: frozenset[str]
    latest_versions: dict[str, int]
    account_imported: bool


@dataclass(frozen=True)
class TargetPresetContext:
    character_key: str
    owned: bool
    current_target: dict[str, Any] | None
    current_preset_key: str | None
    existing_preset_keys: frozenset[str]


@dataclass(frozen=True)
class TargetImportPreview:
    payload: Any
    preview: dict[str, Any]


@dataclass(frozen=True)
class TargetOperationResult:
    values: dict[str, Any]


class TargetGateway(Protocol):
    def import_context(self) -> TargetImportContext: ...

    def commit_validated(
        self,
        *,
        payload: object,
        selected_targets: dict[str, dict],
        operation_id: str,
        preview: dict[str, Any],
    ) -> TargetOperationResult: ...

    def preset_context(self, character_key: str) -> TargetPresetContext: ...

    def create_preset(
        self,
        *,
        character_key: str,
        preset_key: str,
        label: str,
        cloned_target: dict[str, Any],
        cloned_from_preset: str,
    ) -> TargetOperationResult: ...

    def activate_preset(self, character_key: str, preset_key: str) -> TargetOperationResult: ...
