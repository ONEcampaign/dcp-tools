from collections.abc import Callable
from typing import Any

from google.cloud.storage import Client


def _build_client[ClientType](
    client_cls: type[ClientType], credentials: dict | None, project: str | None = None
) -> ClientType:
    if credentials and isinstance(credentials, dict):
        factory: Callable[..., Any] | None = getattr(
            client_cls, "from_service_account_info", None
        )
        if factory is not None:
            return factory(credentials)
        return client_cls(credentials=credentials)
    # Fall back to Application Default Credentials. An explicit `project=None` stops
    # the client inferring a project from the environment, so omit it instead.
    if project is None:
        return client_cls()
    return client_cls(project=project)


def get_gcs_client(credentials: dict | None, *, project: str | None = None) -> Client:
    """Initialize the Google Cloud Storage client.

    Args:
        credentials (dict | None): Service account info. If None, Application Default
            Credentials are used.
        project (str | None): GCP project for the client under Application Default
            Credentials. Service account credentials use the project in the key.
    """
    return _build_client(Client, credentials=credentials, project=project)
