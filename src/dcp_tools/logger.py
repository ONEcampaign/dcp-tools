"""Deprecated: dcp-tools no longer configures logging.

Each module logs under ``dcp_tools``, and the importing application configures
logging. This module remains until 2.0 so existing imports keep working.
"""

import logging
import warnings

warnings.warn(
    "dcp_tools.logger is deprecated and will be removed in 2.0. "
    "Configure logging.getLogger('dcp_tools') instead.",
    DeprecationWarning,
    stacklevel=2,
)

logger = logging.getLogger("dcp_tools")


def get_logger(name: str | None = None) -> logging.Logger:
    return logging.getLogger("dcp_tools" if name is None else name)
