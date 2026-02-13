"""
Module for Knowledge Graph pipeline settings.
"""

import json
from os import PathLike
from pathlib import Path
from typing import Literal, overload

from pydantic import Field, Json
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_IMAGE = "gcr.io/datcom-ci/datacommons-services:latest"


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
        cloud_sql_db_name: Cloud SQL database name.
        cloud_sql_region: Cloud SQL region.
        cloud_job_region: Cloud job region.
        cloud_service_region: Cloud service region.
        cloud_run_job_name: Cloud Run job name.
        cloud_run_service_name: Cloud Run service name.

    """

    local_path: Path = Field(alias="LOCAL_PATH")
    gcp_project_id: str = Field(alias="GCP_PROJECT_ID")
    gcp_credentials: Json[dict] | None = Field(default=None, alias="GCP_CREDENTIALS")

    # cloud storage
    gcs_bucket_name: str = Field(alias="GCS_BUCKET_NAME")
    gcs_input_folder_path: str = Field(alias="GCS_INPUT_FOLDER_PATH")
    gcs_output_folder_path: str = Field(alias="GCS_OUTPUT_FOLDER_PATH")
    # Cloud sql
    cloud_sql_db_name: str = Field(alias="CLOUD_SQL_DB_NAME")
    cloud_sql_region: str = Field(alias="CLOUD_SQL_REGION")
    # Cloud job
    cloud_job_region: str = Field(alias="CLOUD_JOB_REGION")
    cloud_service_region: str = Field(alias="CLOUD_SERVICE_REGION")
    # Cloud run
    cloud_run_job_name: str = Field(alias="CLOUD_RUN_JOB_NAME")
    cloud_run_service_name: str = Field(alias="CLOUD_RUN_SERVICE_NAME")

    datacommons_service_image: str = Field(
        default=_DEFAULT_IMAGE, alias="DATACOMMONS_SERVICE_IMAGE"
    )

    @property
    def full_gcs_input_path(self) -> str:
        """Get the full GCS path for data."""
        return f"gs://{self.gcs_bucket_name}/{self.gcs_input_folder_path}"

    @property
    def full_gcs_output_path(self) -> str:
        """Get the full GCS path for data."""
        return f"gs://{self.gcs_bucket_name}/{self.gcs_output_folder_path}"

    @property
    def load_job_path(self) -> str:
        """Get the path to the load job."""
        return (
            f"projects/{self.gcp_project_id}/locations/"
            f"{self.cloud_job_region}/jobs/{self.cloud_run_job_name}"
        )

    @property
    def dc_service_path(self) -> str:
        """Get the path to the Data Commons service."""
        return (
            f"projects/{self.gcp_project_id}/locations/{self.cloud_service_region}/"
            f"services/{self.cloud_run_service_name}"
        )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )


@overload
def get_kg_settings(
    *, source: Literal["env"] = "env", env_file: str | Path | None = None
) -> KGSettings: ...


@overload
def get_kg_settings(
    *, source: Literal["json"] = "json", file: str | Path
) -> KGSettings: ...


def get_kg_settings(
    *,
    source: Literal["env", "json"] = "env",
    env_file: PathLike | Path | None = None,
    file: str | Path | None = None,
) -> KGSettings:
    """Return an instance of KGSettings.

    Settings are the key configuration values needed to run the pipeline. They include
    information about the GCP project, the GCS bucket, the Cloud SQL database, and the Cloud Run job.

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
