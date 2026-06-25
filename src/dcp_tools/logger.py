"""
Centralised console logger usable across all project modules.
"""

import logging
import os
from typing import Final

_LOG_LEVEL: Final[str] = os.getenv("LOG_LEVEL", "INFO").upper()

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))


def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger("dcp-tools" if name is None else name)


logger = get_logger()
logger.setLevel(_LOG_LEVEL)
logger.addHandler(_handler)
logger.propagate = False
