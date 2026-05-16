import logging
from datetime import datetime

import pytz

from kb.config import LOG_DIR, TIMEZONE, ensure_directories


ensure_directories()


class LocalFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):  # noqa: N802
        dt = datetime.fromtimestamp(record.created, tz=pytz.utc).astimezone(
            pytz.timezone(TIMEZONE)
        )
        return dt.strftime(datefmt or "%Y-%m-%d %H:%M:%S")


def _next_log_file() -> str:
    existing = sorted(LOG_DIR.glob("cognitive_os_*.log"))
    seq = 1
    if existing:
        suffix = existing[-1].stem.split("_")[-1]
        if suffix.isdigit():
            seq = int(suffix) + 1
    return str(LOG_DIR / f"cognitive_os_{seq:04d}.log")


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("cognitive_os")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = LocalFormatter("%(asctime)s | %(levelname)s | %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    file_handler = logging.FileHandler(_next_log_file(), encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file_handler)
    logger.propagate = False
    return logger


logger = setup_logger()
