from pathlib import Path
from unittest.mock import patch

import pytest

from dcp_tools.gcp_utilities import KGSettings
from dcp_tools.gcp_utilities.ingestion import run_ingestion_workflow

TEST_SETTINGS = KGSettings(
    local_path=Path("/tmp/data"),
    gcp_project_id="test_proj",
    gcp_region="test_region",
    gcs_bucket_name="test_bucket",
    gcs_input_folder_path="ingestion/input/",
    gcs_output_folder_path="/output/path/",
    ingestion_prep_job_name="test_prep_job",
    ingestion_workflow_name="test_workflow",
    ingestion_service_account="test@example.com",
)


def test_run_ingestion_workflow() -> None:
    with patch("dcp_tools.gcp_utilities.ingestion.IngestionJobClient") as patch_client:
        run_ingestion_workflow(TEST_SETTINGS, imports="test_import_a,test_import_b")

        patch_client.assert_called_once_with(
            job_name="test_prep_job",
            workflow_name="test_workflow",
            service_account_email="test@example.com",
            project_id="test_proj",
            location="test_region",
        )
        patch_client.return_value.start_workflow.assert_called_once_with(
            imports="test_import_a,test_import_b"
        )


def test_run_ingestion_workflow_no_imports() -> None:
    with patch("dcp_tools.gcp_utilities.ingestion.IngestionJobClient") as patch_client:
        run_ingestion_workflow(TEST_SETTINGS)

        patch_client.assert_called_once_with(
            job_name="test_prep_job",
            workflow_name="test_workflow",
            service_account_email="test@example.com",
            project_id="test_proj",
            location="test_region",
        )
        patch_client.return_value.start_workflow.assert_called_once_with(
            imports="ALL_IMPORTS"
        )


def test_run_ingestion_workflow_warns_when_execution_id_missing() -> None:
    """A response with no 'name' key logs a warning instead of raising."""
    with (
        patch("dcp_tools.gcp_utilities.ingestion.IngestionJobClient") as patch_client,
        patch("dcp_tools.gcp_utilities.ingestion.logger") as mock_logger,
    ):
        patch_client.return_value.start_workflow.return_value = {}
        run_ingestion_workflow(TEST_SETTINGS)
        mock_logger.warning.assert_called_once_with(
            "Failed to retrieve workflow execution id"
        )


def test_run_ingestion_workflow_wraps_errors() -> None:
    with patch("dcp_tools.gcp_utilities.ingestion.IngestionJobClient") as patch_client:
        original_exception = Exception("Test exception")
        patch_client.return_value.start_workflow.side_effect = original_exception
        with pytest.raises(RuntimeError, match="Test exception") as exc_info:
            run_ingestion_workflow(TEST_SETTINGS)
        assert exc_info.value.__cause__ == original_exception
