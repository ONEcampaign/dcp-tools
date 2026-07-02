"""Entry point for the ``dcp_tools`` command line interface."""

import argparse
from collections.abc import Iterable

from dcp_tools.cli import (
    csv2mcf,
    data_load,
    data_load_pipeline,
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
    data_load.add_parser(subparsers)
    data_load_pipeline.add_parser(subparsers)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    """Parse ``argv`` and execute the selected command."""
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if hasattr(args, "func"):
        return args.func(args)

    parser.error(f"Unknown command: {args.command}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
