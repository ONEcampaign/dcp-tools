import pytest
from pydantic import ValidationError

from dcp_tools.custom_data.models.topics import TopicNode
from dcp_tools.custom_data.schema_tools import csv_metadata_to_nodes

# relevantVariable collapsed to plain DcidOrListDcid in #131. The group and topic members of
# the old union each layered an extra pattern on top of Dcid, so every value they accept, Dcid
# accepts too, and the three-member union was exactly DcidOrListDcid once all three enforced
# their patterns.
# Unlike before #131, a value DcidOrListDcid rejects is now rejected outright (there is no
# more-permissive Group/Topic branch left to fall back on).


def test_topic_relevant_variable_accepts_bare_statvar_dcid():
    """A bare token matches the plain-Dcid branch and is minted to a plain dcid
    (regression for #126: this used to pass through unvalidated)."""
    node = TopicNode(dcid="dcid:topic/T", name="Topic", relevant_variable="myVariable")
    assert node.relevant_variable == "dcid:myVariable"


def test_topic_relevant_variable_accepts_group_dcid():
    node = TopicNode(dcid="dcid:topic/T", name="Topic", relevant_variable="g/MyGroup")
    assert node.relevant_variable == "dcid:g/MyGroup"


def test_topic_relevant_variable_accepts_topic_dcid():
    node = TopicNode(
        dcid="dcid:topic/T", name="Topic", relevant_variable="topic/OtherTopic"
    )
    assert node.relevant_variable == "dcid:topic/OtherTopic"


def test_topic_relevant_variable_accepts_list():
    node = TopicNode(
        dcid="dcid:topic/T",
        name="Topic",
        relevant_variable=["varOne", "varTwo"],
    )
    assert node.relevant_variable == ["dcid:varOne", "dcid:varTwo"]
    assert "relevantVariable: dcid:varOne, dcid:varTwo" in node.to_mcf()


def test_topic_node_rejects_missing_slug():
    with pytest.raises(ValidationError):
        TopicNode(dcid="dcid:NotATopic", name="Topic", relevant_variable="var")


def test_topic_node_rejects_missing_dcid_prefix():
    """Regression for #134: a bare 'topic/x' used to validate and reach the MCF
    unprefixed, since the old hand-rolled pattern checked for the 'topic/' segment
    but never required the 'dcid:' prefix."""
    with pytest.raises(ValidationError):
        TopicNode(dcid="topic/x", name="Topic", relevant_variable="var")


def test_topic_node_accepts_dcid_prefixed_slug():
    node = TopicNode(dcid="dcid:topic/x", name="Topic", relevant_variable="var")
    assert node.dcid == "dcid:topic/x"


def test_topic_node_rejects_whitespace_bearing_token():
    with pytest.raises(ValidationError):
        TopicNode(dcid="dcid:topic/ x", name="Topic", relevant_variable="var")


def test_topic_csv_conversion_rejects_bare_node(tmp_path):
    """The rule holds on the path users actually take.

    `csv_metadata_to_nodes(node_type="Topic")` is the only way to build a Topic, and
    it backs the `csv2mcf --node-type Topic` CLI command. Constructing the model
    directly, as the tests above do, is not how a bare `Node` reaches the MCF.
    """
    csv_path = tmp_path / "topics.csv"
    csv_path.write_text("Node,name,relevantVariable\ntopic/x,T,dcid:v\n")

    with pytest.raises(ValidationError):
        csv_metadata_to_nodes(str(csv_path), node_type="Topic")

    csv_path.write_text("Node,name,relevantVariable\ndcid:topic/x,T,dcid:v\n")
    nodes = csv_metadata_to_nodes(str(csv_path), node_type="Topic")

    assert nodes.nodes[0].dcid == "dcid:topic/x"
    assert "Node: dcid:topic/x\n" in nodes.nodes[0].to_mcf()


def test_topic_relevant_variable_rejects_whitespace_bearing_token():
    """Regression for #131: before the union collapsed to plain DcidOrListDcid, a
    value DcidOrListDcid rejected could still validate via the more-permissive
    Group/Topic branches (which used PlainValidator and never enforced a pattern)."""
    with pytest.raises(ValidationError):
        TopicNode(dcid="dcid:topic/T", name="Topic", relevant_variable="has space")
