"""GOOD document adapter: sanitize, merge partial exports, normalize, and hash."""

import hashlib
import json
from copy import deepcopy
from typing import Any

from projectg.application.ports.outbound.account_document_parser import PreparedAccountDocument
from projectg.infrastructure.serialization.good_importer import GoodImporter, GoodImportError


SECTIONS = ("characters", "weapons", "artifacts", "teams")

def canonical_state_hash(state) -> str:
    payload = json.dumps(
        state.canonical_state(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class GoodDocumentParser:
    def __init__(self, importer: GoodImporter):
        self._importer = importer

    def prepare(
        self,
        content: bytes,
        *,
        previous_effective_document: dict[str, Any] | None,
    ) -> PreparedAccountDocument:
        sanitized, incoming = self._sanitize(content)
        incoming = self._importer.parse(incoming)
        effective = deepcopy(previous_effective_document or {})

        for key in ("format", "version", "dbVersion", "goodDbVersion"):
            if key in incoming:
                effective[key] = incoming[key]

        supplied_sections: set[str] = set()
        for name in SECTIONS:
            aliases = (name, "savedTeams") if name == "teams" else (name,)
            supplied = next((key for key in aliases if key in incoming), None)
            if supplied is not None:
                effective[name] = incoming[supplied]
                supplied_sections.add(name)

        if "characters" not in effective:
            raise GoodImportError(
                "A first account import must include the characters section.",
                {"field": "characters", "problem": "no account snapshot exists to merge"},
            )

        try:
            parsed = self._importer.parse(effective)
            state = self._importer.normalize(parsed)
        except GoodImportError:
            raise

        canonical_hash = canonical_state_hash(state)
        return PreparedAccountDocument(
            raw_content=sanitized,
            raw_hash=hashlib.sha256(sanitized).hexdigest(),
            canonical_hash=canonical_hash,
            effective_document=effective,
            supplied_sections=frozenset(supplied_sections),
            state=state,
            importer_version=self._importer.version,
        )

    @staticmethod
    def _sanitize(content: bytes) -> tuple[bytes, dict[str, Any]]:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise GoodImportError(
                "GOOD document must be UTF-8 encoded.",
                {"problem": "invalid UTF-8 encoding", "byteOffset": exc.start},
            ) from exc
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise GoodImportError("Invalid JSON", {"problem": str(exc)}) from exc
        if not isinstance(value, dict):
            # Reuse the importer's public validation/error shape.
            return content, value
        if "materials" not in value:
            return content, value
        value = dict(value)
        value.pop("materials", None)
        sanitized = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return sanitized, value
