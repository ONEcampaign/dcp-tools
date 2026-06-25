# bblocks-datacommons-tools (deprecated)

This package has been renamed to [**dcp-tools**](https://pypi.org/project/dcp-tools/).

Installing `bblocks-datacommons-tools` pulls in `dcp-tools` and keeps the old
import path working: `import bblocks.datacommons_tools` (and any submodule)
transparently redirects to `dcp_tools` while emitting a `DeprecationWarning`.

Migrate at your convenience:

```python
# old
from bblocks.datacommons_tools import CustomDataManager

# new
from dcp_tools import CustomDataManager
```
