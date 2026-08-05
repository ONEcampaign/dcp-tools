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
    INGESTION_WORKFLOW_NAME="test_workflow",
    LOAD_JOB_REGION="test_region",
    LOAD_JOB_SERVICE_ACCOUNT="test@example.com",
)


def test_run_data_load_job() -> None:
    with patch("dcp_tools.gcp_utilities.jobs.IngestionJobClient") as patch_client:
        run_data_load_job(TEST_SETTINGS, imports="test_import_a,test_import_b")

        patch_client.assert_called_once_with(
            job_name="test_job",
            workflow_name="test_workflow",
            service_account_email="test@example.com",
            project_id="test_proj",
            location="test_region",
        )
        patch_client.return_value.start_workflow.assert_called_once_with(
            imports="test_import_a,test_import_b"
        )


def test_run_data_load_job_no_imports() -> None:
    with patch("dcp_tools.gcp_utilities.jobs.IngestionJobClient") as patch_client:
        run_data_load_job(TEST_SETTINGS)

        patch_client.assert_called_once_with(
            job_name="test_job",
            workflow_name="test_workflow",
            service_account_email="test@example.com",
            project_id="test_proj",
            location="test_region",
        )
        patch_client.return_value.start_workflow.assert_called_once_with(
            imports="ALL_IMPORTS"
        )


def test_run_data_ingestion_workflow_warns_when_execution_id_missing() -> None:
    """A response with no 'name' key logs a warning instead of raising."""
    with (
        patch("dcp_tools.gcp_utilities.jobs.IngestionJobClient") as patch_client,
        patch("dcp_tools.gcp_utilities.jobs.logger") as mock_logger,
    ):
        patch_client.return_value.start_workflow.return_value = {}
        run_data_load_job(TEST_SETTINGS)
        mock_logger.warning.assert_called_once_with(
            "Failed to retrieve workflow execution id"
        )


def test_run_data_load_job_wraps_errors() -> None:
    with patch("dcp_tools.gcp_utilities.jobs.IngestionJobClient") as patch_client:
        original_exception = Exception("Test exception")
        patch_client.return_value.start_workflow.side_effect = original_exception
        with pytest.raises(RuntimeError, match="Test exception") as exc_info:
            run_data_load_job(TEST_SETTINGS)
        assert exc_info.value.__cause__ == original_exception
