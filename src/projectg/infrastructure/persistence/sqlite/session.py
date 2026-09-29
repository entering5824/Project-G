from pathlib import Path
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Condition

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

SQLITE_BUSY_TIMEOUT_MS = 10_000


class DatabaseMaintenanceGate:
    """Allow concurrent request sessions while making restore exclusive."""
    def __init__(self):
        self._condition = Condition()
        self._active_sessions = 0
        self._maintenance = False
        self._maintenance_waiters = 0

    @contextmanager
    def session(self):
        with self._condition:
            while self._maintenance or self._maintenance_waiters:
                self._condition.wait()
            self._active_sessions += 1
        try:
            yield
        finally:
            with self._condition:
                self._active_sessions -= 1
                self._condition.notify_all()

    @contextmanager
    def exclusive(self):
        with self._condition:
            self._maintenance_waiters += 1
            try:
                while self._maintenance or self._active_sessions:
                    self._condition.wait()
                self._maintenance = True
            finally:
                self._maintenance_waiters -= 1
        try:
            yield
        finally:
            with self._condition:
                self._maintenance = False
                self._condition.notify_all()


def make_engine(url: str):
    if url.startswith("sqlite:///") and url != "sqlite:///:memory:":
        Path(url.removeprefix("sqlite:///" )).parent.mkdir(parents=True, exist_ok=True)
    is_sqlite = url.startswith("sqlite")
    kwargs = {"check_same_thread": False, "timeout": SQLITE_BUSY_TIMEOUT_MS / 1000} if is_sqlite else {}
    engine = create_engine(url, connect_args=kwargs)
    if is_sqlite:
        @event.listens_for(engine, "connect")
        def configure_sqlite_connection(dbapi_connection, _connection_record):
            # Let SQLAlchemy own BEGIN/COMMIT boundaries instead of sqlite3's
            # legacy implicit transaction behavior.
            dbapi_connection.isolation_level = None
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
            finally:
                cursor.close()

        # WAL is persistent for a file database, so initialize it once per engine.
        database = make_url(url).database
        if database not in (None, "", ":memory:"):
            with engine.connect() as connection:
                connection.exec_driver_sql("PRAGMA journal_mode=WAL")
                connection.commit()

        @event.listens_for(engine, "begin")
        def begin_sqlite_transaction(connection):
            # Read sessions remain deferred; mutating application services can
            # request IMMEDIATE when they must reserve SQLite's writer slot.
            mode = connection.get_execution_options().get("sqlite_begin_mode", "DEFERRED")
            connection.exec_driver_sql("BEGIN IMMEDIATE" if mode == "IMMEDIATE" else "BEGIN")
    return engine


@dataclass(frozen=True)
class DatabaseRuntime:
    engine: Engine
    session_factory: sessionmaker
    maintenance_gate: DatabaseMaintenanceGate


def create_database_runtime(url: str) -> DatabaseRuntime:
    database_engine = make_engine(url)
    return DatabaseRuntime(
        engine=database_engine,
        session_factory=sessionmaker(bind=database_engine, expire_on_commit=False),
        maintenance_gate=DatabaseMaintenanceGate(),
    )
