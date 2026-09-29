"""Translate desktop import inputs and application responses."""

from typing import Any

from projectg.application.use_cases.imports.commit_account_import import (
    CommitAccountImport,
    CommitAccountImportRequest,
)
from projectg.application.use_cases.imports.commit_good_file import CommitGoodFile, CommitGoodFileRequest
from projectg.application.use_cases.imports.preview_account_import import (
    PreviewAccountImport,
    PreviewAccountImportRequest,
)
from projectg.application.use_cases.imports.preview_good_file import PreviewGoodFile, PreviewGoodFileRequest
from projectg.domain.game_catalog.models import GameData
from projectg.interface_adapters.mappers.good_snapshot import snapshot_to_good


class AccountImportController:
    def __init__(self, game_data: GameData, preview_good: PreviewGoodFile,
                 commit_good: CommitGoodFile, preview_import: PreviewAccountImport,
                 commit_import: CommitAccountImport):
        self._game_data = game_data
        self._preview_good = preview_good
        self._commit_good = commit_good
        self._preview_import = preview_import
        self._commit_import = commit_import

    def preview_good_file(self, path: str) -> dict[str, Any]:
        return _preview_payload(self._preview_good.execute(PreviewGoodFileRequest(path)),
                                translate_coverage=True)

    def commit_good_file(self, path: str, *, allow_regression: bool = False) -> dict[str, Any]:
        return _commit_payload(self._commit_good.execute(CommitGoodFileRequest(path, allow_regression)))

    def preview_snapshot(self, value: str | bytes | dict[str, Any]) -> dict[str, Any]:
        content, report = snapshot_to_good(value, self._game_data)
        return {**_preview_payload(self._preview_import.execute(PreviewAccountImportRequest(content))),
                "report": report}

    def commit_snapshot(self, value: str | bytes | dict[str, Any], *,
                        allow_regression: bool = False) -> dict[str, Any]:
        content, report = snapshot_to_good(value, self._game_data)
        return {**_commit_payload(self._commit_import.execute(
            CommitAccountImportRequest(content, allow_regression))), "report": report}


def _preview_payload(result, *, translate_coverage: bool = False) -> dict[str, Any]:
    coverage = result.coverage
    if translate_coverage:
        coverage = {key: ("included" if value == "CURRENT" else "retained stale")
                    for key, value in coverage.items()}
    return {
        "duplicate": result.duplicate,
        "coverage": coverage,
        "characters": result.characters,
        "weapons": result.weapons,
        "equippedArtifacts": result.equipped_artifacts,
        "teams": result.teams,
        "warnings": list(result.warnings),
        "abnormalChanges": list(result.abnormal_changes),
    }


def _commit_payload(result) -> dict[str, Any]:
    return {"snapshotId": result.snapshot_id,
            "previousSnapshotId": result.previous_snapshot_id}
