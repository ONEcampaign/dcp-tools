import importlib
import logging
import subprocess
import sys
from unittest.mock import patch

import pytest

from dcp_tools.cli import main

# Run in a fresh interpreter: other tests call the CLI, which sets levels.
_IMPORT_CHECK = """
import logging

import dcp_tools
import dcp_tools.gcp_utilities.ingestion
import dcp_tools.gcp_utilities.storage

loggers = {
    name: logger
    for name, logger in logging.root.manager.loggerDict.items()
    if name.split(".")[0] == "dcp_tools" and isinstance(logger, logging.Logger)
}
assert loggers
for name, logger in loggers.items():
    assert logger.handlers == [], name
    assert logger.level == logging.NOTSET, name
    assert logger.propagate, name
"""


def test_import_leaves_logging_configuration_to_the_application():
    """Importing dcp-tools sets no handlers or levels, and its loggers propagate."""
    result = subprocess.run(
        [sys.executable, "-c", _IMPORT_CHECK],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_cli_applies_log_level_to_dcp_tools_only(monkeypatch):
    """The CLI applies ``LOG_LEVEL`` to dcp-tools and leaves dependencies at WARNING."""
    monkeypatch.setenv("LOG_LEVEL", "debug")
    package_logger = logging.getLogger("dcp_tools")
    monkeypatch.setattr(package_logger, "level", logging.NOTSET)

    with (
        patch("dcp_tools.cli.main.logging.basicConfig") as basic_config,
        pytest.raises(SystemExit),
    ):
        main(["--help"])

    assert basic_config.call_args.kwargs["level"] == logging.WARNING
    assert package_logger.level == logging.DEBUG


def test_logger_module_is_deprecated(monkeypatch):
    """``dcp_tools.logger`` still imports, warns, and points at the package logger."""
    monkeypatch.delitem(sys.modules, "dcp_tools.logger", raising=False)

    with pytest.warns(DeprecationWarning, match="dcp_tools.logger"):
        module = importlib.import_module("dcp_tools.logger")

    assert module.logger is logging.getLogger("dcp_tools")


def test_old_logger_name_resolves_to_the_package_logger():
    """Configuring the old ``dcp-tools`` logger configures ``dcp_tools``."""
    assert logging.getLogger("dcp-tools") is logging.getLogger("dcp_tools")
