from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8").lower()


def test_normal_windows_launch_is_native_desktop_not_web_server():
    run = _text("run.bat")
    setup = _text("setup.bat")
    start = _text("scripts/start-planner.ps1")

    assert "pyside6" in run
    assert ".[desktop]" in setup
    assert "npm ci" not in setup
    assert "npm run" not in setup
    assert "dist\\index.html" not in run
    assert "uvicorn" not in start
    assert "localhost" not in start
    assert "-m projectg.main" in start


def test_desktop_pyinstaller_build_bundles_database_migrations_and_native_services():
    build = _text("scripts/build_desktop.ps1")

    assert "alembic.ini" in build
    assert "\\migrations;migrations" in build
    assert "src\\projectg\\main.py" in build
    assert "data\\static\\genshin-impact" in build
