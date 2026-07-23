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
        shortDisplayName: Optional human-readable short name for display.
        subClassOf: Optional DCID indicating the 'parent' Node class.

        # Additional Attributes specific to StatisticalVariable
        statType: Type of statistical measurement represented by the variable.
        typeOf: Fixed type indicating this is a StatisticalVariable.
        memberOf: Optional DCID indicating group membership.
        relevantVariable: Optional DCID of a related variable.
        searchDescription: Optional descriptions enhancing NL search capabilities.
        populationType: Optional DCID of the population entity type being measured.
        measuredProperty: Optional DCID of the property being measured.
        measurementQualifier: Optional qualifier describing measurement specifics.
        measurementDenominator: Optional denominator for ratio-type statistical measures.
        footnote: Optional footnotes providing additional context or information.
        observationProperties: Optional observation properties for multi-entity data.
    """

    statType: StatType | None = StatType.MEASURED_VALUE
    typeOf: Literal["dcid:StatisticalVariable"] = "dcid:StatisticalVariable"
    memberOf: GroupDcidOrListGroupDcid | None = None
    relevantVariable: DcidOrListDcid | None = None
    searchDescription: QuotedStrListOrStr | None = None
    populationType: Dcid | None = None
    measuredProperty: Dcid | None = None
    measurementQualifier: Dcid | None = None
    measurementDenominator: Dcid | None = None
    footnote: QuotedStrListOrStr | None = None
    observationProperties: DcidOrListDcid | None = None


class StatVarGroupNode(Node):
    """Represents a Statistical Variable Group node in MCF.

    Attributes:
        # Additional Attributes specific to StatVarGroup
        dcid: Node identifier, must contain '/g'.
        typeOf: Fixed type indicating this is a StatVarGroup.
        specializationOf: DCID of the parent group, must start with 'dcid:' and contain 'g/'.

         # Inherits from Node
        name: The human-readable name for the Node.
        dcid: Optional DCID for uniquely identifying the Node.
        description: Optional human-readable description.
        provenance: Optional provenance information.
        shortDisplayName: Optional human-readable short name for display.
        subClassOf: Optional DCID indicating the 'parent' Node class.
    """

    dcid: GroupDcid
    typeOf: Literal["dcid:StatVarGroup"] = "dcid:StatVarGroup"
    specializationOf: GroupDcid


class StatVarPeerGroupNode(Node):
    """Represents a Statistical Variable Peer Group node in MCF.
    A StatVarPeerGroup represents a group of StatisticalVariable nodes that are comparable peers.

    Attributes:
        # Additional Attributes specific to StatVarPeerGroup
        dcid: Node identifier, must contain '/svpg'.
        typeOf: Fixed type indicating this is a StatVarPeerGroup.
        member: DCID of the parent group, must start with 'dcid:' and contain 'g/'.

         # Inherits from Node
        name: The human-readable name for the Node.
        description: Optional human-readable description.
        provenance: Optional provenance information.
        shortDisplayName: Optional human-readable short name for display.
        subClassOf: Optional DCID indicating the 'parent' Node class.
    """

    dcid: PeerGroupDcid
    typeOf: Literal["dcid:StatVarPeerGroup"] = "dcid:StatVarPeerGroup"
    member: DcidOrListDcid
