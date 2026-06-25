from typing import Annotated, Literal

from pydantic import StringConstraints

from dcp_tools.custom_data.models.common import (
    DcidOrListDcid,
    GroupDcidOrListGroupDcid,
    TopicDcidOrListTopicDcid,
)
from dcp_tools.custom_data.models.mcf import MCFNode


class TopicMCFNode(MCFNode):
    """Represents a Topic node as MCF Nodes.
    A Topic represents a broad topic in the real-world such as economy, poverty,
    crime, etc. Typically used to associated variables (StatisticalVariable)
    related to a common concept.

    Attributes:
        Node: Node identifier, must contain '/topic'.
        typeOf: Fixed type indicating this is a Topic.
        relevantVariable: Variable or list of variables relevant to a topic.
            Contains a list of ordered values. Must start with 'dcid:'

        Inherits from MCFNode:
            name: The human-readable name for the Node.
            dcid: Optional DCID for uniquely identifying the Node.
            description: Optional human-readable description.
            provenance: Optional provenance information.
            shortDisplayName: Optional human-readable short name for display.
            subClassOf: Optional DCID indicating the 'parent' Node class.
    """

    Node: Annotated[
        str, StringConstraints(strip_whitespace=True, pattern=r".*topic/.*")
    ]
    typeOf: Literal["dcid:Topic"] = "dcid:Topic"
    relevantVariable: (
        DcidOrListDcid | GroupDcidOrListGroupDcid | TopicDcidOrListTopicDcid
    )
