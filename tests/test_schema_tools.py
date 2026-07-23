import pytest

from dcp_tools.custom_data.models.mcf import MCFNodes
from dcp_tools.custom_data.models.stat_vars import (
    StatVarGroupMCFNode,
    StatVarMCFNode,
)
from dcp_tools.custom_data.schema_tools import (
    csv_metadata_to_nodes,
    resolve_group_paths,
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


def get_group_nodes(nodes: MCFNodes) -> list[StatVarGroupMCFNode]:
    """Extract all StatVarGroupMCFNode instances from MCFNodes."""
    return [n for n in nodes.nodes if isinstance(n, StatVarGroupMCFNode)]


def get_statvar_nodes(nodes: MCFNodes) -> list[StatVarMCFNode]:
    """Extract all StatVarMCFNode instances from MCFNodes."""
    return [n for n in nodes.nodes if isinstance(n, StatVarMCFNode)]


def test_single_level_group():
    resolved, groups = resolve_group_paths(["Category"], group_namespace="example.org")

    assert len(groups) == 1, (
        "Should create exactly one group node for single-level path"
    )
    group = groups[0]
    assert group.dcid == "dcid:example.org/g/category"
    assert group.name == "Category"
    assert group.specializationOf == "dcid:dc/g/Root"

    assert resolved["Category"] == group.dcid


def test_multi_level_group():
    resolved, groups = resolve_group_paths(["A/B/C"], group_namespace="ns")

    assert len(groups) == 3
    slug_map = {g.dcid.split("/")[-1]: g for g in groups}

    # Check each group's parent linkage
    assert slug_map["A"].specializationOf == "dcid:dc/g/Root"
    assert slug_map["B"].specializationOf == "dcid:ns/g/A"
    assert slug_map["C"].specializationOf == "dcid:ns/g/B"

    # Check the path resolves to the deepest group
    assert resolved["A/B/C"] == "dcid:ns/g/C"


def test_duplicate_paths_do_not_create_duplicates():
    resolved, groups = resolve_group_paths(["X/Y", "X/Y/Z"], group_namespace="ns2")

    # Expect three unique group nodes: X, Y, Z
    assert len(groups) == 3
    slugs = sorted(g.dcid for g in groups)
    assert "dcid:ns2/g/X" in slugs
    assert "dcid:ns2/g/Y" in slugs
    assert "dcid:ns2/g/Z" in slugs

    assert resolved["X/Y"] == "dcid:ns2/g/Y"
    assert resolved["X/Y/Z"] == "dcid:ns2/g/Z"


def test_csv_metadata_to_nodes_parse_groups(tmp_path):
    """
    Full-pipeline check: StatVars keep CSV order, group nodes come after in
    first-seen order, and each StatVar's memberOf is rewritten to the resolved
    group dcid.
    """
    content = (
        "Node,name,typeOf,memberOf\n"
        "dcid:n1,Name1,dcid:StatisticalVariable,Economic/Employment\n"
        "dcid:n2,Name2,dcid:StatisticalVariable,Economic/Health\n"
    )
    csv_path = tmp_path / "test.csv"
    csv_path.write_text(content)

    nodes = csv_metadata_to_nodes(
        str(csv_path), parse_groups=True, group_namespace="ns"
    )

    assert [n.dcid for n in nodes.nodes] == [
        "dcid:n1",
        "dcid:n2",
        "dcid:ns/g/economic",
        "dcid:ns/g/employment",
        "dcid:ns/g/health",
    ]

    statvars = get_statvar_nodes(nodes)
    assert statvars[0].memberOf == "dcid:ns/g/employment"
    assert statvars[1].memberOf == "dcid:ns/g/health"


def test_resolve_group_paths_cleans_raw_path():
    """Covers the path-cleaning contract in the docstring: a leading '-' is
    stripped, '/' and whitespace are stripped from both ends, and empty segments
    (from doubled or edge slashes) are dropped."""
    resolved, groups = resolve_group_paths(
        ["-Economic// Employment / "], group_namespace="ns"
    )

    assert len(groups) == 2
    slugs = [g.dcid for g in groups]
    assert slugs == ["dcid:ns/g/economic", "dcid:ns/g/employment"]
    assert resolved["-Economic// Employment / "] == "dcid:ns/g/employment"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Economic/\t", ["dcid:ns/g/economic"]),
        ("Economic/\t/Health", ["dcid:ns/g/economic", "dcid:ns/g/health"]),
        ("Economic/Health\n", ["dcid:ns/g/economic", "dcid:ns/g/health"]),
        ("Eco\nnomic", ["dcid:ns/g/economic"]),
    ],
)
def test_resolve_group_paths_drops_whitespace_only_segments(raw, expected):
    """A segment that is only whitespace mints no group.

    `.strip("/ ")` does not remove a tab or newline, so such a segment used to
    survive and `to_camelCase` reduced it to an empty slug, minting a group whose
    dcid ends in a bare "g/". These paths reached the resolver through
    `StatVarMCFNode(memberOf=...)` before groups were resolved ahead of node
    construction, and were cleaned on the way in.
    """
    resolved, groups = resolve_group_paths([raw], group_namespace="ns")

    assert [g.dcid for g in groups] == expected
    assert resolved[raw] == expected[-1]


