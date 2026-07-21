from __future__ import annotations

import ast
import re
from enum import StrEnum
from os import PathLike
from pathlib import Path
from typing import Any

import pandas as pd

from dcp_tools.custom_data.models.data_files import MCFFileName
from dcp_tools.custom_data.models.mcf import MCFNode, MCFNodes
from dcp_tools.custom_data.models.stat_vars import (
    StatVarGroupMCFNode,
    StatVarMCFNode,
    StatVarPeerGroupMCFNode,
)
from dcp_tools.custom_data.models.topics import TopicMCFNode


class NodeTypes(StrEnum):
    """Enumeration of node types used in Data Commons."""

    NODE = "Node"
    STAT_VAR = "StatVar"
    STAT_VAR_GROUP = "StatVarGroup"
    TOPIC = "Topic"
    STAT_VAR_PEER_GROUP = "StatVarPeerGroup"


def _parse_maybe_list(s: str | Any) -> str | list[str]:
    """If s (after stripping) starts with '[' and is valid Python literal,
    return the evaluated list. Otherwise, return s unchanged."""
    if not isinstance(s, str):
        return s
    s_stripped = s.strip()
    if s_stripped.startswith("["):
        try:
            return ast.literal_eval(s_stripped)
        except (ValueError, SyntaxError):
            # Not a valid Python literal — fall back to original string
            return s
    else:
        return s


def _rows_to_stat_var_nodes(
    data: pd.DataFrame, node_type: str | NodeTypes = "StatVar"
) -> MCFNodes[StatVarMCFNode]:
    """Convert a DataFrame into a collection of Node objects (of the type selected).

    Empty/NA values are removed from each row before constructing the node.

    Args:
        data: A pandas ``DataFrame`` where every row describes a StatVar.
        node_type: The type of node to create. Default is "StatVar".

    Returns:
        A ``Nodes`` container with one Node of the selected type per row.
    """

    if isinstance(node_type, str):
        node_type = NodeTypes(node_type)

    node_type = str(node_type)

    records = data.to_dict(orient="records")
    nodes = []

    constructor = {
        "Node": MCFNode,
        "StatVar": StatVarMCFNode,
        "StatVarGroup": StatVarGroupMCFNode,
        "Topic": TopicMCFNode,
        "StatVarPeerGroup": StatVarPeerGroupMCFNode,
    }

    for record in records:
        clean: dict[str, Any] = {
            k: _parse_maybe_list(v)
            for k, v in record.items()
            if not pd.isna(v) and v != ""
        }
        nodes.append(constructor[node_type](**clean))

    return MCFNodes(nodes=nodes)


def to_camelCase(segment: str) -> str:
    """
    Turn a segment like 'Official Development Assistance' into 'officialDevelopmentAssistance'.
    Keep all-upper or already-camel segments (e.g. DAC1, ODA) unchanged.
    """
    seg = segment.strip()
    seg = re.sub(r"[:,();&]", "_", seg)

    # All upper case
    if re.fullmatch(r"[A-Z0-9]+", seg):
        return seg

    # Already camel case
    if seg and seg[0].islower() and " " not in seg:
        return seg

    # Split by whitespace and join with camel case
    words = re.split(r"\s+", seg)
    return words[0].lower() + "".join(w.title() for w in words[1:])


