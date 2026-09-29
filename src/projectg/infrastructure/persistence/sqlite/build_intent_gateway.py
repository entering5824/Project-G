"""Persist account-wide personal and Imaginarium Theater build intent."""

from collections.abc import Callable
from sqlalchemy.orm import Session

from projectg.infrastructure.persistence.sqlite.models import AccountPlanningIntent
from projectg.infrastructure.persistence.sqlite.mutation_uow import SqliteMutationUnitOfWork


class SqliteBuildIntentGateway:
    def __init__(self, session_factory: Callable[[], Session], mutations: SqliteMutationUnitOfWork,
                 account_id: str):
        self._session_factory = session_factory
        self._mutations = mutations
        self._account_id = account_id

    def load(self) -> dict:
        with self._session_factory() as db:
            row = db.get(AccountPlanningIntent, self._account_id)
            return {"personal": dict(row.personal_json or {}) if row else {},
                    "theater": dict(row.theater_json or {}) if row else {}}

    def save_personal(self, key: str, state: str) -> dict:
        if state not in {"WANT_BUILD", "COMPLETE", "NORMAL"}:
            raise ValueError("Trạng thái ưu tiên nhân vật không hợp lệ.")
        with self._mutations.transaction() as effects:
            effects.checkpoint("PRE_BUILD_INTENT_CHANGE")
            row = self._row(effects.db)
            personal = dict(row.personal_json or {})
            if state == "NORMAL":
                personal.pop(key, None)
            else:
                personal[key] = state
            row.personal_json = personal
            effects.db.flush()
            return {"personal": personal, "theater": dict(row.theater_json or {})}

    def save_theater(self, config: dict) -> dict:
        elements = config.get("elements", [])
        if (not isinstance(elements, list) or len(elements) != 3 or len(set(elements)) != 3
                or any(not isinstance(item, str) or not item for item in elements)):
            raise ValueError("Chọn đúng ba nguyên tố khác nhau.")
        count = config.get("requiredCharacters")
        if type(count) is not int or not 1 <= count <= 100:
            raise ValueError("Số nhân vật cần chuẩn bị phải từ 1 đến 100.")
        selected = config.get("selectedCharacters", [])
        excluded = config.get("excludedCharacters", [])
        manual_selection = bool(config.get("manualSelection", bool(selected)))
        if not isinstance(selected, list) or not isinstance(excluded, list):
            raise ValueError("Danh sách nhân vật Nhà Hát không hợp lệ.")
        if any(not isinstance(item, str) or not item for item in [*selected, *excluded]):
            raise ValueError("Khóa nhân vật Nhà Hát không hợp lệ.")
        clean = {"elements": elements, "requiredCharacters": count,
                 "selectedCharacters": sorted(set(selected)),
                 "excludedCharacters": sorted(set(excluded)),
                 "manualSelection": manual_selection}
        with self._mutations.transaction() as effects:
            effects.checkpoint("PRE_THEATER_PREPARATION_CHANGE")
            row = self._row(effects.db)
            row.theater_json = clean
            effects.db.flush()
        return {**self.load(), "theater": clean}

    def _row(self, db: Session) -> AccountPlanningIntent:
        row = db.get(AccountPlanningIntent, self._account_id)
        if row is None:
            row = AccountPlanningIntent(account_id=self._account_id, personal_json={}, theater_json={})
            db.add(row)
            db.flush()
        return row
