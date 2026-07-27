from enum import StrEnum
from typing import Literal

from dcp_tools.custom_data.models.common import (
    Dcid,
    DcidOrListDcid,
    GroupDcid,
    GroupDcidOrListGroupDcid,
    PeerGroupDcid,
    QuotedStrListOrStr,
)
from dcp_tools.custom_data.models.mcf import Node


class StatType(StrEnum):
    """Enumeration of statistical value types used in Data Commons."""

    MEASURED_VALUE = "dcid:measuredValue"
    MIN_VALUE = "dcid:minValue"
    MAX_VALUE = "dcid:maxValue"
    MEAN_VALUE = "dcid:meanValue"
    MEDIAN_VALUE = "dcid:medianValue"
    SUM_VALUE = "dcid:sumValue"
    VARIANCE_VALUE = "dcid:varianceValue"
    MARGIN_OF_ERROR = "dcid:marginOfError"
    STANDARD_ERROR = "dcid:stdErr"


class StatVarNode(Node):
    """Represents a Statistical Variable node in MCF.

    Attributes:
        # Inherited from Node
        dcid: Identifier for the Node.
        name: The human-readable name for the Node.
        description: Optional human-readable description.
        provenance: Optional provenance information.
        short_display_name: Optional human-readable short name for display.
        sub_class_of: Optional DCID indicating the 'parent' Node class.

        # Additional Attributes specific to StatisticalVariable
        stat_type: Type of statistical measurement represented by the variable.
        type_of: Fixed type indicating this is a StatisticalVariable.
        member_of: Optional DCID indicating group membership.
        relevant_variable: Optional DCID of a related variable.
        search_description: Optional descriptions enhancing NL search capabilities.
        population_type: Optional DCID of the population entity type being measured.
        measured_property: Optional DCID of the property being measured.
        measurement_qualifier: Optional qualifier describing measurement specifics.
        measurement_denominator: Optional denominator for ratio-type statistical measures.
        footnote: Optional footnotes providing additional context or information.
        observation_properties: Optional observation properties for multi-entity data.
    """

    stat_type: StatType | None = StatType.MEASURED_VALUE
    type_of: Literal["dcid:StatisticalVariable"] = "dcid:StatisticalVariable"
    member_of: GroupDcidOrListGroupDcid | None = None
    relevant_variable: DcidOrListDcid | None = None
    search_description: QuotedStrListOrStr | None = None
    population_type: Dcid | None = None
    measured_property: Dcid | None = None
    measurement_qualifier: Dcid | None = None
    measurement_denominator: Dcid | None = None
    footnote: QuotedStrListOrStr | None = None
    observation_properties: DcidOrListDcid | None = None


class StatVarGroupNode(Node):
    """Represents a Statistical Variable Group node in MCF.

    Attributes:
        # Additional Attributes specific to StatVarGroup
        dcid: Node identifier, must contain '/g'.
        type_of: Fixed type indicating this is a StatVarGroup.
        specialization_of: DCID of the parent group, must start with 'dcid:' and contain 'g/'.

         # Inherits from Node
        name: The human-readable name for the Node.
        dcid: Optional DCID for uniquely identifying the Node.
        description: Optional human-readable description.
        provenance: Optional provenance information.
        short_display_name: Optional human-readable short name for display.
        sub_class_of: Optional DCID indicating the 'parent' Node class.
    """

    dcid: GroupDcid
    type_of: Literal["dcid:StatVarGroup"] = "dcid:StatVarGroup"
    specialization_of: GroupDcid


class StatVarPeerGroupNode(Node):
    """Represents a Statistical Variable Peer Group node in MCF.
    A StatVarPeerGroup represents a group of StatisticalVariable nodes that are comparable peers.

    Attributes:
        # Additional Attributes specific to StatVarPeerGroup
        dcid: Node identifier, must contain '/svpg'.
        type_of: Fixed type indicating this is a StatVarPeerGroup.
        member: DCID of the parent group, must start with 'dcid:' and contain 'g/'.

         # Inherits from Node
        name: The human-readable name for the Node.
        description: Optional human-readable description.
        provenance: Optional provenance information.
        short_display_name: Optional human-readable short name for display.
        sub_class_of: Optional DCID indicating the 'parent' Node class.
    """

    dcid: PeerGroupDcid
    type_of: Literal["dcid:StatVarPeerGroup"] = "dcid:StatVarPeerGroup"
    member: DcidOrListDcid
