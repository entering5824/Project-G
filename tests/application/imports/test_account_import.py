from datetime import datetime, timezone

import pytest

from projectg.application.imports.errors import AbnormalAccountChangeError, DuplicateSnapshotError
from projectg.application.ports.outbound.account_document_parser import PreparedAccountDocument
from projectg.application.ports.outbound.account_import_gateway import (
    AccountImportCommit,
    AccountImportContext,
)
from projectg.application.use_cases.imports.commit_account_import import (
    CommitAccountImport,
    CommitAccountImportRequest,
)
from projectg.application.use_cases.imports.commit_good_file import CommitGoodFile, CommitGoodFileRequest
from projectg.application.use_cases.imports.import_limits import MAX_IMPORT_BYTES
from projectg.application.use_cases.imports.preview_account_import import (
    PreviewAccountImport,
    PreviewAccountImportRequest,
)
from projectg.domain.account.models import CharacterState, NormalizedGood


STATE = NormalizedGood(
    "GOOD", 1, 60,
    [CharacterState("RaidenShogun", 80, 5, 0, 8, 9, 10)],
    [], [], [], ["warning"],
)


class MemoryParser:
    def __init__(self, *, canonical_hash="new-hash", state=STATE, sections=frozenset({"characters"})):
        self.content = None
        self.previous_effective_document = None
        self.canonical_hash = canonical_hash
        self.state = state
        self.sections = sections

    def prepare(self, content, *, previous_effective_document):
        self.content = content
        self.previous_effective_document = previous_effective_document
        return PreparedAccountDocument(
            raw_content=content,
            raw_hash="raw-hash",
            canonical_hash=self.canonical_hash,
            effective_document={"format": "GOOD", "characters": []},
            supplied_sections=self.sections,
            state=self.state,
            importer_version="test",
        )


class MemoryGateway:
    def __init__(self, context=None):
        self.context = context or AccountImportContext(None, None, {}, None)
        self.command = None

    def load_context(self):
        return self.context

    def commit_validated(self, command):
        self.command = command
        return AccountImportCommit(command.snapshot_id, command.expected_previous_snapshot_id)


class MemoryStorage:
    def __init__(self, content):
        self.content = content

    def read(self, key):
        assert key == "selected.good"
        return self.content

    def write(self, key, content):
        raise AssertionError("not used")

    def delete(self, key):
        raise AssertionError("not used")


class FixedClock:
    def now(self):
        return datetime(2026, 9, 26, tzinfo=timezone.utc)


class FixedIdGenerator:
    def next_id(self):
        return "new-snapshot"


def test_preview_import_parses_bytes_and_applies_application_coverage_policy():
    gateway = MemoryGateway(AccountImportContext(
        "old", "old-hash", {"weapons": "old"}, {"format": "GOOD"}))
    parser = MemoryParser()
    preview = PreviewAccountImport(gateway, parser)

    result = preview.execute(PreviewAccountImportRequest(b"GOOD bytes"))

    assert parser.content == b"GOOD bytes"
    assert parser.previous_effective_document == {"format": "GOOD"}
    assert result.characters == 1
    assert result.coverage == {"characters": "CURRENT", "weapons": "old",
                               "artifacts": "old", "teams": "old"}


def test_good_file_use_case_reads_storage_and_commits_a_validated_command():
    gateway = MemoryGateway()
    parser = MemoryParser()
    storage = MemoryStorage(b"GOOD bytes")
    commit = CommitGoodFile(
        storage,
        CommitAccountImport(gateway, parser, FixedClock(), FixedIdGenerator()),
    )

    result = commit.execute(CommitGoodFileRequest("selected.good", allow_regression=True))

    assert parser.content == b"GOOD bytes"
    assert gateway.command.snapshot_id == "new-snapshot"
    assert gateway.command.coverage["characters"] == "new-snapshot"
    assert result.snapshot_id == "new-snapshot"


def test_import_size_limit_is_enforced_before_parser_or_gateway_call():
    gateway = MemoryGateway()
    parser = MemoryParser()
    preview = PreviewAccountImport(gateway, parser)

    with pytest.raises(ValueError, match="25 MiB"):
        preview.execute(PreviewAccountImportRequest(b"x" * (MAX_IMPORT_BYTES + 1)))
    assert parser.content is None


def test_duplicate_detection_is_application_policy():
    gateway = MemoryGateway(AccountImportContext("old", "same", {}, {"format": "GOOD"}))
    parser = MemoryParser(canonical_hash="same")
    commit = CommitAccountImport(gateway, parser, FixedClock(), FixedIdGenerator())

    with pytest.raises(DuplicateSnapshotError):
        commit.execute(CommitAccountImportRequest(b"GOOD"))
    assert gateway.command is None


def test_regression_detection_is_application_policy_and_can_be_overridden():
    previous = CharacterState("RaidenShogun", 80, 5, 0, 8, 9, 10)
    lowered = NormalizedGood(
        "GOOD", 1, 60,
        [CharacterState("RaidenShogun", 79, 5, 0, 8, 9, 10)], [], [], [], [],
    )
    gateway = MemoryGateway(AccountImportContext(
        "old", "old-hash", {"characters": "old"}, {"format": "GOOD"},
        previous_characters=(previous,),
    ))
    parser = MemoryParser(state=lowered)
    commit = CommitAccountImport(gateway, parser, FixedClock(), FixedIdGenerator())

    with pytest.raises(AbnormalAccountChangeError) as error:
        commit.execute(CommitAccountImportRequest(b"GOOD"))
    assert error.value.changes == [
        {"characterKey": "RaidenShogun", "field": "level", "before": 80, "after": 79}
    ]

    result = commit.execute(CommitAccountImportRequest(b"GOOD", allow_regression=True))
    assert result.snapshot_id == "new-snapshot"
