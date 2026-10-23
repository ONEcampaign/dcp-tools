"""
Module for Knowledge Graph pipeline settings.
"""

import json
import warnings
from os import PathLike
from pathlib import Path
from typing import Literal

from pydantic import Field, Json, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class KGSettings(BaseSettings):
    """Configuration constants for the project.

    Attributes:
        local_path: Path to the local directory that will be exported.
        gcp_project_id: GCP project ID.
        gcp_region: GCP region the ingestion resources live in.
        gcp_credentials: GCP credentials in JSON format. Optional; if not provided,
            Application Default Credentials (ADC) will be used.
        gcs_bucket_name: Google Cloud Storage bucket name.
        gcs_input_folder_path: Google Cloud Storage input folder path. Defaults to
            "ingestion/input", the DCP Terraform default.
        gcs_output_folder_path: Google Cloud Storage output folder path.
        ingestion_workflow_name: Name of the Cloud Workflow that runs ingestion.
        ingestion_service_account: Service account email to impersonate when triggering
            ingestion, optional.
        ingestion_prep_job_name: Deprecated and ignored, to be removed in 2.0. The
            ingestion workflow creates its own preprocessing job.
    """

    local_path: Path = Field(validation_alias="LOCAL_PATH")
    gcp_project_id: str = Field(validation_alias="GCP_PROJECT_ID")
    gcp_region: str = Field(validation_alias="GCP_REGION")
    gcp_credentials: Json[dict] | None = Field(
        default=None, validation_alias="GCP_CREDENTIALS"
    )

    # Cloud storage
    gcs_bucket_name: str = Field(validation_alias="GCS_BUCKET_NAME")
    gcs_input_folder_path: str = Field(
        default="ingestion/input", validation_alias="GCS_INPUT_FOLDER_PATH"
    )
    gcs_output_folder_path: str = Field(validation_alias="GCS_OUTPUT_FOLDER_PATH")

    # Ingestion
    ingestion_workflow_name: str = Field(validation_alias="INGESTION_WORKFLOW_NAME")
    ingestion_service_account: str | None = Field(
        validation_alias="INGESTION_SERVICE_ACCOUNT", default=None
    )
    ingestion_prep_job_name: str | None = Field(
        default=None, validation_alias="INGESTION_PREP_JOB_NAME"
    )

    @field_validator("gcs_input_folder_path", "gcs_output_folder_path")
    @classmethod
    def _strip_slashes(cls, v: str) -> str:
        return v.strip("/")

    @field_validator("ingestion_prep_job_name")
    @classmethod
    def _warn_prep_job_name(cls, v: str | None) -> str | None:
        if v is not None:
            warnings.warn(
                "INGESTION_PREP_JOB_NAME is deprecated, ignored, and will be removed "
                "in 2.0. The ingestion workflow creates its own preprocessing job.",
                DeprecationWarning,
                stacklevel=2,
            )
        return v

    @property
    def full_gcs_input_path(self) -> str:
        """Get the full GCS path for data."""
        return f"gs://{self.gcs_bucket_name}/{self.gcs_input_folder_path}"

    @property
    def full_gcs_output_path(self) -> str:
        """Get the full GCS path for data."""
        return f"gs://{self.gcs_bucket_name}/{self.gcs_output_folder_path}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,
    )


def get_kg_settings(
    *,
    source: Literal["env", "json"] = "env",
    env_file: PathLike | Path | None = None,
    file: str | Path | None = None,
) -> KGSettings:
    """Return an instance of KGSettings.

    Settings are the key configuration values needed to run the pipeline. They include
    information about the GCP project, the GCS bucket, and the ingestion resources.

    Args:
        source (str): Source of the settings. Can be "env" or "json".
        env_file (str | Path, optional): Path to the .env file. Defaults to None.
            Only used if source is "env".
        file (str | Path, optional): Path to the JSON file. Defaults to None.
            Only used if source is "json".

    """
    if source == "env":
        config_kwargs = {"_env_file": env_file} if env_file else {}
        return KGSettings(**config_kwargs)

    if source == "json":
        if file is None:
            raise ValueError("File path must be provided when source is 'json'.")
        raw = json.loads(Path(file).read_text())
        return KGSettings.model_validate(raw, from_attributes=False)

    raise ValueError("Invalid source. Must be 'env' or 'json'.")
