"""This module contains functions to run the data ingestion workflow."""

from datacommons_admin.ingestion_job_client import IngestionJobClient

from dcp_tools.gcp_utilities.settings import KGSettings
from dcp_tools.logger import logger


def run_data_load_job(
    settings: KGSettings, *, imports: str | None = "ALL_IMPORTS"
) -> None:
    """Trigger the ingestion workflow to load data into the knowledge graph.

    Args:
        settings (KGSettings): Settings for the workflow.
        imports (str | None): Comma-separated list of imports to load. Defaults to "ALL_IMPORTS".
    """
    logger.info(
        f"Starting data ingestion workflow '{settings.ingestion_workflow_name}'"
    )
    try:
        client = IngestionJobClient(
            job_name=settings.load_job_name,
            workflow_name=settings.ingestion_workflow_name,
            # datacommons-admin annotates service_account_email as `str` but defaults it
            # to None and handles None at runtime; the annotation should be `str | None`.
            service_account_email=settings.load_job_service_account,  # ty: ignore[invalid-argument-type]
            project_id=settings.gcp_project_id,
            location=settings.load_job_region,
        )
        result = client.start_workflow(imports=imports)
        workflow_execution_id = result.get("name")
        if workflow_execution_id:
            logger.info(f"Started workflow execution '{workflow_execution_id}'")
        else:
            logger.warning("Failed to retrieve workflow execution id")
    except Exception as e:
        raise RuntimeError(f"Failed to start data load job: {e}") from e
