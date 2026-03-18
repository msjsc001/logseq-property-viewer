import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app_constants import APP_IDENTIFIER
from config import get_log_dir


_LOGGER_CACHE: dict[str, logging.Logger] = {}


def get_logger(name: str = APP_IDENTIFIER) -> logging.Logger:
    logger = _LOGGER_CACHE.get(name)
    if logger is not None:
        return logger

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        log_dir = get_log_dir()
        log_file = Path(log_dir) / f"{APP_IDENTIFIER}.log"
        handler = RotatingFileHandler(
            log_file,
            maxBytes=1_024_000,
            backupCount=3,
            encoding="utf-8",
        )
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    _LOGGER_CACHE[name] = logger
    return logger
