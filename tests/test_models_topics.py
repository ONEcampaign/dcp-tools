import pytest
from pydantic import ValidationError

from dcp_tools.custom_data.models.topics import TopicMCFNode

# relevantVariable collapsed to plain DcidOrListDcid in #131. The group and topic members of
# the old union each layered an extra pattern on top of Dcid, so every value they accept, Dcid
# accepts too, and the three-member union was exactly DcidOrListDcid once all three enforced
# their patterns.
# Unlike before #131, a value DcidOrListDcid rejects is now rejected outright (there is no
# more-permissive Group/Topic branch left to fall back on).


def test_topic_relevant_variable_accepts_bare_statvar_dcid():
    """A bare token matches the plain-Dcid branch and is minted to a plain dcid
    (regression for #126: this used to pass through unvalidated)."""
    node = TopicMCFNode(
        Node="dcid:topic/T", name="Topic", relevantVariable="myVariable"
    )
    assert node.relevantVariable == "dcid:myVariable"


def test_topic_relevant_variable_accepts_group_dcid():
    node = TopicMCFNode(Node="dcid:topic/T", name="Topic", relevantVariable="g/MyGroup")
    assert node.relevantVariable == "dcid:g/MyGroup"


def test_topic_relevant_variable_accepts_topic_dcid():
    node = TopicMCFNode(
        Node="dcid:topic/T", name="Topic", relevantVariable="topic/OtherTopic"
    )
    assert node.relevantVariable == "dcid:topic/OtherTopic"


def test_topic_relevant_variable_accepts_list():
    node = TopicMCFNode(
        Node="dcid:topic/T",
        name="Topic",
        relevantVariable=["varOne", "varTwo"],
    )
    assert node.relevantVariable == ["dcid:varOne", "dcid:varTwo"]
    assert "relevantVariable: dcid:varOne, dcid:varTwo" in node.mcf


def test_topic_node_rejects_missing_slug():
    with pytest.raises(ValidationError):
        TopicMCFNode(Node="dcid:NotATopic", name="Topic", relevantVariable="var")


def test_topic_relevant_variable_rejects_whitespace_bearing_token():
    """Regression for #131: before the union collapsed to plain DcidOrListDcid, a
    value DcidOrListDcid rejected could still validate via the more-permissive
    Group/Topic branches (which used PlainValidator and never enforced a pattern)."""
    with pytest.raises(ValidationError):
        TopicMCFNode(Node="dcid:topic/T", name="Topic", relevantVariable="has space")
