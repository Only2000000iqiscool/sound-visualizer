from __future__ import annotations

import faulthandler
import logging
import os
import platform
import sys
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "sound-visualizer"
LATEST_LOG = LOG_DIR / "latest.log"

_configured = False


def setup_logging() -> Path:
    """Configure file logging for diagnostics and support."""
    global _configured
    if _configured:
        return LATEST_LOG

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    session_log = LOG_DIR / f"app-{datetime.now():%Y%m%d-%H%M%S}.log"

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(session_log, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    latest_handler = logging.FileHandler(LATEST_LOG, mode="w", encoding="utf-8")
    latest_handler.setLevel(logging.DEBUG)
    latest_handler.setFormatter(formatter)
    root.addHandler(latest_handler)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    fault_file = open(session_log, "a", encoding="utf-8")  # noqa: SIM115
    faulthandler.enable(file=fault_file, all_threads=True)

    def _excepthook(exc_type, exc_value, exc_tb) -> None:
        logging.getLogger("app").critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_tb),
        )
        sys.__excepthook__(exc_type, exc_value, exc_tb)

    sys.excepthook = _excepthook

    logger = logging.getLogger("app")
    logger.info("=" * 60)
    logger.info("Sound Visualizer session started")
    logger.info("Log file: %s", session_log)
    logger.info("Latest log: %s", LATEST_LOG)
    logger.info("Python: %s", sys.version.replace("\n", " "))
    logger.info("Platform: %s", platform.platform())
    logger.info("CWD: %s", Path.cwd())
    logger.info("DISPLAY: %s", os.environ.get("DISPLAY", "(unset)"))
    logger.info("WAYLAND_DISPLAY: %s", os.environ.get("WAYLAND_DISPLAY", "(unset)"))

    _configured = True
    return session_log


def log_paths() -> str:
    return f"{LATEST_LOG}\n{LOG_DIR}/app-*.log"
