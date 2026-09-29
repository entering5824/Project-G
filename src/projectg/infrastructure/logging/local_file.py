"""Rotating file logging for the local desktop installation."""

import logging
from logging.handlers import RotatingFileHandler

from projectg.infrastructure.configuration.settings import Settings


def configure_local_file_logging(configuration: Settings) -> None:
    try:
        configuration.log_dir.mkdir(parents=True, exist_ok=True)
        root = logging.getLogger()
        if not any(getattr(handler, "_project_g_log", False) for handler in root.handlers):
            handler = RotatingFileHandler(
                configuration.log_dir / "planner.log",
                maxBytes=2_000_000,
                backupCount=4,
                encoding="utf-8",
            )
            handler._project_g_log = True
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
            root.addHandler(handler)
    except OSError:
        logging.getLogger(__name__).warning("Local rotating log file is unavailable; logging to console only.")
