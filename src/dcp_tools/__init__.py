from importlib.metadata import version

from .custom_data.config_utils import merge_configs_from_directory
from .custom_data.data_management import CustomDataManager
from .custom_data.schema_tools import csv_metadata_to_mfc_file, csv_metadata_to_nodes

__version__ = version("dcp-tools")


__all__ = [
    "CustomDataManager",
    "csv_metadata_to_mfc_file",
    "csv_metadata_to_nodes",
    "merge_configs_from_directory",
]
