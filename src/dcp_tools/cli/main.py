"""Entry point for the ``dcp_tools`` command line interface."""

import argparse
import logging
import os
from collections.abc import Iterable

from dcp_tools.cli import (
    csv2mcf,
    ingest,
    pipeline,
    upload,
)

__all__ = ["main"]


def _build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser and register commands."""
    parser = argparse.ArgumentParser(
        description="Utilities for working with Data Commons files"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    csv2mcf.add_parser(subparsers)
    upload.add_parser(subparsers)
    ingest.add_parser(subparsers)
    pipeline.add_parser(subparsers)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    """Parse ``argv`` and execute the selected command."""
    # LOG_LEVEL applies to dcp-tools only; dependencies show warnings and above.
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logging.getLogger("dcp_tools").setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if hasattr(args, "func"):
        return args.func(args)

    parser.error(f"Unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
