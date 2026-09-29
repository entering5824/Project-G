"""JSON/file-system adapter for target import documents."""

from __future__ import annotations

import json
from pathlib import Path

from projectg.application.ports.outbound.target_document_source import TargetDocumentSource
from projectg.application.targets.errors import TargetOperationError


MAX_TARGET_DOCUMENT_BYTES = 10 * 1024 * 1024


class JsonTargetDocumentSource(TargetDocumentSource):
    def read(self, path: str) -> object:
        file = Path(path)
        try:
            if file.stat().st_size > MAX_TARGET_DOCUMENT_BYTES:
                raise TargetOperationError(
                    "TARGET_FILE_TOO_LARGE", "Target JSON exceeds 10 MiB.", {}
                )
            return json.loads(file.read_text(encoding="utf-8-sig"))
        except TargetOperationError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise TargetOperationError(
                "INVALID_TARGET_JSON", "Could not read Target JSON.", {"reason": str(exc)}
            ) from exc

    def encoded_size(self, payload: object) -> int:
        try:
            return len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        except (TypeError, ValueError, OverflowError) as exc:
            raise TargetOperationError(
                "INVALID_TARGET_JSON", "Could not encode Target JSON.", {"reason": str(exc)}
            ) from exc
