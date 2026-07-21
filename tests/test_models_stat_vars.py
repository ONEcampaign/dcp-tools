import pandas as pd
import pytest
from pydantic import ValidationError

from dcp_tools.custom_data.models.stat_vars import (
    StatVarMCFNode,
    StatVarPeerGroupMCFNode,
)
from dcp_tools.custom_data.schema_tools import _rows_to_stat_var_nodes


def test_search_description_serialization_str_and_list():
    sv_str = StatVarMCFNode(Node="dcid:n1", name="Var", searchDescription="A")
    assert 'searchDescription: "A"' in sv_str.mcf

    sv_str = StatVarMCFNode(
        Node="dcid:n1",
        name="Var",
        searchDescription=["A string, or not", "B string, other"],
    )
    assert 'searchDescription: "A string, or not","B string, other"' in sv_str.mcf

    sv_list = StatVarMCFNode(Node="dcid:n2", name="Var", searchDescription=["A", "B"])
    assert 'searchDescription: "A","B"' in sv_list.mcf


def test_statvarnode_strips_whitespace_and_linebreaks():
    sv = StatVarMCFNode(
        Node="dcid:n1\n",
        name="Var \n",
        searchDescription=["First line\n", "Second line "],
    )
    assert sv.Node == "dcid:n1"
    assert sv.name == "Var"
    assert sv.searchDescription == ["First line", "Second line"]


def test_statvarnode_omits_observation_properties_by_default():
    sv = StatVarMCFNode(
        Node="dcid:n1",
        name="Var",
    )
    assert "observationProperties" not in sv.mcf


def test_statvarnode_serializes_observation_properties_multi_entity():
    sv = StatVarMCFNode(
        Node="dcid:n1",
        name="Var",
        observationProperties=["dcid:source", "dcid:destination"],
    )
    assert "observationProperties: dcid:source, dcid:destination" in sv.mcf


def test_rows_to_stat_var_nodes_parses_comma_separated():
    df = pd.DataFrame(
        {"Node": ["dcid:n3"], "name": ["Var"], "searchDescription": ["A, B"]}
    )
    nodes = _rows_to_stat_var_nodes(df)
    mcf = nodes.nodes[0].mcf
    assert 'searchDescription: "A","B"' in mcf


def test_rows_to_stat_var_nodes_parses_spreadsheet_lists():
    df = pd.DataFrame(
        {
            "Node": ["dcid:n3"],
            "name": ["Var"],
            "searchDescription": ['["A list, comma", "second element"]'],
        }
    )
    nodes = _rows_to_stat_var_nodes(df)
    mcf = nodes.nodes[0].mcf
    assert 'searchDescription: "A list, comma","second element"' in mcf


def test_rows_to_stat_var_nodes_parses_spreadsheet_lists_no_quotes():
    df = pd.DataFrame(
        {
            "Node": ["dcid:n3"],
            "name": ["Var"],
            "memberOf": ['["dcid:oneId", "dcid:twoId"]'],
        }
    )
    nodes = _rows_to_stat_var_nodes(df)
    mcf = nodes.nodes[0].mcf
    assert "memberOf: dcid:oneId, dcid:twoId" in mcf


# --- observationProperties / relevantVariable normalize bare tokens (regression for #126) ---
#
# Both are DcidOrListDcid. Before the fix, PlainValidator bypassed the dcid: pattern
# entirely, so a bare token like "originCountry" landed in the MCF unprefixed.


def test_observation_properties_normalizes_bare_scalar_and_list():
    sv = StatVarMCFNode(
        Node="dcid:n1", name="Var", observationProperties="originCountry"
    )
    assert sv.observationProperties == "dcid:originCountry"

    sv_list = StatVarMCFNode(
        Node="dcid:n1",
        name="Var",
        observationProperties=["originCountry", "destinationCountry"],
    )
    assert sv_list.observationProperties == [
        "dcid:originCountry",
        "dcid:destinationCountry",
    ]
    assert (
        "observationProperties: dcid:originCountry, dcid:destinationCountry"
        in sv_list.mcf
    )


def test_observation_properties_rejects_whitespace_bearing_token():
    with pytest.raises(ValidationError):
        StatVarMCFNode(Node="dcid:n1", name="Var", observationProperties="has space")


def test_relevant_variable_normalizes_bare_scalar_and_list():
    sv = StatVarMCFNode(Node="dcid:n1", name="Var", relevantVariable="otherVar")
    assert sv.relevantVariable == "dcid:otherVar"

    sv_list = StatVarMCFNode(
        Node="dcid:n1", name="Var", relevantVariable=["one", "two"]
    )
    assert sv_list.relevantVariable == ["dcid:one", "dcid:two"]


def test_relevant_variable_rejects_whitespace_bearing_token():
    with pytest.raises(ValidationError):
        StatVarMCFNode(Node="dcid:n1", name="Var", relevantVariable="has space")


# --- member on StatVarPeerGroupMCFNode is DcidOrListDcid, same normalization ---


def test_peer_group_member_normalizes_bare_scalar_and_list():
    node = StatVarPeerGroupMCFNode(
        Node="dcid:svpg/x", name="Peers", member=["varOne", "varTwo"]
    )
    assert node.member == ["dcid:varOne", "dcid:varTwo"]
    assert "member: dcid:varOne, dcid:varTwo" in node.mcf


def test_peer_group_member_rejects_whitespace_bearing_token():
    with pytest.raises(ValidationError):
        StatVarPeerGroupMCFNode(Node="dcid:svpg/x", name="Peers", member="has space")
