from pathlib import Path
from unittest.mock import patch

import pytest

from dcp_tools.gcp_utilities import KGSettings
from dcp_tools.gcp_utilities.jobs import run_data_load_job

TEST_SETTINGS = KGSettings(
    LOCAL_PATH=Path("/tmp/data"),
    GCP_PROJECT_ID="test_proj",
    GCS_BUCKET_NAME="test_bucket",
    GCS_INPUT_FOLDER_PATH="ingestion/input/",
    GCS_OUTPUT_FOLDER_PATH="/output/path/",
    LOAD_JOB_NAME="test_job",
    LOAD_JOB_REGION="test_region",
    LOAD_JOB_SERVICE_ACCOUNT="test@example.com",
)


def test_run_data_load_job() -> None:
    with patch("dcp_tools.gcp_utilities.jobs.IngestionJobClient") as patch_client:
        run_data_load_job(TEST_SETTINGS, imports="test_import_a,test_import_b")

        patch_client.assert_called_once_with(
            job_name="test_job",
            service_account_email="test@example.com",
            project_id="test_proj",
            location="test_region",
        )
        patch_client.return_value.start_job.assert_called_once_with(
            imports="test_import_a,test_import_b"
        )


def test_run_data_load_job_no_imports() -> None:
    with patch("dcp_tools.gcp_utilities.jobs.IngestionJobClient") as patch_client:
        run_data_load_job(TEST_SETTINGS)

        patch_client.assert_called_once_with(
            job_name="test_job",
            service_account_email="test@example.com",
            project_id="test_proj",
            location="test_region",
        )
        patch_client.return_value.start_job.assert_called_once_with(
            imports="ALL_IMPORTS"
        )


def test_run_data_load_job_wraps_errors() -> None:
    with patch("dcp_tools.gcp_utilities.jobs.IngestionJobClient") as patch_client:
        original_exception = Exception("Test exception")
        patch_client.return_value.start_job.side_effect = original_exception
        with pytest.raises(RuntimeError, match="Test exception") as exc_info:
            run_data_load_job(TEST_SETTINGS)
        assert exc_info.value.__cause__ == original_exception
