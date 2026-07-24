from __future__ import annotations

import ast
import os
import re
from collections.abc import Iterable
from enum import StrEnum
from pathlib import Path
from typing import Any

import pandas as pd

from dcp_tools.custom_data.models.data_files import MCFFileName
from dcp_tools.custom_data.models.mcf import Node, Nodes
from dcp_tools.custom_data.models.stat_vars import (
    StatVarGroupNode,
    StatVarNode,
    StatVarPeerGroupNode,
)
from dcp_tools.custom_data.models.topics import TopicNode


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
) -> Nodes:
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
        "Node": Node,
        "StatVar": StatVarNode,
        "StatVarGroup": StatVarGroupNode,
        "Topic": TopicNode,
        "StatVarPeerGroup": StatVarPeerGroupNode,
    }

    for record in records:
        clean: dict[str, Any] = {
            k: _parse_maybe_list(v)
            for k, v in record.items()
            if not pd.isna(v) and v != ""
        }
        if "Node" in clean:
            clean["dcid"] = clean.pop("Node")
        nodes.append(constructor[node_type](**clean))

    return Nodes(nodes=nodes)


def to_camel_case(segment: str) -> str:
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


def resolve_group_paths(
    paths: Iterable[str], *, group_namespace: str
) -> tuple[dict[str, str], list[StatVarGroupNode]]:
    """Resolve slash-separated group path strings into StatVarGroup dcids.

    Each path (e.g. "Economic/Employment/Unemployment") is split into segments,
    each segment is camelCased and minted into a chain of StatVarGroupNode
    objects rooted at "dcid:dc/g/Root". A segment shared by two paths (a common
    prefix, or the same path repeated) mints only one node.

    Args:
        paths: Raw slash-separated group path strings, one per StatVar. Each path
            has line breaks removed, a leading '-' stripped, and '/' and whitespace
            stripped from both ends before being split; empty and whitespace-only
            segments are dropped.
        group_namespace: The namespace under which group dcids are minted (e.g.,
            "one"). The resulting dcids have the form
            "dcid:{group_namespace}/g/{groupSlug}".

    Returns:
        A tuple of:
            - A mapping from each input path (as given) to the dcid of its
              deepest group. A path with no non-empty segments once cleaned
              (e.g. "-", "/") is omitted.
            - The StatVarGroupNode objects for every unique group, in
              first-seen order.
    """

    resolved: dict[str, str] = {}
    group_nodes: list[StatVarGroupNode] = []
    seen: set[str] = set()
    root = f"dcid:{group_namespace}/g/"

    for raw in paths:
        if raw in resolved:
            continue

        # Strip line breaks and trailing spaces first. Group paths used to reach the
        # resolver through `StatVarNode(memberOf=...)`, which cleaned them on the
        # way in; resolving before construction skips that. Segments that are only
        # whitespace are dropped too, or `to_camelCase` yields an empty slug and the
        # path mints a group whose dcid ends in a bare "g/".
        cleaned = Node._clean_value(raw).lstrip("-").strip("/ ")
        parts = [p for p in cleaned.split("/") if p.strip()]
        if not parts:
            continue
        slug_parts = [to_camel_case(part) for part in parts]

        for idx, part in enumerate(parts):
            group_dcid = root + slug_parts[idx]

            if group_dcid not in seen:
                seen.add(group_dcid)
                parent = "dcid:dc/g/Root" if idx == 0 else root + slug_parts[idx - 1]
                group_nodes.append(
                    StatVarGroupNode(
                        dcid=group_dcid, name=part, specialization_of=parent
                    )
                )

        resolved[raw] = group_dcid

    return resolved, group_nodes


