"""Tests for the deprecated ``bblocks-datacommons-tools`` shim distribution.

The shim installs a ``MetaPathFinder`` into ``sys.meta_path`` and registers
modules under the old name in ``sys.modules`` on import, so it is exercised in a
subprocess to avoid polluting the test interpreter's import state.
"""

import os
import subprocess
import sys
from pathlib import Path

SHIM_SRC = Path(__file__).resolve().parents[1] / "shim" / "src"

_REDIRECT_CHECK = """
import warnings

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    from bblocks.datacommons_tools import CustomDataManager
    # deep / submodule imports must redirect too (documented surface)
    from bblocks.datacommons_tools.custom_data.models.data_files import ColumnMappings
    import bblocks.datacommons_tools.gcp_utilities  # noqa: F401

import dcp_tools
from dcp_tools.custom_data.models.data_files import ColumnMappings as NewColumnMappings

assert CustomDataManager is dcp_tools.CustomDataManager
assert ColumnMappings is NewColumnMappings
assert any(issubclass(w.category, DeprecationWarning) for w in caught)
print("shim-ok")
"""


def test_shim_redirects_with_deprecation_warning():
    """Importing the old name redirects to ``dcp_tools`` and warns once."""
    env = {**os.environ, "PYTHONPATH": str(SHIM_SRC)}
    result = subprocess.run(
        [sys.executable, "-c", _REDIRECT_CHECK],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "shim-ok" in result.stdout
