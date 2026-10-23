"""This module contains functions to run the data ingestion workflow."""

import logging

from datacommons_admin.core.clients import IngestionJobClient

from dcp_tools.gcp_utilities.settings import KGSettings

logger = logging.getLogger(__name__)


def run_ingestion_workflow(settings: KGSettings, *, imports: str | None = None) -> None:
    """Trigger the ingestion workflow to load data into the knowledge graph.

    Args:
        settings (KGSettings): Settings for the workflow.
        imports (str | None): Comma-separated list of imports to ingest. All imports are ingested if omitted.
    """
    logger.info(
        f"Starting data ingestion workflow '{settings.ingestion_workflow_name}'"
    )
    try:
        client = IngestionJobClient(
            workflow_name=settings.ingestion_workflow_name,
            service_account_email=settings.ingestion_service_account,
            project_id=settings.gcp_project_id,
            location=settings.gcp_region,
        )
        result = client.start_workflow(imports=imports or "ALL_IMPORTS")
        workflow_execution_id = result.get("name")
        if workflow_execution_id:
            logger.info(f"Started workflow execution '{workflow_execution_id}'")
        else:
            logger.warning("Failed to retrieve workflow execution id")
    except Exception as e:
        raise RuntimeError(f"Failed to start ingestion workflow: {e}") from e
