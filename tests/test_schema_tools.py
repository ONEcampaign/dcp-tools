from bblocks.datacommons_tools.custom_data.models.mcf import MCFNodes
from bblocks.datacommons_tools.custom_data.models.stat_vars import (
    StatVarMCFNode,
    StatVarGroupMCFNode,
)
from bblocks.datacommons_tools.custom_data.schema_tools import (
    csv_metadata_to_nodes,
    build_stat_var_groups_from_strings,
    to_camelCase,
)


def test_csv_metadata_to_nodes(tmp_path):
    """
    Validates CSV-to-MCF conversion, ignoring columns and custom mappings.
    """
    content = (
        "Node,name,typeOf,extra\n"
        "dcid:n1,Name1,dcid:StatisticalVariable,\n"
        "dcid:n2,Name2,dcid:StatisticalVariable,prop\n"
    )
    csv_path = tmp_path / "test.csv"
    csv_path.write_text(content)

    nodes = csv_metadata_to_nodes(str(csv_path))
    assert len(nodes.nodes) == 2

    nodes_ignore = csv_metadata_to_nodes(str(csv_path), ignore_columns=["extra"])
    for node in nodes_ignore.nodes:
        assert not hasattr(node, "extra")

    mapping = {"extra": "searchDescription"}
    nodes_map = csv_metadata_to_nodes(str(csv_path), column_to_property_mapping=mapping)
    for node in nodes_map.nodes:
        assert hasattr(node, "searchDescription")


def make_sv(member_of: str) -> StatVarMCFNode:
    """Helper to create a StatVarMCFNode with a given memberOf path."""
    return StatVarMCFNode(
        Node="dcid:dummy", name="TestVar", description="", memberOf=member_of
    )


def get_group_nodes(nodes: MCFNodes) -> list[StatVarGroupMCFNode]:
    """Extract all StatVarGroupMCFNode instances from MCFNodes."""
    return [n for n in nodes.nodes if isinstance(n, StatVarGroupMCFNode)]


def get_statvar_nodes(nodes: MCFNodes) -> list[StatVarMCFNode]:
    """Extract all StatVarMCFNode instances from MCFNodes."""
    return [n for n in nodes.nodes if isinstance(n, StatVarMCFNode)]


def test_single_level_group():
    sv = make_sv("Category")
    nodes = MCFNodes(nodes=[sv])

    result = build_stat_var_groups_from_strings(nodes, groups_namespace="example.org")
    groups = get_group_nodes(result)
    assert len(groups) == 1, (
        "Should create exactly one group node for single-level path"
    )

    group = groups[0]
    assert group.Node == "dcid:example.org/g/category"
    assert group.name == "Category"
    assert group.specializationOf == "dcid:dc/g/Root"

    statvars = get_statvar_nodes(result)
    assert statvars[0].memberOf == group.Node


def test_multi_level_group():
    sv = make_sv("A/B/C")
    nodes = MCFNodes(nodes=[sv])

    result = build_stat_var_groups_from_strings(nodes, groups_namespace="ns")
    groups = get_group_nodes(result)

    assert len(groups) == 3
    slug_map = {g.Node.split("/")[-1]: g for g in groups}

    # Check each group's parent linkage
    assert slug_map["A"].specializationOf == "dcid:dc/g/Root"
    assert slug_map["B"].specializationOf == "dcid:ns/g/A"
    assert slug_map["C"].specializationOf == "dcid:ns/g/B"

    # Check StatVar points to deepest
    statvars = get_statvar_nodes(result)
    assert statvars[0].memberOf == "dcid:ns/g/C"


def test_duplicate_paths_do_not_create_duplicates():
    sv1 = make_sv("X/Y")
    sv2 = make_sv("X/Y/Z")
    nodes = MCFNodes(nodes=[sv1, sv2])

    result = build_stat_var_groups_from_strings(nodes, groups_namespace="ns2")
    groups = get_group_nodes(result)
    # Expect three unique group nodes: X, Y, Z
    assert len(groups) == 3
    slugs = sorted(g.Node for g in groups)
    assert "dcid:ns2/g/X" in slugs
    assert "dcid:ns2/g/Y" in slugs
    assert "dcid:ns2/g/Z" in slugs


def test_to_camelcase_multi_word():
    assert (
        to_camelCase("Official Development Assistance")
        == "officialDevelopmentAssistance"
    )


def test_to_camelcase_all_uppercase_preserved():
    assert to_camelCase("ODA") == "ODA"
    assert to_camelCase("DAC1") == "DAC1"


def test_to_camelcase_returns_already_camel():
    assert to_camelCase("alreadyCamel") == "alreadyCamel"


def test_to_camelcase_colon_comma_replacement():
    assert to_camelCase("GDP: PPP, Constant 2017 USD") == "gdp_Ppp_Constant2017Usd"
