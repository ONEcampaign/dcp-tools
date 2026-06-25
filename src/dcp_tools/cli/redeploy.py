"""Redeploy the Data Commons service via CLI."""

import argparse
from pathlib import Path

from dcp_tools.cli.common import load_settings_from_args
from dcp_tools.gcp_utilities.pipeline import redeploy_service

__all__ = ["add_parser", "run"]


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``redeploy`` subcommand."""
    parser = subparsers.add_parser("redeploy", help="Redeploy the Data Commons service")
    parser.add_argument(
        "--settings-file", type=Path, help="Path to the KG settings JSON file"
    )
    parser.add_argument(
        "--env-file", type=Path, help="Optional .env file containing KG settings"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Timeout for the redeploy operation (default: %(default)s)",
    )
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    """Execute the ``redeploy`` command."""
    settings = load_settings_from_args(args)
    redeploy_service(settings=settings, timeout=args.timeout)
    return 0
