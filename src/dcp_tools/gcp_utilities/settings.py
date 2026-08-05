"""
Module for Knowledge Graph pipeline settings.
"""

import json
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
        gcp_credentials: GCP credentials in JSON format. Optional; if not provided,
            Application Default Credentials (ADC) will be used.
        gcs_bucket_name: Google Cloud Storage bucket name.
        gcs_input_folder_path: Google Cloud Storage input folder path.
        gcs_output_folder_path: Google Cloud Storage output folder path.
        load_job_region: Cloud Run load job region.
        load_job_name: Cloud Run load job name.
        load_job_service_account: Cloud Run service account email to impersonate, optional.
    """

    local_path: Path = Field(alias="LOCAL_PATH")
    gcp_project_id: str = Field(alias="GCP_PROJECT_ID")
    gcp_credentials: Json[dict] | None = Field(default=None, alias="GCP_CREDENTIALS")

    # Cloud storage
    gcs_bucket_name: str = Field(alias="GCS_BUCKET_NAME")
    gcs_input_folder_path: str = Field(alias="GCS_INPUT_FOLDER_PATH")
    gcs_output_folder_path: str = Field(alias="GCS_OUTPUT_FOLDER_PATH")

    # Cloud run
    load_job_region: str = Field(alias="LOAD_JOB_REGION")
    load_job_name: str = Field(alias="LOAD_JOB_NAME")
    ingestion_workflow_name: str = Field(alias="INGESTION_WORKFLOW_NAME")
    load_job_service_account: str | None = Field(
        alias="LOAD_JOB_SERVICE_ACCOUNT", default=None
    )

    @field_validator("gcs_input_folder_path", "gcs_output_folder_path")
    @classmethod
    def _strip_slashes(cls, v: str) -> str:
        return v.strip("/")

    @property
    def full_gcs_input_path(self) -> str:
        """Get the full GCS path for data."""
        return f"gs://{self.gcs_bucket_name}/{self.gcs_input_folder_path}"

    @property
    def full_gcs_output_path(self) -> str:
        """Get the full GCS path for data."""
        return f"gs://{self.gcs_bucket_name}/{self.gcs_output_folder_path}"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )


def get_kg_settings(
    *,
    source: Literal["env", "json"] = "env",
    env_file: PathLike | Path | None = None,
    file: str | Path | None = None,
) -> KGSettings:
    """Return an instance of KGSettings.

    Settings are the key configuration values needed to run the pipeline. They include
    information about the GCP project, the GCS bucket, and the Cloud Run job.

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