def test_resolve_group_paths_omits_path_with_no_segments():
    """A path that cleans down to nothing (e.g. just '-' or '/') mints no group
    and is omitted from the resolved mapping."""
    resolved, groups = resolve_group_paths(["-", "/"], group_namespace="ns")

    assert resolved == {}
    assert groups == []


def test_csv_metadata_to_nodes_parse_groups_without_memberof_column_raises(tmp_path):
    """parse_groups=True with no `memberOf` column is a clear ValueError, not a crash."""
    content = "Node,name,typeOf\ndcid:n1,Name1,dcid:StatisticalVariable\n"
    csv_path = tmp_path / "test.csv"
    csv_path.write_text(content)

    with pytest.raises(ValueError, match="memberOf"):
        csv_metadata_to_nodes(str(csv_path), parse_groups=True, group_namespace="ns")


def test_csv_metadata_to_nodes_parse_groups_leaves_missing_memberof_unset(tmp_path):
    """A row with a missing memberOf is left unset rather than crashing."""
    content = (
        "Node,name,typeOf,memberOf\n"
        "dcid:n1,Name1,dcid:StatisticalVariable,Economic/Employment\n"
        "dcid:n2,Name2,dcid:StatisticalVariable,\n"
    )
    csv_path = tmp_path / "test.csv"
    csv_path.write_text(content)

    nodes = csv_metadata_to_nodes(
        str(csv_path), parse_groups=True, group_namespace="ns"
    )
    statvars = get_statvar_nodes(nodes)

    assert statvars[0].memberOf == "dcid:ns/g/employment"
    assert statvars[1].memberOf is None


def test_csv_metadata_to_nodes_parse_groups_leaves_segmentless_memberof_unset(tmp_path):
    """A memberOf that cleans down to nothing ('-', '/') leaves the node ungrouped,
    the same as a blank cell.

    Keeping the raw value instead would hand '-' to a memberOf that now enforces the
    group pattern, aborting the whole call over a row that carries no group at all.
    """
    content = (
        "Node,name,typeOf,memberOf\n"
        "dcid:n1,Name1,dcid:StatisticalVariable,-\n"
        "dcid:n2,Name2,dcid:StatisticalVariable,/\n"
        "dcid:n3,Name3,dcid:StatisticalVariable,Economic/Employment\n"
    )
    csv_path = tmp_path / "test.csv"
    csv_path.write_text(content)

    nodes = csv_metadata_to_nodes(
        str(csv_path), parse_groups=True, group_namespace="ns"
    )
    statvars = get_statvar_nodes(nodes)

    assert statvars[0].memberOf is None
    assert statvars[1].memberOf is None
    assert statvars[2].memberOf == "dcid:ns/g/employment"


def test_csv_metadata_to_nodes_parse_groups_remove_works_on_group_node(tmp_path):
    """Regression test: csv_metadata_to_nodes used to append group nodes directly to
    `nodes.nodes`, bypassing `MCFNodes.add` and leaving `_pos` stale. `.remove()` (which
    looks the node up via `_pos`) on a group node from a parse_groups=True result must
    work — the same class of index bug #126 fixed in `rename_variable`."""
    content = (
        "dcid,name,typeOf,memberOf\n"
        "dcid:n1,Name1,dcid:StatisticalVariable,Economic/Employment\n"
    )
    csv_path = tmp_path / "test.csv"
    csv_path.write_text(content)

    nodes = csv_metadata_to_nodes(
        str(csv_path), parse_groups=True, group_namespace="ns"
    )

    nodes.remove("dcid:ns/g/employment")
    assert [n.dcid for n in nodes.nodes] == ["dcid:n1", "dcid:ns/g/economic"]
    # The index was kept consistent, not merely the list.
    assert nodes._expect_present("dcid:ns/g/economic") == 1


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
