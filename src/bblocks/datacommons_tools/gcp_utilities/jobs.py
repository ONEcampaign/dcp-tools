"""This module contains functions to run a Cloud Run job and redeploy a Cloud Run service."""

from datetime import datetime, timezone

from google.cloud.run_v2 import (
    Container,
    EnvVar,
    JobsClient,
    ServicesClient,
    RunJobRequest,
    UpdateServiceRequest,
)

from bblocks.datacommons_tools.gcp_utilities.settings import KGSettings
from bblocks.datacommons_tools.logger import logger


def _utc_timestamp() -> str:
    """Return an ISO‑8601 timestamp in UTC"""
    return datetime.now(tz=timezone.utc).isoformat()


def _build_env_vars(settings: KGSettings) -> list[EnvVar]:
    """Prepare the environment variables for Cloud Run tasks."""
    return [
        EnvVar({"name": "TIMESTAMP", "value": _utc_timestamp()}),
        EnvVar({"name": "DB_NAME", "value": settings.cloud_sql_db_name}),
    ]


def _override_env_vars(settings: KGSettings, container: Container) -> Container:
    """Override the environment variables in the Cloud Run container."""

    existing: dict[str, str] = {v.name: v.value for v in container.env}

    for var in _build_env_vars(settings=settings):
        current_val = existing.get(var.name)
        if current_val and current_val == var.value:
            logger.info(f"Skipping local environment variable: {var.name}")
            continue

        container.env = [v for v in container.env if v.name != var.name]
        container.env.append(var)

    return container


def run_data_load_job(
    settings: KGSettings, client: JobsClient, *, timeout: int = 6000
) -> None:
    """Trigger a Cloud Run job to load data.

    Args:
        settings (KGSettings): Settings for the job.
        client (JobsClient): Cloud Run Jobs client.
        timeout (int): Timeout for the job. Default is 6000 seconds.

    """

    # Create the required overrides for the job
    overrides = [
        RunJobRequest.Overrides.ContainerOverride(
            {"env": _build_env_vars(settings=settings)}
        )
    ]

    # Create the request to run the job
    request = RunJobRequest(
        {
            "name": settings.load_job_path,
            "etag": "*",
            "validate_only": False,
            "overrides": RunJobRequest.Overrides(
                {"task_count": 1, "container_overrides": overrides}
            ),
        }
    )

    # Start the job
    operation = client.run_job(request=request, timeout=timeout)
    logger.info(f"Started job {request.name}....")

    # Wait for the job to complete
    response = operation.result(timeout=timeout)
    logger.info(f"Job {request.name} completed with response: {response.name}")


def redeploy_cloud_run_service(
    settings: KGSettings, client: ServicesClient, *, timeout: int = 300
) -> None:
    """Deploy the Cloud Run service

    Args:
        settings (KGSettings): Settings for the service.
        client (ServicesClient): Cloud Run Services client.
        timeout (int): Timeout for the service. Default is 300 seconds.

    """

    service = client.get_service(name=settings.dc_service_path)
    container = service.template.containers[0]

    # Replace the environment variables in the container.
    service.template.containers = [
        _override_env_vars(settings=settings, container=container)
    ]

    # Create the request to update the service
    request = UpdateServiceRequest(
        {"service": service, "validate_only": False, "allow_missing": False}
    )

    # Start the update operation
    operation = client.update_service(request=request)
    logger.info("Started service update....")

    # Wait for the update to complete
    response = operation.result(timeout=timeout)
    logger.info(f"Service update completed with response: {response}")
