"""This module contains functions to run the data ingestion workflow."""

import logging
import time
from dataclasses import dataclass
from typing import Any

from datacommons_admin.core.clients import IngestionJobClient
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import AuthorizedSession

from dcp_tools.gcp_utilities.settings import KGSettings

logger = logging.getLogger(__name__)

WORKFLOWS_API = "https://workflows.googleapis.com/v1"
WORKFLOW_EXECUTIONS_API = "https://workflowexecutions.googleapis.com/v1"

# The DCP 1.1.6 ingestion workflow creates its preprocessing Cloud Batch job itself,
# which is why datacommons-admin 1.1.6 sends it only the import list. DCP 1.1.5 and
# earlier run a Cloud Run job instead and need a temp location in the request.
DCP_116_WORKFLOW_MARKER = "googleapis.batch.v1.projects.locations.jobs.create"

# Workflow Executions API states after which an execution no longer changes.
TERMINAL_EXECUTION_STATES = frozenset(
    {"SUCCEEDED", "FAILED", "CANCELLED", "UNAVAILABLE"}
)
DEFAULT_POLL_INTERVAL = 30


class WorkflowContractError(RuntimeError):
    """The ingestion workflow is not one this version of dcp-tools can start."""


@dataclass(frozen=True)
class IngestionExecutionState:
    """State of an ingestion workflow execution.

    Attributes:
        state: Execution state from the Workflow Executions API: "QUEUED", "ACTIVE",
            "SUCCEEDED", "FAILED", "CANCELLED", "UNAVAILABLE" or
            "STATE_UNSPECIFIED".
        current_steps: Steps the execution is running, as "routine.step". Empty
            once the execution has finished.
        error: Error payload when the execution failed, otherwise None.
    """

    state: str
    current_steps: tuple[str, ...]
    error: str | None


def _ingestion_client(settings: KGSettings) -> IngestionJobClient:
    return IngestionJobClient(
        workflow_name=settings.ingestion_workflow_name,
        service_account_email=settings.ingestion_service_account,
        project_id=settings.gcp_project_id,
        location=settings.gcp_region,
    )


def _get_json(session: AuthorizedSession, url: str) -> dict[str, Any]:
    response = session.get(url, timeout=60)
    if not response.ok:
        raise RuntimeError(
            f"GET {url} returned HTTP {response.status_code}: {response.text}"
        )
    return response.json()


def _check_workflow_contract(client: IngestionJobClient) -> None:
    """Refuse a workflow that does not come from a DCP 1.1.6 stack."""
    workflow = client.full_workflow_name
    override = (
        "Pass skip_workflow_contract_check=True (--skip-workflow-contract-check on "
        "the CLI) to start it anyway."
    )
    try:
        source = _get_json(client.session, f"{WORKFLOWS_API}/{workflow}").get(
            "sourceContents"
        )
    except (OSError, ValueError, RuntimeError, GoogleAuthError) as e:
        raise WorkflowContractError(
            f"Could not read the definition of workflow '{workflow}' to confirm it "
            f"belongs to a Data Commons Platform 1.1.6 stack: {e}. Reading it needs "
            f"roles/workflows.viewer. {override}"
        ) from e

    if not source:
        raise WorkflowContractError(
            f"The definition of workflow '{workflow}' has no source to confirm it "
            f"belongs to a Data Commons Platform 1.1.6 stack. {override}"
        )
    if DCP_116_WORKFLOW_MARKER not in source:
        raise WorkflowContractError(
            f"Workflow '{workflow}' belongs to a Data Commons Platform stack older "
            "than 1.1.6: it does not create its preprocessing job on Cloud Batch. "
            "dcp-tools 1.1 starts ingestion only on DCP 1.1.6. Use dcp-tools 1.0 "
            f"with DCP stacks up to 1.1.5. {override}"
        )


def check_ingestion_workflow_contract(settings: KGSettings) -> None:
    """Check that the ingestion workflow comes from a Data Commons Platform 1.1.6 stack.

    Reads the workflow's definition from the Workflows API with the credentials
    `run_ingestion_workflow` uses: Application Default Credentials, impersonating
    `ingestion_service_account` when it is set. That identity needs
    `roles/workflows.viewer`.

    Args:
        settings (KGSettings): Settings for the workflow.

    Raises:
        WorkflowContractError: The workflow definition could not be read, or does
            not come from a DCP 1.1.6 stack.
    """
    _check_workflow_contract(_ingestion_client(settings))


