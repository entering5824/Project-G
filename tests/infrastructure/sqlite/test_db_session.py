from sqlalchemy import event

from projectg.infrastructure.persistence.sqlite.session import SQLITE_BUSY_TIMEOUT_MS, make_engine


def test_sqlite_file_engine_enables_wal_foreign_keys_and_busy_timeout(tmp_path):
    database = tmp_path / "concurrent.db"
    engine = make_engine(f"sqlite:///{database.as_posix()}")
    try:
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA journal_mode").scalar_one().lower() == "wal"
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
            assert connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one() == SQLITE_BUSY_TIMEOUT_MS
    finally:
        engine.dispose()


def test_sqlite_transaction_mode_can_reserve_writer_before_handler_reads(tmp_path):
    engine = make_engine(f"sqlite:///{(tmp_path / 'writer.db').as_posix()}")
    statements = []
    event.listen(engine, "before_cursor_execute", lambda _conn, _cursor, statement, *_args: statements.append(statement))
    try:
        with engine.connect().execution_options(sqlite_begin_mode="IMMEDIATE") as connection:
            connection.exec_driver_sql("SELECT 1").scalar_one()
            connection.rollback()
        assert "BEGIN IMMEDIATE" in statements
    finally:
        engine.dispose()
