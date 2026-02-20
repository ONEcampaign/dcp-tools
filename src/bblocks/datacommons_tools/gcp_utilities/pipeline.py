"""Loading data to a custom Knowledge Graph.

For original documentation, see:
https://colab.research.google.com/github/datacommonsorg/tools/blob/master/notebooks/Your_Data_Commons_Load_Data_Workflow.ipynb

"""

from os import PathLike
from pathlib import Path

from bblocks.datacommons_tools.gcp_utilities.clients import (
    get_gcs_client,
    get_jobs_client,
    get_services_client,
)
from bblocks.datacommons_tools.gcp_utilities.jobs import (
    run_data_load_job,
    redeploy_cloud_run_service,
)
from bblocks.datacommons_tools.gcp_utilities.settings import KGSettings
from bblocks.datacommons_tools.gcp_utilities.storage import (
    upload_directory_to_gcs,
    sync_directory_to_gcs,
)


def upload_to_cloud_storage(
    settings: KGSettings,
    directory: PathLike | Path | None = None,
    sync: bool = False,
):
    """Upload data to Google Cloud Storage.

    Args:
        settings (KGSettings): The settings for the Knowledge Graph.
        directory (Path | None): The local directory to upload. If None, uses the default path.
        sync (bool): If True, delete remote blobs that no longer have a local
            counterpart after uploading. Defaults to False.

    """

    gcs_client = get_gcs_client(credentials=settings.gcp_credentials)
    bucket = gcs_client.get_bucket(settings.gcs_bucket_name)

    upload_fn = sync_directory_to_gcs if sync else upload_directory_to_gcs
    upload_fn(
        bucket=bucket,
        directory=directory,
        gcs_folder_name=settings.gcs_input_folder_path,
    )


def run_data_load(settings: KGSettings, timeout: int = 6000):
    """Run the data load job.

    Args:
        settings (KGSettings): The settings for the Knowledge Graph.
        timeout (int): The timeout for the job. Default is 6000 seconds.
    """
    jobs_client = get_jobs_client(credentials=settings.gcp_credentials)
    run_data_load_job(settings=settings, client=jobs_client, timeout=timeout)


def redeploy_service(settings: KGSettings, timeout: int = 600):
    """Redeploy the Data Commons service.

    Args:
        settings (KGSettings): The settings for the Knowledge Graph.
        timeout (int): The timeout for the service. Default is 600 seconds.

    """
    services_client = get_services_client(credentials=settings.gcp_credentials)
    redeploy_cloud_run_service(
        settings=settings, client=services_client, timeout=timeout
    )
