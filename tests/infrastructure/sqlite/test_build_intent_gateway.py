from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from projectg.infrastructure.persistence.sqlite.build_intent_gateway import SqliteBuildIntentGateway
from projectg.infrastructure.persistence.sqlite.models import Account


class _Mutations:
    def __init__(self, db):
        self.db = db

    @contextmanager
    def transaction(self):
        yield SimpleNamespace(db=self.db, checkpoint=lambda reason: None)


class _SessionScope:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        return self.db

    def __exit__(self, *args):
        return False


def test_personal_and_theater_intents_round_trip_per_account(db_session):
    db_session.add(Account(id="intent-account", name="Intent", server_region="ASIA"))
    db_session.flush()
    gateway = SqliteBuildIntentGateway(lambda: _SessionScope(db_session), _Mutations(db_session), "intent-account")
    gateway.save_personal("Vesna", "WANT_BUILD")
    gateway.save_personal("Amber", "COMPLETE")
    gateway.save_theater({"elements": ["Pyro", "Hydro", "Anemo"], "requiredCharacters": 4,
                          "selectedCharacters": ["Amber"], "excludedCharacters": [], "manualSelection": True})
    assert gateway.load() == {
        "personal": {"Vesna": "WANT_BUILD", "Amber": "COMPLETE"},
        "theater": {"elements": ["Pyro", "Hydro", "Anemo"], "requiredCharacters": 4,
                    "selectedCharacters": ["Amber"], "excludedCharacters": [], "manualSelection": True},
    }
    gateway.save_personal("Vesna", "COMPLETE")
    assert gateway.load()["personal"]["Vesna"] == "COMPLETE"


def test_theater_intent_requires_three_distinct_elements(db_session):
    db_session.add(Account(id="intent-account", name="Intent", server_region="ASIA"))
    db_session.flush()
    gateway = SqliteBuildIntentGateway(lambda: _SessionScope(db_session), _Mutations(db_session), "intent-account")
    with pytest.raises(ValueError, match="ba nguyên tố"):
        gateway.save_theater({"elements": ["Pyro", "Pyro", "Hydro"], "requiredCharacters": 4})