def run_ingestion_workflow(
    settings: KGSettings,
    *,
    imports: str | None = None,
    skip_workflow_contract_check: bool = False,
) -> str:
    """Trigger the ingestion workflow to load data into the knowledge graph.

    Runs the check in `check_ingestion_workflow_contract` first and refuses to
    start a workflow that does not come from a Data Commons Platform 1.1.6 stack.
    Both calls use Application Default Credentials, impersonating
    `ingestion_service_account` when it is set.

    Args:
        settings (KGSettings): Settings for the workflow.
        imports (str | None): Comma-separated list of imports to ingest. All imports
            are ingested if omitted or blank.
        skip_workflow_contract_check (bool): Start the workflow without running
            `check_ingestion_workflow_contract` first.

    Returns:
        str: Resource name of the started execution, which
            `get_ingestion_execution_state` and `wait_for_ingestion` take.

    Raises:
        WorkflowContractError: The workflow definition could not be read, or does
            not come from a DCP 1.1.6 stack.
        RuntimeError: The workflow could not be started, or its response held no
            execution name.
    """
    if not imports or not imports.replace(",", "").strip():
        imports = "ALL_IMPORTS"

    logger.info(
        f"Starting data ingestion workflow '{settings.ingestion_workflow_name}'"
    )
    try:
        client = _ingestion_client(settings)
        if not skip_workflow_contract_check:
            _check_workflow_contract(client)
        result = client.start_workflow(imports=imports)
    except WorkflowContractError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to start ingestion workflow: {e}") from e

    execution_name = result.get("name")
    if not execution_name:
        raise RuntimeError(
            f"Ingestion workflow '{settings.ingestion_workflow_name}' returned no "
            f"execution name: {result}"
        )
    logger.info(f"Started workflow execution '{execution_name}'")
    return execution_name


def _read_execution_state(
    session: AuthorizedSession, execution_name: str
) -> IngestionExecutionState:
    execution = _get_json(session, f"{WORKFLOW_EXECUTIONS_API}/{execution_name}")
    steps = execution.get("status", {}).get("currentSteps", [])
    return IngestionExecutionState(
        state=execution.get("state", "STATE_UNSPECIFIED"),
        current_steps=tuple(f"{s['routine']}.{s['step']}" for s in steps),
        error=execution.get("error", {}).get("payload"),
    )


def get_ingestion_execution_state(
    settings: KGSettings, execution_name: str
) -> IngestionExecutionState:
    """Read the state of an ingestion workflow execution.

    Uses the same credentials as `run_ingestion_workflow`.

    Args:
        settings (KGSettings): Settings for the workflow.
        execution_name (str): Execution resource name returned by
            `run_ingestion_workflow`.

    Returns:
        IngestionExecutionState: The execution's state, current steps and error.

    Raises:
        RuntimeError: The Workflow Executions API returned an error.
    """
    return _read_execution_state(_ingestion_client(settings).session, execution_name)


def wait_for_ingestion(
    settings: KGSettings,
    execution_name: str,
    *,
    timeout: float | None = None,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
) -> IngestionExecutionState:
    """Poll an ingestion workflow execution until it reaches a terminal state.

    Uses the same credentials as `run_ingestion_workflow`. Logs the state and
    current steps each time they change.

    Args:
        settings (KGSettings): Settings for the workflow.
        execution_name (str): Execution resource name returned by
            `run_ingestion_workflow`.
        timeout (float | None): Seconds to wait before giving up. Waits
            indefinitely if None.
        poll_interval (float): Seconds between polls.

    Returns:
        IngestionExecutionState: The terminal state, one of
            `TERMINAL_EXECUTION_STATES`. A failed or cancelled execution is
            returned, not raised.

    Raises:
        ValueError: `poll_interval` is not positive, or `timeout` is negative.
        TimeoutError: The execution had not finished within `timeout` seconds.
        RuntimeError: The Workflow Executions API returned an error.
    """
    if poll_interval <= 0:
        raise ValueError(f"poll_interval must be positive, got {poll_interval}")
    if timeout is not None and timeout < 0:
        raise ValueError(f"timeout must not be negative, got {timeout}")

    session = _ingestion_client(settings).session
    deadline = None if timeout is None else time.monotonic() + timeout
    previous_state = None
    while True:
        execution_state = _read_execution_state(session, execution_name)
        if execution_state != previous_state:
            steps = ", ".join(execution_state.current_steps) or "none"
            logger.info(
                f"Execution '{execution_name}' is {execution_state.state} "
                f"(current steps: {steps})"
            )
            previous_state = execution_state
        if execution_state.state in TERMINAL_EXECUTION_STATES:
            return execution_state

        if deadline is None:
            time.sleep(poll_interval)
            continue
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(
                f"Execution '{execution_name}' had not finished after {timeout} "
                f"seconds; its last state was {execution_state.state}"
            )
        time.sleep(min(poll_interval, remaining))
