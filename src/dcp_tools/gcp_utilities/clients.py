from collections.abc import Callable
from typing import Any

from google.cloud.run_v2 import JobsClient, ServicesClient
from google.cloud.storage import Client


def _build_client[ClientType](
    client_cls: type[ClientType], credentials: dict | None
) -> ClientType:
    if credentials and isinstance(credentials, dict):
        factory: Callable[..., Any] | None = getattr(
            client_cls, "from_service_account_info", None
        )
        if factory is not None:
            return factory(credentials)
        return client_cls(credentials=credentials)
    # Fall back to Application Default Credentials
    return client_cls()


def get_gcs_client(credentials: dict | None) -> Client:
    """Initialize the Google Cloud Storage client."""
    return _build_client(Client, credentials=credentials)


def get_jobs_client(credentials: dict | None) -> JobsClient:
    """Initialize the Google Cloud Run Jobs client."""
    return _build_client(JobsClient, credentials=credentials)


def get_services_client(credentials: dict | None) -> ServicesClient:
    """Initialize the Google Cloud Run Services client."""
    return _build_client(ServicesClient, credentials=credentials)
