"""Run the full Knowledge Graph pipeline via CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from dcp_tools.cli.common import load_settings_from_args
from dcp_tools.gcp_utilities.ingestion import (
    check_ingestion_workflow_contract,
    run_ingestion_workflow,
)
from dcp_tools.gcp_utilities.pipeline import upload_to_cloud_storage

__all__ = ["add_parser", "run"]


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``pipeline`` subcommand."""
    parser = subparsers.add_parser(
        "pipeline", help="Run the full Knowledge Graph loading pipeline"
    )
    parser.add_argument(
        "--settings-file", type=Path, help="Path to the KG settings JSON file"
    )
    parser.add_argument(
        "--env-file", type=Path, help="Optional .env file containing KG settings"
    )
    parser.add_argument(
        "--directory",
        type=Path,
        help="Local directory to upload. Defaults to settings.LOCAL_PATH",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        default=False,
        help="Delete remote blobs that no longer have a local counterpart after uploading",
    )
    parser.add_argument(
        "--skip-workflow-contract-check",
        action="store_true",
        help="Start the workflow without checking it comes from a DCP 1.1.6 stack",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    """Execute the ``pipeline`` command."""
    settings = load_settings_from_args(args)
    # Check before uploading, so a stack older than DCP 1.1.6 gets no files.
    if not args.skip_workflow_contract_check:
        check_ingestion_workflow_contract(settings)
    upload_to_cloud_storage(settings=settings, directory=args.directory, sync=args.sync)
    run_ingestion_workflow(settings=settings, skip_workflow_contract_check=True)
    return 0
