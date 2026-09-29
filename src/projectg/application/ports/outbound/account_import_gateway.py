"""Persistence contract used by account-import application workflows."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from projectg.application.ports.outbound.account_document_parser import PreparedAccountDocument
from projectg.domain.account.models import CharacterState, WeaponState


@dataclass(frozen=True)
class AccountImportContext:
    current_snapshot_id: str | None
    current_canonical_hash: str | None
    coverage: dict[str, str]
    effective_document: dict[str, Any] | None
    previous_characters: tuple[CharacterState, ...] = ()
    previous_weapons: tuple[WeaponState, ...] = ()


@dataclass(frozen=True)
class AccountImportPreview:
    duplicate: bool
    coverage: dict[str, str]
    characters: int
    weapons: int
    equipped_artifacts: int
    teams: int
    warnings: tuple[str, ...]
    abnormal_changes: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class AccountImportCommit:
    snapshot_id: str
    previous_snapshot_id: str | None


@dataclass(frozen=True)
class AccountImportCommitCommand:
    snapshot_id: str
    imported_at: datetime
    expected_previous_snapshot_id: str | None
    coverage: dict[str, str]
    document: PreparedAccountDocument


class AccountImportGateway(Protocol):
    def load_context(self) -> AccountImportContext: ...

    def commit_validated(self, command: AccountImportCommitCommand) -> AccountImportCommit: ...
