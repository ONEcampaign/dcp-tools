from typing import Literal

from dcp_tools.custom_data.models.common import DcidOrListDcid, TopicDcid
from dcp_tools.custom_data.models.mcf import Node


class TopicNode(Node):
    """Represents a Data Commons Topic node.
    A Topic represents a broad topic in the real-world such as economy, poverty,
    crime, etc. Typically used to associated variables (StatisticalVariable)
    related to a common concept.

    Attributes:
        dcid: Node identifier, must start with 'dcid:' and contain 'topic/'.
        type_of: Fixed type indicating this is a Topic.
        relevant_variable: Variable or list of variables relevant to a topic.
            Contains a list of ordered values. Must start with 'dcid:'. Accepts
            plain StatVar dcids as well as group (``.../g/...``) and topic
            (``.../topic/...``) dcids: both are already valid ``dcid:\\S+`` tokens,
            so DcidOrListDcid covers them without a separate union member.

        Inherits from Node:
            name: The human-readable name for the Node.
            dcid: Optional DCID for uniquely identifying the Node.
            description: Optional human-readable description.
            provenance: Optional provenance information.
            short_display_name: Optional human-readable short name for display.
            sub_class_of: Optional DCID indicating the 'parent' Node class.
    """

    dcid: TopicDcid
    type_of: Literal["dcid:Topic"] = "dcid:Topic"
    relevant_variable: DcidOrListDcid
