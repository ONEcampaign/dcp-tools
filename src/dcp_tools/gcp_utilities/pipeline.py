"""Loading data to a custom Knowledge Graph.

For original documentation, see:
https://colab.research.google.com/github/datacommonsorg/tools/blob/master/notebooks/Your_Data_Commons_Load_Data_Workflow.ipynb

"""

from os import PathLike
from pathlib import Path

from dcp_tools.gcp_utilities.clients import get_gcs_client
from dcp_tools.gcp_utilities.settings import KGSettings
from dcp_tools.gcp_utilities.storage import (
    sync_directory_to_gcs,
    upload_directory_to_gcs,
)


def upload_to_cloud_storage(
    settings: KGSettings,
    directory: str | PathLike[str] | None = None,
    sync: bool = False,
) -> None:
    """Upload data to Google Cloud Storage.

    Args:
        settings (KGSettings): The settings for the Knowledge Graph.
        directory (str | PathLike | None): The local directory to upload. If None,
            ``settings.local_path`` is used.
        sync (bool): If True, delete remote blobs that no longer have a local
            counterpart after uploading. Defaults to False.

    Raises:
        ValueError: If `directory` is None and `LOCAL_PATH` is not set.

    """

    if directory is None:
        if settings.local_path is None:
            raise ValueError("Pass a directory to upload, or set LOCAL_PATH.")
        directory = settings.local_path
    directory = Path(directory)

    gcs_client = get_gcs_client(
        credentials=settings.gcp_credentials, project=settings.gcp_project_id
    )
    bucket = gcs_client.get_bucket(settings.gcs_bucket_name)

    upload_fn = sync_directory_to_gcs if sync else upload_directory_to_gcs
    upload_fn(
        bucket=bucket,
        directory=directory,
        gcs_folder_name=settings.gcs_input_folder_path,
    )
