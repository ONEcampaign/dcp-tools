import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, create_autospec, patch

import pytest
from google.auth.transport.requests import AuthorizedSession
from requests import Response

from dcp_tools.gcp_utilities import KGSettings
from dcp_tools.gcp_utilities.ingestion import (
    DEFAULT_POLL_INTERVAL,
    TERMINAL_EXECUTION_STATES,
    IngestionExecutionState,
    WorkflowContractError,
    get_ingestion_execution_state,
    run_ingestion_workflow,
    wait_for_ingestion,
)

TEST_SETTINGS = KGSettings(
    local_path=Path("/tmp/data"),
    gcp_project_id="test_proj",
    gcp_region="test_region",
    gcs_bucket_name="test_bucket",
    gcs_input_folder_path="ingestion/input/",
    gcs_output_folder_path="/output/path/",
    ingestion_workflow_name="test_workflow",
    ingestion_service_account="test@example.com",
)

WORKFLOW = "projects/test_proj/locations/test_region/workflows/test_workflow"
WORKFLOW_URL = f"https://workflows.googleapis.com/v1/{WORKFLOW}"
EXECUTION = f"{WORKFLOW}/executions/abc-123"

# The preprocessing call of each DCP release's deployed ingestion workflow.
DCP_116_SOURCE = """
launch_and_poll_preprocessing_job:
  steps:
    - create_batch_job:
        call: googleapis.batch.v1.projects.locations.jobs.create
"""
DCP_115_SOURCE = """
launch_and_poll_preprocessing_job:
  steps:
    - run_cloud_run_job:
        call: googleapis.run.v2.projects.locations.jobs.run
"""


def http_response(status_code: int, body: dict[str, Any]) -> Response:
    response = Response()
    response.status_code = status_code
    response._content = json.dumps(body).encode()
    return response


@pytest.fixture
def client_class() -> Iterator[MagicMock]:
    with patch(
        "dcp_tools.gcp_utilities.ingestion.IngestionJobClient", autospec=True
    ) as client_class:
        yield client_class


@pytest.fixture
def client(client_class: MagicMock) -> MagicMock:
    """The IngestionJobClient instance, serving a DCP 1.1.6 workflow definition."""
    instance = client_class.return_value
    instance.full_workflow_name = WORKFLOW
    instance.session = create_autospec(AuthorizedSession, instance=True)
    instance.session.get.return_value = http_response(
        200, {"name": WORKFLOW, "sourceContents": DCP_116_SOURCE}
    )
    instance.start_workflow.return_value = {"name": EXECUTION}
    return instance


def test_run_ingestion_workflow(client_class: MagicMock, client: MagicMock) -> None:
    execution = run_ingestion_workflow(
        TEST_SETTINGS, imports="test_import_a,test_import_b"
    )

    client_class.assert_called_once_with(
        workflow_name="test_workflow",
        service_account_email="test@example.com",
        project_id="test_proj",
        location="test_region",
    )
    client.session.get.assert_called_once_with(WORKFLOW_URL, timeout=60)
    client.start_workflow.assert_called_once_with(imports="test_import_a,test_import_b")
    assert execution == EXECUTION


@pytest.mark.parametrize("imports", [None, "", "  ", ",", " , ,"])
def test_run_ingestion_workflow_blank_imports_ingest_all(
    client: MagicMock, imports: str | None
) -> None:
    run_ingestion_workflow(TEST_SETTINGS, imports=imports)

    client.start_workflow.assert_called_once_with(imports="ALL_IMPORTS")


def test_run_ingestion_workflow_raises_when_execution_name_missing(
    client: MagicMock,
) -> None:
    client.start_workflow.return_value = {}

    with pytest.raises(RuntimeError, match="no execution name"):
        run_ingestion_workflow(TEST_SETTINGS)


def test_run_ingestion_workflow_wraps_errors(client: MagicMock) -> None:
    original_exception = Exception("Test exception")
    client.start_workflow.side_effect = original_exception

    with pytest.raises(RuntimeError, match="Test exception") as exc_info:
        run_ingestion_workflow(TEST_SETTINGS)

    assert not isinstance(exc_info.value, WorkflowContractError)
    assert exc_info.value.__cause__ == original_exception


