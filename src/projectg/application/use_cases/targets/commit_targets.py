"""Commit a selected subset of a validated target import."""

from dataclasses import dataclass

from projectg.application.ports.outbound.target_document_source import TargetDocumentSource
from projectg.application.ports.outbound.target_gateway import TargetGateway, TargetOperationResult
from projectg.application.targets.errors import TargetOperationError
from projectg.application.targets.import_policy import (
    build_target_import_preview,
    select_target_import,
    validate_operation_id,
)


MAX_TARGET_DOCUMENT_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class CommitTargetRequest:
    payload: object
    selected_keys: frozenset[str]
    operation_id: str


class CommitTargets:
    def __init__(self, gateway: TargetGateway, document_source: TargetDocumentSource):
        self._gateway = gateway
        self._document_source = document_source

    def execute(self, request: CommitTargetRequest) -> TargetOperationResult:
        operation_id = validate_operation_id(request.operation_id)
        if self._document_source.encoded_size(request.payload) > MAX_TARGET_DOCUMENT_BYTES:
            raise TargetOperationError("TARGET_FILE_TOO_LARGE", "Target JSON exceeds 10 MiB.", {})
        context = self._gateway.import_context()
        if not context.account_imported:
            raise TargetOperationError(
                "ACCOUNT_NOT_IMPORTED", "Import a GOOD snapshot before targets.", {}
            )
        preview, valid = build_target_import_preview(
            request.payload, context.available_character_keys, context.latest_versions
        )
        selected_targets = select_target_import(valid, request.selected_keys, preview)
        return self._gateway.commit_validated(
            payload=request.payload,
            selected_targets=selected_targets,
            operation_id=operation_id,
            preview=preview,
        )