def csv_metadata_to_nodes(
    file_path: str | os.PathLike[str],
    *,
    node_type: NodeTypes | str = "StatVar",
    column_to_property_mapping: dict[str, str] | None = None,
    csv_options: dict[str, Any] | None = None,
    ignore_columns: list[str] | None = None,
    parse_groups: bool = False,
    group_namespace: str | None = None,
) -> Nodes:
    """Read a CSV of StatVar metadata and return the corresponding MCF StatVar nodes.

    Args:
        file_path: Path to the CSV file.
        node_type: The type of node to create. Default is "StatVar".
        column_to_property_mapping: Optional map from CSV column names to
            ``StatVarNode`` attribute names.
        csv_options: Extra keyword arguments forwarded verbatim to
            ``pandas.read_csv``.
        ignore_columns: Optional list of columns to ignore when reading the CSV.
        parse_groups: If True, the ``memberOf`` column is treated as a
            slash-separated group path (e.g. "Economic/Employment/Unemployment"),
            resolved via ``resolve_group_paths``, and the minted
            ``StatVarGroupNode`` objects are appended to the returned
            container. A row whose ``memberOf`` carries no group path, whether
            missing, empty, or cleaning to no segments at all (e.g. "-", "/"), is
            left unset rather than raising. Defaults to False.
        group_namespace: Namespace under which group dcids are minted (e.g.,
            "one"). Only used if ``parse_groups`` is True; an empty string is
            used if not provided.

    Returns:
        A ``Nodes`` container populated with ``StatVarNode`` objects, followed
        by any ``StatVarGroupNode`` objects minted from ``memberOf`` paths.

    Raises:
        ValueError: If ``parse_groups`` is True and the CSV has no ``memberOf``
            column.
    """

    if column_to_property_mapping is None:
        column_to_property_mapping = {}

    if csv_options is None:
        csv_options = {}

    if ignore_columns is None:
        ignore_columns = []

    data = (
        pd.read_csv(file_path, **csv_options)
        .drop(columns=ignore_columns)
        .rename(columns=column_to_property_mapping)
    )

    group_nodes: list[StatVarGroupNode] = []
    if parse_groups:
        if "memberOf" not in data.columns:
            raise ValueError(
                "parse_groups=True requires a 'memberOf' column in the CSV."
            )

        present = data["memberOf"].map(lambda v: not pd.isna(v) and v != "")
        resolved, group_nodes = resolve_group_paths(
            data.loc[present, "memberOf"], group_namespace=group_namespace or ""
        )
        # A path that cleans to no segments at all (e.g. "-", "/") is absent from
        # `resolved` and leaves the node ungrouped, the same as a blank cell. Keeping
        # the raw value would send it to a `memberOf` that now enforces the group
        # pattern, turning a row that carries no group into a hard failure.
        data["memberOf"] = data.loc[present, "memberOf"].map(resolved.get)

    nodes = _rows_to_stat_var_nodes(data, node_type=node_type)
    for group_node in group_nodes:
        nodes.add(group_node)
    return nodes


def validate_mcf_file_name(file_name: str | MCFFileName) -> str:
    if isinstance(file_name, str):
        return MCFFileName(file_name=file_name).file_name
    return file_name.file_name


def csv_metadata_to_mcf_file(
    csv_path: str | os.PathLike[str],
    mcf_path: str | os.PathLike[str],
    node_type: NodeTypes | str,
    *,
    column_to_property_mapping: dict[str, str] | None = None,
    csv_options: dict[str, Any] | None = None,
    ignore_columns: list[str] | None = None,
    overwrite: bool = True,
) -> None:
    """Convert a CSV of Node metadata to an MCF file.

    Args:
        csv_path: Path to the input CSV file.
        mcf_path: Path to write the generated MCF file.
        node_type: The type of node to create (e.g., "StatVar", "StatVarGroup").
        column_to_property_mapping: Optional mapping from CSV columns to MCF properties.
        csv_options: Extra options for reading the CSV file.
        ignore_columns: List of columns to ignore when reading the CSV.
        overwrite: If True, overwrite the output file if it exists.

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

    nodes.export_to_mcf_file(file_path=mcf_path, overwrite=overwrite)