@pytest.mark.parametrize(
    "workflow_response",
    [
        pytest.param(
            http_response(200, {"sourceContents": DCP_115_SOURCE}), id="dcp-1.1.5"
        ),
        pytest.param(http_response(200, {"name": WORKFLOW}), id="no-source"),
        pytest.param(
            http_response(403, {"error": {"status": "PERMISSION_DENIED"}}),
            id="forbidden",
        ),
        pytest.param(OSError("connection reset"), id="network-error"),
    ],
)
def test_contract_check_refuses_unconfirmed_workflow(
    client: MagicMock, workflow_response: Response | Exception
) -> None:
    if isinstance(workflow_response, Exception):
        client.session.get.side_effect = workflow_response
    else:
        client.session.get.return_value = workflow_response

    with pytest.raises(WorkflowContractError):
        run_ingestion_workflow(TEST_SETTINGS)

    client.start_workflow.assert_not_called()


def test_skipping_contract_check_starts_without_reading_workflow(
    client: MagicMock,
) -> None:
    client.session.get.return_value = http_response(
        200, {"sourceContents": DCP_115_SOURCE}
    )

    execution = run_ingestion_workflow(TEST_SETTINGS, skip_workflow_contract_check=True)

    client.session.get.assert_not_called()
    client.start_workflow.assert_called_once_with(imports="ALL_IMPORTS")
    assert execution == EXECUTION


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        pytest.param(
            {
                "state": "ACTIVE",
                "status": {
                    "currentSteps": [
                        {"routine": "main", "step": "run_preprocessing"},
                        {
                            "routine": "poll_cloud_batch_job_execution",
                            "step": "get_job",
                        },
                    ]
                },
            },
            IngestionExecutionState(
                state="ACTIVE",
                current_steps=(
                    "main.run_preprocessing",
                    "poll_cloud_batch_job_execution.get_job",
                ),
                error=None,
            ),
            id="active",
        ),
        pytest.param(
            {"state": "FAILED", "error": {"payload": "Dataflow job failed"}},
            IngestionExecutionState(
                state="FAILED", current_steps=(), error="Dataflow job failed"
            ),
            id="failed",
        ),
        pytest.param(
            {
                "state": "UNAVAILABLE",
                "stateError": {"type": "KMS_ERROR", "details": "Key revoked"},
            },
            IngestionExecutionState(
                state="UNAVAILABLE",
                current_steps=(),
                error=None,
                state_error="KMS_ERROR: Key revoked",
            ),
            id="unavailable",
        ),
        pytest.param(
            {"state": "UNAVAILABLE", "stateError": {"type": "TYPE_UNSPECIFIED"}},
            IngestionExecutionState(
                state="UNAVAILABLE",
                current_steps=(),
                error=None,
                state_error="TYPE_UNSPECIFIED",
            ),
            id="state-error-without-details",
        ),
    ],
)
def test_get_ingestion_execution_state(
    client: MagicMock, body: dict[str, Any], expected: IngestionExecutionState
) -> None:
    client.session.get.return_value = http_response(200, {"name": EXECUTION} | body)

    state = get_ingestion_execution_state(TEST_SETTINGS, EXECUTION)

    client.session.get.assert_called_once_with(
        f"https://workflowexecutions.googleapis.com/v1/{EXECUTION}", timeout=60
    )
    assert state == expected


def test_get_ingestion_execution_state_raises_on_http_error(client: MagicMock) -> None:
    client.session.get.return_value = http_response(404, {"error": {"code": 404}})

    with pytest.raises(RuntimeError, match="HTTP 404"):
        get_ingestion_execution_state(TEST_SETTINGS, EXECUTION)


