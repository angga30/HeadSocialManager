"""Logging setup: rotating file under data/logs/ (+ optional console).

Idempotent so TUI and API can both call configure_logging() safely.

❕ TUI mode: pass console=False. Textual owns the terminal (alternate screen), so any log
that prints to the console every few seconds (e.g. APScheduler ticks) makes the UI flicker /
blink. In TUI mode logs go to the file only; tail data/logs/app.log.
"""

import logging
from logging.handlers import RotatingFileHandler

from headofsocial.config import settings

_configured = False

_FORMAT = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")

# Third-party loggers that are noisy at INFO (scheduler ticks, framework chatter).
_QUIET_LOGGERS: dict[str, int] = {
    "apscheduler": logging.WARNING,
    "litellm": logging.WARNING,
    "uvicorn.access": logging.WARNING,
    "httpx": logging.WARNING,
    "python_multipart": logging.WARNING,
    "urllib3": logging.WARNING,
}


def configure_logging(
    level: int = logging.INFO,
    file: bool = True,
    console: bool = True,
) -> None:
    """Install root handlers once. Call at TUI/API startup.

    Args:
        level: Root log level.
        file: Write a rotating log file under data/logs/.
        console: Also print to stderr. Pass False in the TUI to avoid UI flashing.
    """
    global _configured
    if _configured:
        return

    handlers: list[logging.Handler] = []

    if console:
        stream = logging.StreamHandler()
        stream.setFormatter(_FORMAT)
        handlers.append(stream)

    if file:
        log_dir = settings.resolved_data_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=2 * 1024 * 1024,  # 2 MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(_FORMAT)
        handlers.append(file_handler)

    # Fallback to a console handler if neither was requested (keep something visible).
    logging.basicConfig(level=level, handlers=handlers or [logging.StreamHandler()], force=True)

    # Quiet noisy third-party loggers so their INFO chatter doesn't flood us.
    for name, lvl in _QUIET_LOGGERS.items():
        logging.getLogger(name).setLevel(lvl)

    _configured = True


def log_file_path() -> str:
    return str(settings.resolved_data_dir / "logs" / "app.log")