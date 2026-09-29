"""Shared limits for account import requests."""

MAX_IMPORT_BYTES = 25 * 1024 * 1024


def validate_import_size(content: bytes) -> None:
    if len(content) > MAX_IMPORT_BYTES:
        raise ValueError("GOOD file exceeds 25 MiB")