def build_stat_var_groups_from_strings(
    stat_vars: MCFNodes[StatVarMCFNode], *, groups_namespace: str
) -> MCFNodes[StatVarMCFNode]:
    """
    Build hierarchical StatVarGroup nodes from string-encoded group paths and attach them to StatVar nodes.

    This function reads the `memberOf` attribute of each StatVar node in `stat_vars`, which is
    expected to be a slash-separated string path describing its group hierarchy (e.g.,
    "Economic/Employment/Unemployment"). It generates StatVarGroupMCFNode objects for each
    group level, sets up their parent-child relationships, and updates the original StatVar
    nodes to reference the deepest group DCID.

    Args:
        stat_vars: An MCFNodes container holding StatVarMCFNode objects. Each node must have a
            `memberOf` attribute set to a path string indicating its group hierarchy.
        groups_namespace: The namespace under which group DCIDs will be created (e.g.,
            "one"). The resulting group DCIDs will have the form
            "dcid: {groups_namespace}/g/{{groupSlug}}".

    Returns:
        The same MCFNodes container provided as `stat_vars`, extended in-place with newly
        created StatVarGroupMCFNode objects representing each unique group. Each StatVarMCFNode's
        `memberOf` will be updated to the DCID of its deepest group.
    """

    group_nodes, seen = [], set()
    root = f"dcid:{groups_namespace}/g/"

    for node_idx, node in enumerate(stat_vars.nodes):
        # clean
        raw = node.memberOf
        raw = raw.lstrip("-").strip("/ ")
        parts = [p for p in raw.split("/") if p]
        slug_parts = [to_camelCase(part) for part in parts]

        for idx, part in enumerate(parts):
            group_node = root + f"{slug_parts[idx]}"

            if idx == len(parts) - 1:
                stat_vars.nodes[node_idx].memberOf = group_node

            if group_node in seen:
                continue
            seen.add(group_node)

            parent = "dcid:dc/g/Root" if idx == 0 else root + f"{slug_parts[idx - 1]}"

            group_nodes.append(
                StatVarGroupMCFNode(Node=group_node, name=part, specializationOf=parent)
            )

    stat_vars.nodes.extend(group_nodes)

    return stat_vars


def csv_metadata_to_nodes(
    file_path: str | PathLike[str],
    *,
    node_type: NodeTypes | str = "StatVar",
    column_to_property_mapping: dict[str, str] | None = None,
    csv_options: dict[str, Any] | None = None,
    ignore_columns: list[str] | None = None,
) -> MCFNodes[StatVarMCFNode]:
    """Read a CSV of StatVar metadata and return the corresponding MCF StatVar nodes.

    Args:
        file_path: Path to the CSV file.
        node_type: The type of node to create. Default is "StatVar".
        column_to_property_mapping: Optional map from CSV column names to
            ``StatVarMCFNode`` attribute names.
        csv_options: Extra keyword arguments forwarded verbatim to
            ``pandas.read_csv``.
        ignore_columns: Optional list of columns to ignore when reading the CSV.

    Returns:
        A ``Nodes`` container populated with ``StatVarMCFNode`` objects.
    """

    if column_to_property_mapping is None:
        column_to_property_mapping = {}

    if csv_options is None:
        csv_options = {}

    if ignore_columns is None:
        ignore_columns = []

    return (
        pd.read_csv(file_path, **csv_options)
        .drop(columns=ignore_columns)
        .rename(columns=column_to_property_mapping)
        .pipe(_rows_to_stat_var_nodes, node_type=node_type)
    )


def validate_mcf_file_name(file_name: str | MCFFileName) -> str:
    if isinstance(file_name, str):
        return MCFFileName(file_name=file_name).file_name
    return file_name.file_name


def csv_metadata_to_mcf_file(
    csv_path: str | PathLike[str],
    mcf_path: str | PathLike[str],
    node_type: NodeTypes | str,
    *,
    column_to_property_mapping: dict[str, str] | None = None,
    csv_options: dict[str, Any] | None = None,
    ignore_columns: list[str] | None = None,
    override: bool = False,
) -> None:
    """Convert a CSV of Node metadata to an MCF file.

    Args:
        csv_path: Path to the input CSV file.
        mcf_path: Path to write the generated MCF file.
        node_type: The type of node to create (e.g., "StatVar", "StatVarGroup").
        column_to_property_mapping: Optional mapping from CSV columns to MCF properties.
        csv_options: Extra options for reading the CSV file.
        ignore_columns: List of columns to ignore when reading the CSV.
        override: If True, overwrite the output file if it exists.

    """

    mcf_path = Path(mcf_path)
    validate_mcf_file_name(mcf_path.name)

    nodes = csv_metadata_to_nodes(
        file_path=csv_path,
        node_type=node_type,
        column_to_property_mapping=column_to_property_mapping,
        csv_options=csv_options,
        ignore_columns=ignore_columns,
    )

    nodes.export_to_mcf_file(file_path=mcf_path, override=override)
