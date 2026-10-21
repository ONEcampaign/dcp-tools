from pathlib import Path
from unittest.mock import Mock, patch

from dcp_tools.cli import main
from dcp_tools.gcp_utilities.clients import _build_client
from dcp_tools.gcp_utilities.pipeline import upload_to_cloud_storage


def test_upload_command_invokes_pipeline(tmp_path: Path) -> None:
    directory = tmp_path / "data"
    directory.mkdir()
    with (
        patch("dcp_tools.cli.common.get_kg_settings") as get,
        patch("dcp_tools.cli.upload.upload_to_cloud_storage") as upload,
    ):
        get.return_value = Mock()
        exit_code = main(
            ["upload", "--settings-file", "s.json", "--directory", str(directory)]
        )
        assert exit_code == 0
        get.assert_called_once_with(source="json", file=Path("s.json"))
        upload.assert_called_once_with(
            settings=get.return_value, directory=directory, sync=False
        )


def test_ingest_command_invokes_workflow() -> None:
    with (
        patch("dcp_tools.cli.common.get_kg_settings") as get,
        patch("dcp_tools.cli.ingest.run_ingestion_workflow") as run,
    ):
        get.return_value = Mock()
        exit_code = main(["ingest", "--env-file", "e"])
        assert exit_code == 0
        get.assert_called_once_with(env_file=Path("e"))
        run.assert_called_once_with(settings=get.return_value, imports=None)


def test_ingest_command_defaults_to_all_imports() -> None:
    with (
        patch("dcp_tools.cli.common.get_kg_settings") as get,
        patch("dcp_tools.gcp_utilities.ingestion.IngestionJobClient") as client,
    ):
        get.return_value = Mock()
        exit_code = main(["ingest", "--env-file", "e"])
        assert exit_code == 0
        client.return_value.start_workflow.assert_called_once_with(
            imports="ALL_IMPORTS"
        )


def test_ingest_command_invokes_workflow_with_named_imports() -> None:
    with (
        patch("dcp_tools.cli.common.get_kg_settings") as get,
        patch("dcp_tools.cli.ingest.run_ingestion_workflow") as run,
    ):
        get.return_value = Mock()
        exit_code = main(["ingest", "--env-file", "e", "--imports", "test_import"])
        assert exit_code == 0
        get.assert_called_once_with(env_file=Path("e"))
        run.assert_called_once_with(settings=get.return_value, imports="test_import")


def test_pipeline_command_runs_all(tmp_path: Path) -> None:
    directory = tmp_path / "data"
    with (
        patch("dcp_tools.cli.common.get_kg_settings") as get,
        patch("dcp_tools.cli.pipeline.upload_to_cloud_storage") as upload,
        patch("dcp_tools.cli.pipeline.run_ingestion_workflow") as load,
    ):
        get.return_value = Mock()
        exit_code = main(
            [
                "pipeline",
                "--settings-file",
                "s.json",
                "--directory",
                str(directory),
            ]
        )
        assert exit_code == 0
        get.assert_called_once_with(source="json", file=Path("s.json"))
        upload.assert_called_once_with(
            settings=get.return_value, directory=directory, sync=False
        )
        load.assert_called_once_with(settings=get.return_value)


def test_build_client_with_credentials_uses_service_account_info() -> None:
    """When credentials dict is provided, use from_service_account_info."""
    mock_cls = Mock()
    mock_cls.from_service_account_info.return_value = Mock()
    creds = {"type": "service_account", "project_id": "test"}

    result = _build_client(mock_cls, credentials=creds)

    mock_cls.from_service_account_info.assert_called_once_with(creds)
    assert result == mock_cls.from_service_account_info.return_value


def test_build_client_without_credentials_uses_adc() -> None:
    """When credentials is None, fall back to ADC (no-arg constructor)."""
    mock_cls = Mock()
    mock_cls.return_value = Mock()

    result = _build_client(mock_cls, credentials=None)

    mock_cls.assert_called_once_with()
    assert result == mock_cls.return_value
    mock_cls.from_service_account_info.assert_not_called()


def test_build_client_without_credentials_passes_project_to_adc() -> None:
    mock_cls = Mock()

    result = _build_client(mock_cls, credentials=None, project="proj")

    mock_cls.assert_called_once_with(project="proj")
    assert result == mock_cls.return_value


def test_upload_to_cloud_storage_passes_project_id_under_adc(tmp_path: Path) -> None:
    settings = Mock(gcp_credentials=None, gcp_project_id="proj")
    with (
        patch("dcp_tools.gcp_utilities.clients.Client") as client_cls,
        patch("dcp_tools.gcp_utilities.pipeline.upload_directory_to_gcs") as upload,
    ):
        upload_to_cloud_storage(settings=settings, directory=tmp_path)

    client_cls.assert_called_once_with(project="proj")
    upload.assert_called_once_with(
        bucket=client_cls.return_value.get_bucket.return_value,
        directory=tmp_path,
        gcs_folder_name=settings.gcs_input_folder_path,
    )