class FakeClock:
    """Stands in for the `time` module: `sleep` advances `monotonic` instantly."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def clock() -> Iterator[FakeClock]:
    fake = FakeClock()
    with patch("dcp_tools.gcp_utilities.ingestion.time", fake):
        yield fake


def execution_responses(client: MagicMock, *states: str) -> None:
    """Serve one execution poll per state, in order."""
    client.session.get.side_effect = [
        http_response(200, {"name": EXECUTION, "state": state}) for state in states
    ]


@pytest.mark.parametrize("terminal_state", sorted(TERMINAL_EXECUTION_STATES))
def test_wait_for_ingestion_returns_terminal_state(
    client: MagicMock, clock: FakeClock, terminal_state: str
) -> None:
    execution_responses(
        client, "STATE_UNSPECIFIED", "QUEUED", "ACTIVE", "ACTIVE", terminal_state
    )

    state = wait_for_ingestion(TEST_SETTINGS, EXECUTION, poll_interval=5)

    assert state.state == terminal_state
    assert client.session.get.call_count == 5
    assert clock.sleeps == [5, 5, 5, 5]


def test_wait_for_ingestion_keeps_polling_through_unavailable(
    client: MagicMock, clock: FakeClock, caplog: pytest.LogCaptureFixture
) -> None:
    unavailable = {
        "state": "UNAVAILABLE",
        "stateError": {"type": "KMS_ERROR", "details": "Key revoked"},
    }
    client.session.get.side_effect = [
        http_response(200, {"state": "ACTIVE"}),
        http_response(200, unavailable),
        http_response(200, unavailable),
        http_response(200, {"state": "SUCCEEDED"}),
    ]

    with caplog.at_level(logging.INFO, logger="dcp_tools.gcp_utilities.ingestion"):
        state = wait_for_ingestion(TEST_SETTINGS, EXECUTION, poll_interval=5)

    assert state.state == "SUCCEEDED"
    assert client.session.get.call_count == 4
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert [record.getMessage() for record in warnings] == [
        f"Execution '{EXECUTION}' is UNAVAILABLE (current steps: none): "
        "KMS_ERROR: Key revoked"
    ]


def test_wait_for_ingestion_builds_one_client(
    client_class: MagicMock, client: MagicMock, clock: FakeClock
) -> None:
    execution_responses(client, "ACTIVE", "ACTIVE", "SUCCEEDED")

    wait_for_ingestion(TEST_SETTINGS, EXECUTION)

    client_class.assert_called_once()
    assert clock.sleeps == [DEFAULT_POLL_INTERVAL] * 2


def test_wait_for_ingestion_without_timeout_never_raises(
    client: MagicMock, clock: FakeClock
) -> None:
    polls = 1_000
    execution_responses(client, *["ACTIVE"] * polls, "SUCCEEDED")

    state = wait_for_ingestion(TEST_SETTINGS, EXECUTION, poll_interval=3600)

    assert state.state == "SUCCEEDED"
    assert len(clock.sleeps) == polls


def test_wait_for_ingestion_raises_on_timeout(
    client: MagicMock, clock: FakeClock
) -> None:
    execution_responses(client, *["ACTIVE"] * 10)

    with pytest.raises(TimeoutError, match=f"{EXECUTION}.*ACTIVE"):
        wait_for_ingestion(TEST_SETTINGS, EXECUTION, timeout=25, poll_interval=10)

    # The last sleep is cut short so the final poll lands on the deadline.
    assert clock.sleeps == [10, 10, 5]
    assert clock.now == 25
    assert client.session.get.call_count == 4


def test_wait_for_ingestion_returns_terminal_state_found_at_deadline(
    client: MagicMock, clock: FakeClock
) -> None:
    execution_responses(client, "ACTIVE", "FAILED")

    state = wait_for_ingestion(TEST_SETTINGS, EXECUTION, timeout=10, poll_interval=10)

    assert state.state == "FAILED"


def test_wait_for_ingestion_zero_timeout_polls_once(
    client: MagicMock, clock: FakeClock
) -> None:
    execution_responses(client, "ACTIVE")

    with pytest.raises(TimeoutError):
        wait_for_ingestion(TEST_SETTINGS, EXECUTION, timeout=0)

    assert clock.sleeps == []


@pytest.mark.parametrize(
    ("timeout", "poll_interval", "message"),
    [
        (None, 0, "poll_interval"),
        (None, -1, "poll_interval"),
        (-1, 30, "timeout"),
    ],
)
def test_wait_for_ingestion_validates_arguments(
    client: MagicMock, timeout: float | None, poll_interval: float, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        wait_for_ingestion(
            TEST_SETTINGS, EXECUTION, timeout=timeout, poll_interval=poll_interval
        )

    client.session.get.assert_not_called()


def test_wait_for_ingestion_logs_only_on_change(
    client: MagicMock, clock: FakeClock, caplog: pytest.LogCaptureFixture
) -> None:
    def execution(state: str, step: str | None = None) -> Response:
        steps = [] if step is None else [{"routine": "main", "step": step}]
        return http_response(200, {"state": state, "status": {"currentSteps": steps}})

    client.session.get.side_effect = [
        execution("QUEUED"),
        execution("QUEUED"),
        execution("ACTIVE", "preprocess"),
        execution("ACTIVE", "preprocess"),
        execution("ACTIVE", "ingest"),
        execution("SUCCEEDED"),
    ]

    with caplog.at_level(logging.INFO, logger="dcp_tools.gcp_utilities.ingestion"):
        wait_for_ingestion(TEST_SETTINGS, EXECUTION)

    assert [record.getMessage() for record in caplog.records] == [
        f"Execution '{EXECUTION}' is QUEUED (current steps: none)",
        f"Execution '{EXECUTION}' is ACTIVE (current steps: main.preprocess)",
        f"Execution '{EXECUTION}' is ACTIVE (current steps: main.ingest)",
        f"Execution '{EXECUTION}' is SUCCEEDED (current steps: none)",
    ]
