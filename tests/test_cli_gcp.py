import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock, create_autospec, patch

import pytest
from google.auth.transport.requests import AuthorizedSession
from requests import Response

from dcp_tools.cli import main
from dcp_tools.gcp_utilities.clients import _build_client
from dcp_tools.gcp_utilities.ingestion import (
    DEFAULT_POLL_INTERVAL,
    IngestionExecutionState,
    WorkflowContractError,
)
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


@pytest.mark.parametrize(
    ("flags", "imports", "skip_check"),
    [
        ([], None, False),
        (["--imports", "test_import"], "test_import", False),
        (["--skip-workflow-contract-check"], None, True),
    ],
)
def test_ingest_command_invokes_workflow(
    flags: list[str], imports: str | None, skip_check: bool
) -> None:
    with (
        patch("dcp_tools.cli.common.get_kg_settings") as get,
        patch("dcp_tools.cli.ingest.run_ingestion_workflow") as run,
    ):
        get.return_value = Mock()
        exit_code = main(["ingest", "--env-file", "e", *flags])
        assert exit_code == 0
        get.assert_called_once_with(env_file=Path("e"))
        run.assert_called_once_with(
            settings=get.return_value,
            imports=imports,
            skip_workflow_contract_check=skip_check,
        )


@pytest.mark.parametrize(
    ("flags", "skip_check"), [([], False), (["--skip-workflow-contract-check"], True)]
)
def test_pipeline_command_runs_all(
    tmp_path: Path, flags: list[str], skip_check: bool
) -> None:
    directory = tmp_path / "data"
    with (
        patch("dcp_tools.cli.common.get_kg_settings") as get,
        patch("dcp_tools.cli.pipeline.check_ingestion_workflow_contract") as check,
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
                *flags,
            ]
        )
        assert exit_code == 0
        get.assert_called_once_with(source="json", file=Path("s.json"))
        upload.assert_called_once_with(
            settings=get.return_value, directory=directory, sync=False
        )
        assert check.call_count == (0 if skip_check else 1)
        load.assert_called_once_with(
            settings=get.return_value, skip_workflow_contract_check=True
        )


def test_pipeline_command_refuses_older_stack_before_upload(tmp_path: Path) -> None:
    source = "call: googleapis.run.v2.projects.locations.jobs.run"
    response = Response()
    response.status_code = 200
    response._content = json.dumps({"sourceContents": source}).encode()
    with (
        patch("dcp_tools.cli.common.get_kg_settings") as get,
        patch(
            "dcp_tools.gcp_utilities.ingestion.IngestionJobClient", autospec=True
        ) as client_class,
        patch("dcp_tools.cli.pipeline.upload_to_cloud_storage") as upload,
    ):
        get.return_value = Mock()
        client = client_class.return_value
        client.full_workflow_name = "projects/p/locations/r/workflows/w"
        client.session = create_autospec(AuthorizedSession, instance=True)
        client.session.get.return_value = response

        with pytest.raises(WorkflowContractError):
            main(["pipeline", "--env-file", "e", "--directory", str(tmp_path)])

        upload.assert_not_called()
        client.start_workflow.assert_not_called()


EXECUTION = "projects/p/locations/r/workflows/w/executions/abc-123"
INGESTION_COMMANDS = [
    pytest.param(["ingest", "--env-file", "e"], "ingest", id="ingest"),
    pytest.param(
        ["pipeline", "--env-file", "e", "--skip-workflow-contract-check"],
        "pipeline",
        id="pipeline",
    ),
]


@contextmanager
def ingestion_command_mocks(module: str) -> Iterator[dict[str, Mock]]:
    """Patch settings, upload and workflow start, and the wait the CLI calls."""
    with (
        patch("dcp_tools.cli.common.get_kg_settings") as get,
        patch("dcp_tools.cli.pipeline.upload_to_cloud_storage") as upload,
        patch(f"dcp_tools.cli.{module}.run_ingestion_workflow") as start,
        patch("dcp_tools.cli.common.wait_for_ingestion") as wait,
    ):
        start.return_value = EXECUTION
        yield {"get": get, "upload": upload, "start": start, "wait": wait}


