"""Run the ingestion workflow via CLI."""

import argparse
from pathlib import Path

from dcp_tools.cli.common import load_settings_from_args
from dcp_tools.gcp_utilities.ingestion import run_ingestion_workflow

__all__ = ["add_parser", "run"]


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``ingest`` subcommand."""
    parser = subparsers.add_parser(
        "ingest", help="Run the Knowledge Graph ingestion workflow"
    )
    parser.add_argument(
        "--settings-file", type=Path, help="Path to the KG settings JSON file"
    )
    parser.add_argument(
        "--env-file", type=Path, help="Optional .env file containing KG settings"
    )
    parser.add_argument(
        "--imports",
        type=str,
        help="Comma-separated list of imports to ingest, defaults to all imports",
    )
    parser.add_argument(
        "--skip-workflow-contract-check",
        action="store_true",
        help="Start the workflow without checking it comes from a DCP 1.1.6 stack",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    """Execute the ``ingest`` command."""
    settings = load_settings_from_args(args)
    run_ingestion_workflow(
        settings=settings,
        imports=args.imports,
        skip_workflow_contract_check=args.skip_workflow_contract_check,
    )
    return 0
