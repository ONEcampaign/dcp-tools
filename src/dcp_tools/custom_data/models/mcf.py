from __future__ import annotations

from enum import Enum
from os import PathLike
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, model_validator

from dcp_tools.custom_data.models.common import (
    Dcid,
    DcidOrListDcid,
    QuotedStr,
    StrOrListStr,
)


class MCFNode(BaseModel):
    """Represents a general node for MCF.

    Attributes:
        Node: Identifier for the Node.
        name: The human-readable name for the Node.
        typeOf: The DCID representing the typeOf this Node. It can be a single DCID
            or a list of DCIDs if the Node belongs to multiple types.
        dcid: Optional DCID for uniquely identifying the Node.
        description: Optional human-readable description.
        provenance: Optional provenance information.
        shortDisplayName: Optional human-readable short name for display.
        subClassOf: Optional DCID indicating the 'parent' Node class.
    """

    Node: Dcid
    name: QuotedStr | None = None
    typeOf: DcidOrListDcid
    dcid: Dcid | None = None
    description: QuotedStr | None = None
    provenance: QuotedStr | None = None
    shortDisplayName: QuotedStr | None = None
    subClassOf: StrOrListStr | None = None

    # Allow extra fields since MCF can have arbitrary properties and this
    # class is not comprehensive of all possible MCF properties. Assignments are
    # validated too, so patterns like Dcid/GroupDcid are enforced on `MCFNodes.rename`
    # (which assigns `.Node`), not just on construction.
    model_config = ConfigDict(extra="allow", validate_assignment=True)

    @classmethod
    def _clean_value(cls, value: Any) -> Any:
        """Recursively remove line breaks and trailing spaces from strings.

        Enum members (e.g. StatType) are returned untouched. They are not plain
        strings even when their base class is str: `value.replace(...)` on a
        StrEnum member returns a plain `str`, which would silently degrade the
        enum to its value. That only matters under validate_assignment, where this
        also runs on assignment (see `__setattr__` below) over an
        already-constructed value.
        """
        if isinstance(value, Enum):
            return value
        if isinstance(value, str):
            return value.replace("\n", "").replace("\r", "").rstrip()
        if isinstance(value, list):
            return [cls._clean_value(v) for v in value]
        if isinstance(value, dict):
            return {k: cls._clean_value(v) for k, v in value.items()}
        return value

    @model_validator(mode="before")
    @classmethod
    def _strip_whitespace(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return {k: cls._clean_value(v) for k, v in data.items()}
        return data

    def __setattr__(self, name: str, value: Any) -> None:
        """Clean the value before it is assigned, as construction cleans it.

        Under `validate_assignment`, `_strip_whitespace` reruns on every assignment,
        but its cleaned output is applied only to the *other*, already-set fields and
        is discarded for the field actually being assigned. Cleaning here instead
        covers both declared fields and the `extra="allow"` keys that carry arbitrary
        MCF properties, neither of which a wildcard field validator would reach in
        full.
        """
        super().__setattr__(name, self._clean_value(value))

    @property
    def mcf(self) -> str:
        """Generates an MCF-formatted string representing this node.

        Returns:
            A string formatted according to MCF conventions, sorted alphabetically
                except for 'Node', which appears first.
        """
        data = self.model_dump(exclude_none=True)

        # Pull Node first, then sort for consistent ordering
        lines = [f"Node: {data.pop('Node')}"]
        lines.extend(f"{k}: {v}" for k, v in data.items())

        return "\n".join(lines) + "\n\n"


class MCFNodes(BaseModel):
    """Represents a collection of Nodes.

    Attributes:
        nodes: A list of Node instances.
    """

    nodes: list[MCFNode] = Field(default_factory=list)
    _pos: dict[str, int] = PrivateAttr(default_factory=dict)

    def _reindex(self) -> None:
        """If needed, rebuild the index of nodes."""
        self._pos = {n.Node: i for i, n in enumerate(self.nodes)}

    def model_post_init(self, context: Any, /) -> None:
        self._reindex()

    def _expect_present(self, node_id: str) -> int:
        """Try to find the index of a node by its ID."""
        try:
            return self._pos[node_id]
        except KeyError:
            raise ValueError(f"Node '{node_id}' not found.") from None

    def _flush(self, block: dict[str, str]) -> None:
        """Convert the current block into an `MCFNode` and store it."""
        if not block:
            return
        if "Node" not in block:
            raise ValueError(
                f"Missing mandatory 'Node:' line in block starting with "
                f"{next(iter(block.items()))!r}"
            )
        self.add(MCFNode(**block))
        block.clear()

    def load_from_mcf_file(self, file_path: str | PathLike) -> MCFNodes:
        """Parses MCF nodes from a file and populates the collection.

        Each node block is expected to start with
            ``Node: <identifier>``
        followed by one or more ``key: value`` lines, and is delimited
        by a blank line (or EOF).

        Args:
            file_path: The path of the MCF file to read.
        """

        path = Path(file_path)
        current_block: dict[str, str] = {}

        with path.open(encoding="utf-8") as file_obj:
            for line_no, raw_line in enumerate(file_obj, start=1):
                stripped = raw_line.strip()

                # Blank line means end of current block
                if not stripped:
                    self._flush(current_block)
                    continue

                key, sep, value = stripped.partition(":")
                if not sep or not key or not value:
                    raise ValueError(
                        f"Invalid MCF syntax on line {line_no}: {raw_line!r}"
                    )
                current_block[key.strip()] = value.strip()

        # Handle the final block if the file does not end with a blank line.
        self._flush(current_block)

        return self

    def add(self, node: MCFNode, override: bool = False) -> MCFNodes:
        """Adds a new node to the collection.

        Args:
            node: The MCFNode instance to add.
            override: If True, overwrite the existing node with the same ID.
                If False, raise an error if a node with the same ID already exists.
        """
        idx = self._pos.get(node.Node)

        if idx is not None:
            if not override:
                raise ValueError(
                    f"Node '{node.Node}' already exists; pass override=True to replace it."
                )
            self.nodes[idx] = node
        else:
            self._pos[node.Node] = len(self.nodes)
            self.nodes.append(node)

        return self

    def remove(self, node_id: str) -> MCFNodes:
        """Removes a node from the collection by its ID.

        Args:
            node_id: The ID of the node to remove.
        """
        idx = self._expect_present(node_id)
        self.nodes.pop(idx)
        self._pos.pop(node_id)

        # Update positions of all nodes after the removed node
        for id_, pos in list(self._pos.items()):
            if pos > idx:
                self._pos[id_] = pos - 1

        return self

    def rename(self, old_id: str, new_id: str) -> MCFNodes:
        """Renames a node in place, keeping the lookup index consistent.

        Args:
            old_id: The current ID of the node.
            new_id: The ID to give it.

        Raises:
            ValueError: If no node has ``old_id``, or if ``new_id`` is already taken.
        """
        idx = self._expect_present(old_id)
        if new_id in self._pos:
            raise ValueError(f"Node '{new_id}' already exists.")

        self.nodes[idx].Node = new_id
        self._pos.pop(old_id)
        self._pos[new_id] = idx

        return self

    def export_to_mcf_file(
        self, file_path: str | PathLike, *, override: bool = True
    ) -> MCFNodes:
        """Exports the MCF nodes to a file.

        Args:
            file_path: The path of the file to which to export.
            override: If True, overwrite the file if it exists. If False, append to the file.
        """
        mode = "w" if override else "a"

        with open(file_path, mode) as f:
            for node in self.nodes:
                f.write(node.mcf)

        return self
