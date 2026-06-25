"""CSV to MCF command implementation."""

from __future__ import annotations

import argparse
from pathlib import Path

from dcp_tools.custom_data.schema_tools import (
    NodeTypes,
    csv_metadata_to_mfc_file,
)

__all__ = ["add_parser", "run"]


def _kv_pair(value: str) -> tuple[str, str]:
    """Parse a KEY=VALUE string into a tuple."""
    if "=" not in value:
        raise ValueError(f"Invalid key-value pair: {value}")
    key, val = value.split("=", 1)
    return key.strip(), val.strip()


def add_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the ``csv2mcf`` subcommand with the CLI parser."""
    parser = subparsers.add_parser(
        "csv2mcf", help="Convert a CSV of Node metadata to an MCF file"
    )

    parser.add_argument("csv", type=Path, help="Path to the input CSV file")
    parser.add_argument("mcf", type=Path, help="Path to write the generated MCF")

    parser.add_argument(
        "--node-type",
        choices=[node_type.value for node_type in NodeTypes],
        default="Node",
        help="Type of node to create (default: %(default)s)",
    )

    parser.add_argument(
        "--column-mapping",
        metavar="CSV_COL=MCF_PROP",
        type=_kv_pair,
        action="append",
        help=(
            "Map CSV column names to MCF properties. "
            "May be used multiple times, eg: "
            "--column-mapping description=searchDescription --column-mapping indicator=Node"
        ),
    )

    parser.add_argument(
        "--csv-option",
        metavar="KEY=VALUE",
        type=_kv_pair,
        action="append",
        help=(
            "Extra keyword arguments forwarded to pandas.read_csv, "
            'e.g. --csv-option delimiter=";" --csv-option encoding=UTF-8'
        ),
    )

    parser.add_argument(
        "--ignore-column",
        metavar="COLUMN",
        action="append",
        help="Name of a CSV column to ignore. May be specified multiple times.",
    )

    parser.add_argument(
        "--override",
        action="store_true",
        help="Overwrite the output file if it exists",
    )

    parser.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    """Execute the ``csv2mcf`` command."""
    column_mapping = dict(args.column_mapping) if args.column_mapping else None
    csv_options = dict(args.csv_option) if args.csv_option else None

    csv_metadata_to_mfc_file(
        csv_path=args.csv,
        mcf_path=args.mcf,
        node_type=args.node_type,
        column_to_property_mapping=column_mapping,
        csv_options=csv_options,
        ignore_columns=args.ignore_column,
        override=args.override,
    )
    return 0
