"""Upload data to Cloud Storage via CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from dcp_tools.cli.common import load_settings_from_args
from dcp_tools.gcp_utilities.pipeline import upload_to_cloud_storage

__all__ = ["add_parser", "run"]


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``upload`` subcommand."""
    parser = subparsers.add_parser(
        "upload", help="Upload local data to Google Cloud Storage"
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
    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    """Execute the ``upload`` command."""
    settings = load_settings_from_args(args)
    upload_to_cloud_storage(settings=settings, directory=args.directory, sync=args.sync)
    return 0
