"""This module contains functions to run the Cloud Run data load job."""

from datacommons_admin.ingestion_job_client import IngestionJobClient

from dcp_tools.gcp_utilities.settings import KGSettings
from dcp_tools.logger import logger


def run_data_load_job(settings: KGSettings, *, imports: str | None = None) -> None:
    """Trigger a Cloud Run job to load data.

    Args:
        settings (KGSettings): Settings for the job.
        imports (str | None): Comma-separated list of imports to load. Default is None, which loads all imports.
    """
    logger.info(f"Starting data load job '{settings.load_job_name}'")
    try:
        client = IngestionJobClient(
            job_name=settings.load_job_name,
            # datacommons-admin annotates service_account_email as `str` but defaults it
            # to None and handles None at runtime; the annotation should be `str | None`.
            service_account_email=settings.load_job_service_account,  # ty: ignore[invalid-argument-type]
            project_id=settings.gcp_project_id,
            location=settings.load_job_region,
        )
        client.start_job(imports=imports)
        logger.info(f"Started job '{client.full_job_name}'")
    except Exception as e:
        raise RuntimeError(f"Failed to start data load job: {e}") from e
