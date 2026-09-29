"""Filesystem adapter for validated local GameData packs."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from projectg.application.ports.outbound.clock import Clock
from projectg.application.ports.outbound.game_data_pack_storage import (
    GameDataInstallReceipt,
    GameDataPackDocument,
)
from projectg.application.ports.outbound.id_generator import IdGenerator
from projectg.infrastructure.game_data.json.loader import load_game_data


class LocalGameDataPackStorage:
    def __init__(self, installed_path: Path | str, clock: Clock, id_generator: IdGenerator):
        self._installed_path = Path(installed_path)
        self._clock = clock
        self._id_generator = id_generator

    def load_installed(self) -> GameDataPackDocument:
        return GameDataPackDocument(
            path=str(self._installed_path),
            data=load_game_data(self._installed_path),
        )

    def load_candidate(self, path: str) -> GameDataPackDocument:
        source = Path(path)
        if not source.is_file():
            raise ValueError("GameData pack file does not exist.")
        return GameDataPackDocument(path=str(source), data=load_game_data(source, strict=True))

    def install_candidate(self, path: str) -> GameDataInstallReceipt:
        source = Path(path)
        if not source.is_file():
            raise ValueError("GameData pack file does not exist.")

        destination = self._installed_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        backup_dir = destination.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        backup_path: Path | None = None
        if destination.is_file():
            stamp = self._clock.now().strftime("%Y%m%dT%H%M%SZ")
            backup_path = backup_dir / (
                f"game_data-{stamp}-{self._id_generator.next_id()[:8]}.json"
            )
            shutil.copy2(destination, backup_path)

        temp = destination.with_name(
            f".{destination.name}.{self._id_generator.next_id()}.tmp"
        )
        try:
            shutil.copy2(source, temp)
            # Validate the bytes after the copy as an integrity check before replace.
            load_game_data(temp, strict=True)
            os.replace(temp, destination)
        finally:
            temp.unlink(missing_ok=True)

        return GameDataInstallReceipt(
            path=str(destination),
            backup_path=str(backup_path) if backup_path else None,
        )

    def export_installed(self, destination: str) -> str:
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self._installed_path, target)
        return str(target)
