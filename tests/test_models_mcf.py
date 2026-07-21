import pytest
from pydantic import ValidationError

from dcp_tools.custom_data.models.mcf import MCFNode, MCFNodes
from dcp_tools.custom_data.models.stat_vars import StatType, StatVarMCFNode


def test_mcfnode_mcf_output_order_and_formatting():
    """
    Ensures MCFNode.mcf outputs properties sorted alphabetically
    after 'Node:' line.
    """
    node = MCFNode(
        Node="dcid:TestNode",
        name='"My Name"',
        typeOf="dcid:TypeA",
        description='"Desc"',
    )
    lines = node.mcf.strip().splitlines()
    assert lines[0] == "Node: dcid:TestNode"
    assert lines[1] == 'name: "My Name"'
    assert lines[2] == "typeOf: dcid:TypeA"
    assert lines[3] == 'description: "Desc"'


def test_mcfnode_typeof_accepts_list_and_serializes():
    """
    Accepts a list of DCIDs for typeOf and serializes as CSV.
    """
    node = MCFNode(
        Node="dcid:TestNode", name='"My Name"', typeOf=["dcid:TypeA", "dcid:TypeB"]
    )
    lines = node.mcf.strip().splitlines()
    assert lines[0] == "Node: dcid:TestNode"
    # Field order keeps name before typeOf
    assert lines[2] == "typeOf: dcid:TypeA, dcid:TypeB"


def test_mcfnode_typeof_accepts_comma_string_and_serializes():
    """
    Accepts a comma-delimited string for typeOf and serializes consistently.
    """
    node = MCFNode(
        Node="dcid:TestNode", name='"My Name"', typeOf="dcid:TypeA, dcid:TypeB"
    )
    lines = node.mcf.strip().splitlines()
    assert lines[0] == "Node: dcid:TestNode"
    assert lines[2] == "typeOf: dcid:TypeA, dcid:TypeB"


def test_mcfnode_allows_missing_name_and_serializes_without_it():
    """
    `name` is optional; when omitted it should not appear in MCF output.
    """
    node = MCFNode(Node="dcid:NoNameNode", typeOf="dcid:TypeA")
    lines = node.mcf.strip().splitlines()
    assert lines[0] == "Node: dcid:NoNameNode"
    # With no name, typeOf should be next
    assert lines[1] == "typeOf: dcid:TypeA"
    assert not any(line.startswith("name:") for line in lines)


def test_mcfnode_strips_linebreaks_and_trailing_spaces():
    node = MCFNode(
        Node="dcid:TestNode \n",  # newline and trailing space
        name="My name\n ",
        typeOf="dcid:TypeA \n",
        extra_field="extra value \n",
    )
    assert node.Node == "dcid:TestNode"
    assert node.name == "My name"
    assert node.typeOf == "dcid:TypeA"
    assert node.extra_field == "extra value"


def test_mcfnodes_load_from_file_without_name(tmp_path):
    """
    Loading MCF where a block has no `name` should succeed.
    """
    mcf_text = (
        "Node: dcid:NoName\n"
        "typeOf: dcid:TypeA\n\n"
        "Node: dcid:WithName\n"
        'name: "Some Name"\n'
        "typeOf: dcid:TypeB\n\n"
    )
    path = tmp_path / "nodes.mcf"
    path.write_text(mcf_text)

    nodes = MCFNodes().load_from_mcf_file(str(path))
    assert len(nodes.nodes) == 2
    # First node should have no name, but have typeOf
    first = nodes.nodes[0]
    assert first.Node == "dcid:NoName"
    assert getattr(first, "name", None) is None
    assert first.typeOf == "dcid:TypeA"


def test_mcfnode_typeof_normalizes_bare_token():
    """typeOf is DcidOrListDcid; a bare token is minted to dcid:<token> (regression for #126)."""
    node = MCFNode(Node="dcid:TestNode", typeOf="TypeA")
    assert node.typeOf == "dcid:TypeA"


def test_mcfnode_typeof_rejects_whitespace_bearing_token():
    with pytest.raises(ValidationError):
        MCFNode(Node="dcid:TestNode", typeOf="has space")


def test_mcfnodes_add_override_and_remove():
    """
    Tests adding nodes, override behavior, and removal from MCFNodes.
    """
    nodes = MCFNodes()
    node1 = MCFNode(Node="dcid:n1", name='"First"', typeOf="dcid:T1")
    nodes.add(node1)
    assert nodes._expect_present("dcid:n1") == 0

    # Adding same node without override should error
    node1b = MCFNode(Node="dcid:n1", name='"Second"', typeOf="dcid:T1")
    with pytest.raises(ValueError):
        nodes.add(node1b, override=False)

    # Override replaces existing
    nodes.add(node1b, override=True)
    assert nodes.nodes[0].name == '"Second"'

    # Remove node
    nodes.remove("dcid:n1")
    with pytest.raises(ValueError):
        nodes._expect_present("n1")


# --- validate_assignment (regression tests for #131) ---
#
# MCFNode.model_config gained validate_assignment=True so that the patterns restored on
# the slug-variant types (GroupDcidOrListGroupDcid and friends, see models/common.py) are
# enforced on assignment too, not just on construction.


def test_mcfnode_assignment_is_validated():
    """An invalid value assigned to a pattern-constrained field raises, the same as
    construction would."""
    node = MCFNode(Node="dcid:n1", typeOf="dcid:T1")
    with pytest.raises(ValidationError):
        node.typeOf = "has space"


def test_mcfnode_assignment_cleans_the_assigned_value():
    """A newly-assigned value is cleaned (newlines/trailing spaces stripped) the same
    way construction cleans it, for declared fields and for the extra keys that carry
    arbitrary MCF properties. An uncleaned value would emit a line break mid-node and
    break the MCF file (the bug fixed in v0.0.7, for construction only)."""
    node = MCFNode(Node="dcid:n1", typeOf="dcid:T1")

    node.name = "text\nwith newline  "
    assert node.name == "textwith newline"

    node.customProperty = "extra\nvalue  "
    assert node.customProperty == "extravalue"
    assert "customProperty: extravalue\n" in node.mcf


def test_stat_type_survives_assignment():
    """Regression: with validate_assignment=True, `_strip_whitespace` (a mode="before"
    model validator) reran over the whole field dict on every assignment, including
    fields the assignment did not touch. Because StatType is a StrEnum, the old
    `_clean_value` matched its `isinstance(value, str)` branch and `value.replace(...)`
    returned a plain str, silently degrading the enum member on any unrelated
    assignment. `_clean_value` now leaves Enum members untouched."""
    sv = StatVarMCFNode(Node="dcid:v1")
    assert isinstance(sv.statType, StatType)

    sv.name = "Var"

    assert isinstance(sv.statType, StatType)
    assert sv.statType == StatType.MEASURED_VALUE


def test_mcfnodes_rename_rejected_leaves_index_intact():
    """A rename to a value that fails Node's dcid pattern raises, and leaves the
    node and the lookup index exactly as they were (assignment happens before
    `_pos` is mutated)."""
    nodes = MCFNodes()
    nodes.add(MCFNode(Node="dcid:n1", typeOf="dcid:T1"))

    with pytest.raises(ValidationError):
        nodes.rename("dcid:n1", "not-a-dcid")

    assert nodes.nodes[0].Node == "dcid:n1"
    assert nodes._pos == {"dcid:n1": 0}
