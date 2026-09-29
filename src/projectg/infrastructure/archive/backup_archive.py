"""ZIP archive mechanics for ProjectG backups.

The adapter owns archive safety, hashing, and extraction. Backup-format
compatibility itself is parsed by application.backups.policy.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from projectg.application.backups.errors import BackupError
from projectg.application.backups.models import BackupFileIntegrity, BackupManifest
from projectg.application.backups.policy import parse_backup_manifest

MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 25_000
MAX_ENTRY_UNCOMPRESSED_BYTES = 1024 * 1024 * 1024
MAX_COMPRESSION_RATIO = 200
MIN_RATIO_CHECK_BYTES = 10 * 1024 * 1024
REQUIRED_FILES = {"manifest.json", "settings.json", "database.sqlite"}


@dataclass(frozen=True)
class ArchiveInspection:
    manifest: BackupManifest
    names: tuple[str, ...]


def file_integrity(path: Path) -> BackupFileIntegrity:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return BackupFileIntegrity(digest.hexdigest(), size)


def bytes_integrity(content: bytes) -> BackupFileIntegrity:
    return BackupFileIntegrity(hashlib.sha256(content).hexdigest(), len(content))


class ZipBackupArchive:
    def write(
        self,
        destination: Path,
        *,
        database_copy: Path,
        settings_bytes: bytes,
        manifest: BackupManifest,
        snapshot_dir: Path,
        akasha_dir: Path,
    ) -> None:
        snapshot_files = (
            sorted(path for path in snapshot_dir.rglob("*") if path.is_file())
            if snapshot_dir.exists() else []
        )
        akasha_files = (
            sorted(path for path in akasha_dir.rglob("*") if path.is_file())
            if akasha_dir.exists() else []
        )
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            archive.write(database_copy, "database.sqlite")
            archive.writestr(
                "manifest.json",
                json.dumps(manifest.to_mapping(), ensure_ascii=False, indent=2),
            )
            archive.writestr("settings.json", settings_bytes)
            archive.writestr("snapshots/", "")
            for path in snapshot_files:
                archive.write(path, f"snapshots/{path.relative_to(snapshot_dir).as_posix()}")
            archive.writestr("akasha/", "")
            for path in akasha_files:
                archive.write(path, f"akasha/{path.relative_to(akasha_dir).as_posix()}")

    def inspect(self, content: bytes | BinaryIO) -> ArchiveInspection:
        if isinstance(content, bytes) and len(content) > MAX_ARCHIVE_BYTES:
            raise BackupError("BACKUP_TOO_LARGE", "Backup archive exceeds the upload size limit.")
        if not isinstance(content, bytes) and content.seekable():
            position = content.tell()
            content.seek(0, os.SEEK_END)
            size = content.tell()
            content.seek(position)
            if size > MAX_ARCHIVE_BYTES:
                raise BackupError(
                    "BACKUP_TOO_LARGE", "Backup archive exceeds the upload size limit.",
                    {"sizeBytes": size, "maxBytes": MAX_ARCHIVE_BYTES},
                )
        try:
            archive = zipfile.ZipFile(io.BytesIO(content) if isinstance(content, bytes) else content)
        except Exception as exc:
            raise BackupError("BACKUP_INVALID_ARCHIVE", "File is not a valid ZIP backup.") from exc

        with archive:
            names: set[str] = set()
            total = 0
            entries = archive.infolist()
            if len(entries) > MAX_ARCHIVE_ENTRIES:
                raise BackupError(
                    "BACKUP_TOO_MANY_ENTRIES", "Backup contains too many archive entries.",
                    {"entryCount": len(entries), "maxEntries": MAX_ARCHIVE_ENTRIES},
                )
            for info in entries:
                name = info.filename.replace("\\", "/")
                path = PurePosixPath(name)
                mode = (info.external_attr >> 16) & 0xFFFF
                if path.is_absolute() or ".." in path.parts or (path.parts and ":" in path.parts[0]):
                    raise BackupError(
                        "BACKUP_UNSAFE_PATH", "Archive contains an unsafe path.", {"path": info.filename})
                if mode & 0o170000 == 0o120000:
                    raise BackupError(
                        "BACKUP_UNSAFE_PATH", "Archive may not contain symbolic links.", {"path": info.filename})
                if name in names and not info.is_dir():
                    raise BackupError(
                        "BACKUP_DUPLICATE_PATH", "Archive contains duplicate file paths.", {"path": name})
                if not (
                    name in REQUIRED_FILES
                    or name in {"snapshots/", "akasha/"}
                    or name.startswith("snapshots/")
                    or name.startswith("akasha/")
                ):
                    raise BackupError(
                        "BACKUP_UNEXPECTED_PATH",
                        "Archive contains a file outside the backup layout.",
                        {"path": name},
                    )
                names.add(name)
                if info.file_size > MAX_ENTRY_UNCOMPRESSED_BYTES:
                    raise BackupError(
                        "BACKUP_ENTRY_TOO_LARGE", "An archive entry exceeds the per-file safety limit.",
                        {"path": name, "uncompressedBytes": info.file_size,
                         "maxBytes": MAX_ENTRY_UNCOMPRESSED_BYTES},
                    )
                if (
                    info.file_size >= MIN_RATIO_CHECK_BYTES
                    and info.file_size / max(info.compress_size, 1) > MAX_COMPRESSION_RATIO
                ):
                    raise BackupError(
                        "BACKUP_COMPRESSION_RATIO", "An archive entry exceeds the allowed compression ratio.",
                        {"path": name, "maxRatio": MAX_COMPRESSION_RATIO},
                    )
                total += info.file_size
                if total > MAX_UNCOMPRESSED_BYTES:
                    raise BackupError("BACKUP_TOO_LARGE", "Uncompressed backup exceeds the safety limit.")

            missing = REQUIRED_FILES - names
            if missing:
                raise BackupError(
                    "BACKUP_REQUIRED_FILE_MISSING", "Backup is missing required files.",
                    {"files": sorted(missing)},
                )
            info_by_name = {info.filename.replace("\\", "/"): info for info in entries}
            for metadata_name in ("manifest.json", "settings.json"):
                if info_by_name[metadata_name].file_size > 1024 * 1024:
                    raise BackupError(
                        "BACKUP_METADATA_TOO_LARGE", "Backup metadata file exceeds the safety limit.",
                        {"path": metadata_name},
                    )
            try:
                raw_manifest = json.loads(archive.read("manifest.json"))
            except Exception as exc:
                raise BackupError("BACKUP_INVALID_MANIFEST", "Backup manifest is invalid JSON.") from exc
            manifest = parse_backup_manifest(raw_manifest)

            try:
                settings_data = json.loads(archive.read("settings.json"))
                if not isinstance(settings_data, dict) or not isinstance(settings_data.get("accountId"), str):
                    raise ValueError("settings.json must contain accountId")
            except Exception as exc:
                raise BackupError("BACKUP_INVALID_SETTINGS", "Backup settings are invalid.") from exc

            if manifest.backup_schema_version >= 2:
                expected_files = {name for name in names if not name.endswith("/") and name != "manifest.json"}
                if set(manifest.files) != expected_files:
                    raise BackupError(
                        "BACKUP_INTEGRITY_MANIFEST_INVALID",
                        "File integrity manifest does not match archive entries.",
                    )
                for name in sorted(expected_files):
                    expected = manifest.files[name]
                    if expected.size_bytes != info_by_name[name].file_size:
                        raise BackupError(
                            "BACKUP_INTEGRITY_MISMATCH",
                            "Archive entry size does not match its manifest.", {"path": name})
                    digest = hashlib.sha256()
                    with archive.open(info_by_name[name]) as source:
                        while chunk := source.read(1024 * 1024):
                            digest.update(chunk)
                    if digest.hexdigest() != expected.sha256:
                        raise BackupError(
                            "BACKUP_INTEGRITY_MISMATCH",
                            "Archive entry hash does not match its manifest.", {"path": name})
            return ArchiveInspection(manifest, tuple(sorted(names)))

    def extract(self, content: bytes | BinaryIO, destination: Path) -> ArchiveInspection:
        if not isinstance(content, bytes) and content.seekable():
            content.seek(0)
        inspection = self.inspect(content)
        if not isinstance(content, bytes) and content.seekable():
            content.seek(0)
        with zipfile.ZipFile(io.BytesIO(content) if isinstance(content, bytes) else content) as archive:
            archive.extractall(destination)
        return inspection
