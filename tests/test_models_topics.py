import pytest
from pydantic import ValidationError

from dcp_tools.custom_data.models.topics import TopicMCFNode

# relevantVariable is DcidOrListDcid | GroupDcidOrListGroupDcid | TopicDcidOrListTopicDcid.
# Only DcidOrListDcid was fixed for #126 (see models/common.py); the other two still use
# PlainValidator, so there is no whitespace-rejection test here — a value the DcidOrListDcid
# branch would reject can still validate via the still-permissive Group/Topic branches.


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
