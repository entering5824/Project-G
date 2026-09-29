"""Atomic filesystem storage for sanitized raw GOOD account documents."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path


class AccountImportRawDocumentStorage:
    """Store raw import bytes outside SQLite and clean them up after failed transactions."""

    def __init__(self, snapshot_dir: Path):
        self._snapshot_dir = Path(snapshot_dir)

    def write(self, imported_at: datetime, raw_hash: str, content: bytes) -> Path:
        self._snapshot_dir.mkdir(parents=True, exist_ok=True)
        safe_name = f"{imported_at.strftime('%Y%m%dT%H%M%S%fZ')}_{raw_hash[:12]}.json"
        path = self._snapshot_dir / safe_name
        temporary = path.with_suffix(".tmp")
        try:
            temporary.write_bytes(content)
            os.replace(temporary, path)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return path

    @staticmethod
    def delete(path: Path) -> None:
        path.unlink(missing_ok=True)
