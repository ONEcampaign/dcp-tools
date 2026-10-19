import logging
from importlib.metadata import version

from .custom_data.config_utils import merge_configs_from_directory
from .custom_data.data_management import CustomDataManager
from .custom_data.schema_tools import csv_metadata_to_mcf_file, csv_metadata_to_nodes

__version__ = version("dcp-tools")

# Until 2.0, configuring the old "dcp-tools" logger configures "dcp_tools".
logging.Logger.manager.loggerDict.setdefault("dcp-tools", logging.getLogger(__name__))


__all__ = [
    "CustomDataManager",
    "csv_metadata_to_mcf_file",
    "csv_metadata_to_nodes",
    "merge_configs_from_directory",
]
