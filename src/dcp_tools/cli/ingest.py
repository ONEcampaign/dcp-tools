"""Run the ingestion workflow via CLI."""

import argparse
from functools import partial
from pathlib import Path

from dcp_tools.cli.common import (
    add_wait_arguments,
    check_wait_arguments,
    load_settings_from_args,
    wait_for_execution,
)
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
    add_wait_arguments(parser)
    parser.set_defaults(func=partial(run, parser=parser))


def run(args: argparse.Namespace, *, parser: argparse.ArgumentParser) -> int:
    """Execute the ``ingest`` command."""
    check_wait_arguments(parser, args)
    settings = load_settings_from_args(args)
    execution_name = run_ingestion_workflow(
        settings=settings,
        imports=args.imports,
        skip_workflow_contract_check=args.skip_workflow_contract_check,
    )
    if not args.wait:
        return 0
    return wait_for_execution(settings, execution_name, args)
