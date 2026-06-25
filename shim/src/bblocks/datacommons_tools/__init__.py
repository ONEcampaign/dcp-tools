"""Deprecated alias for :mod:`dcp_tools`.

``bblocks-datacommons-tools`` was renamed to ``dcp-tools``. Importing
``bblocks.datacommons_tools`` (or any of its submodules) still works: it emits a
``DeprecationWarning`` and transparently redirects to ``dcp_tools``.
"""

import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import sys
import warnings
from collections.abc import Sequence
from types import ModuleType

_OLD = "bblocks.datacommons_tools"
_NEW = "dcp_tools"

warnings.warn(
    "bblocks-datacommons-tools has been renamed to dcp-tools. Import 'dcp_tools' "
    "instead; the 'bblocks.datacommons_tools' import path is deprecated and will "
    "be removed in a future release.",
    DeprecationWarning,
    stacklevel=2,
)


class _RedirectFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Resolve every ``bblocks.datacommons_tools.*`` name to its ``dcp_tools`` twin.

    A single finder covers the whole subtree, so deep imports
    (``from bblocks.datacommons_tools.gcp_utilities import ...``) keep working
    without mirroring the package layout.
    """

    def find_spec(
        self,
        name: str,
        path: Sequence[str] | None = None,
        target: ModuleType | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        if name == _OLD or name.startswith(_OLD + "."):
            return importlib.util.spec_from_loader(name, self)
        return None

    def create_module(self, spec: importlib.machinery.ModuleSpec) -> ModuleType:
        target = _NEW + spec.name[len(_OLD) :]
        module = importlib.import_module(target)
        sys.modules[spec.name] = module
        return module

    def exec_module(self, module: ModuleType) -> None:
        # The real module was already executed by import_module in create_module.
        pass


sys.meta_path.insert(0, _RedirectFinder())

# Re-export the top-level public API so ``from bblocks.datacommons_tools import X``
# resolves directly off this package object.
_pkg = importlib.import_module(_NEW)
__all__ = list(getattr(_pkg, "__all__", []))
globals().update({name: getattr(_pkg, name) for name in __all__})
__version__ = getattr(_pkg, "__version__", None)