@pytest.mark.parametrize(("command", "module"), INGESTION_COMMANDS)
@pytest.mark.parametrize(
    ("state", "error", "expected_exit_code"),
    [
        ("SUCCEEDED", None, 0),
        ("FAILED", "Dataflow job failed", 1),
        ("CANCELLED", None, 1),
    ],
)
def test_wait_exit_code_follows_terminal_state(
    command: list[str],
    module: str,
    state: str,
    error: str | None,
    expected_exit_code: int,
) -> None:
    with ingestion_command_mocks(module) as mocks:
        mocks["wait"].return_value = IngestionExecutionState(
            state=state, current_steps=(), error=error
        )

        exit_code = main([*command, "--wait"])

    assert exit_code == expected_exit_code
    mocks["wait"].assert_called_once_with(
        mocks["get"].return_value,
        EXECUTION,
        timeout=None,
        poll_interval=DEFAULT_POLL_INTERVAL,
    )


@pytest.mark.parametrize(("command", "module"), INGESTION_COMMANDS)
def test_wait_passes_timeout_and_poll_interval(command: list[str], module: str) -> None:
    with ingestion_command_mocks(module) as mocks:
        mocks["wait"].return_value = IngestionExecutionState(
            state="SUCCEEDED", current_steps=(), error=None
        )

        main([*command, "--wait", "--timeout", "600", "--poll-interval", "5"])

    mocks["wait"].assert_called_once_with(
        mocks["get"].return_value, EXECUTION, timeout=600, poll_interval=5
    )


@pytest.mark.parametrize(("command", "module"), INGESTION_COMMANDS)
def test_wait_timeout_exits_non_zero(command: list[str], module: str) -> None:
    with ingestion_command_mocks(module) as mocks:
        mocks["wait"].side_effect = TimeoutError("still ACTIVE")

        exit_code = main([*command, "--wait", "--timeout", "1"])

    assert exit_code != 0


@pytest.mark.parametrize(("command", "module"), INGESTION_COMMANDS)
def test_without_wait_does_not_poll(command: list[str], module: str) -> None:
    with ingestion_command_mocks(module) as mocks:
        exit_code = main(command)

    assert exit_code == 0
    mocks["wait"].assert_not_called()


@pytest.mark.parametrize(("command", "module"), INGESTION_COMMANDS)
@pytest.mark.parametrize(
    ("flags", "message"),
    [
        (["--timeout", "60"], "--timeout requires --wait"),
        (["--poll-interval", "5"], "--poll-interval requires --wait"),
        (["--wait", "--timeout", "-1"], "argument --timeout: must not be negative"),
        (
            ["--wait", "--poll-interval", "0"],
            "argument --poll-interval: must be positive",
        ),
        (
            ["--wait", "--timeout", "nan"],
            "argument --timeout: must be a finite number of seconds",
        ),
        (
            ["--wait", "--timeout", "inf"],
            "argument --timeout: must be a finite number of seconds",
        ),
        (
            ["--wait", "--poll-interval", "nan"],
            "argument --poll-interval: must be a finite number of seconds",
        ),
        (
            ["--wait", "--poll-interval", "inf"],
            "argument --poll-interval: must be a finite number of seconds",
        ),
    ],
)
def test_wait_options_are_rejected_before_any_work(
    command: list[str],
    module: str,
    flags: list[str],
    message: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with (
        ingestion_command_mocks(module) as mocks,
        pytest.raises(SystemExit) as exit_info,
    ):
        main([*command, *flags])

    assert exit_info.value.code == 2
    assert message in capsys.readouterr().err
    mocks["get"].assert_not_called()
    mocks["upload"].assert_not_called()
    mocks["start"].assert_not_called()


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
