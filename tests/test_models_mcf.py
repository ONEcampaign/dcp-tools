import pytest

from dcp_tools.custom_data.models.mcf import MCFNode, MCFNodes


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
