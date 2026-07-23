from typing import Literal

from dcp_tools.custom_data.models.common import Dcid, QuotedStr
from dcp_tools.custom_data.models.mcf import MCFNode


class SourceMCFNode(MCFNode):
    """Represents a Source node for MCF.

    Attributes:
        # Inherited from MCFNode
        dcid: Identifier for the Node (minted as ``dcid:source/<name>``).
        name: The human-readable name for the Node.
        description: Optional human-readable description.

        # Source-specific
        typeOf: Fixed type indicating this is a Source (``dcid:Source``).
        url: URL of the data source.
        license: Optional license information.
        isPartOf: Optional DCID of a parent source.
    """

    typeOf: Literal["dcid:Source"] = "dcid:Source"
    url: QuotedStr | None = None
    license: QuotedStr | None = None
    isPartOf: Dcid | None = None


class ProvenanceMCFNode(MCFNode):
    """Represents a Provenance node for MCF.

    Attributes:
        # Inherited from MCFNode
        dcid: Identifier for the Node (minted as ``dcid:provenance/<name>``).
        name: The human-readable name for the Node.
        description: Optional human-readable description.

        # Provenance-specific
        typeOf: Fixed type indicating this is a Provenance (``dcid:Provenance``).
        url: URL of the provenance dataset.
        sourceLink: DCID of the parent Source node.
        license: Optional license information.
        licenseType: Optional license type.
        lastDataRefreshDate: Optional date of last data refresh.
        nextDataRefreshDate: Optional date of next expected data refresh.
        nextSourceReleaseDate: Optional date of next source release.
        sourceReleaseFrequency: Optional frequency of source releases.
        earliestObservationDate: Optional earliest observation date in the dataset.
        latestObservationDate: Optional latest observation date in the dataset.
        curator: Optional curator of the dataset.
        isPartOf: Optional DCID of a parent provenance.
    """

    typeOf: Literal["dcid:Provenance"] = "dcid:Provenance"
    url: QuotedStr | None = None
    sourceLink: Dcid | None = None
    license: QuotedStr | None = None
    licenseType: QuotedStr | None = None
    lastDataRefreshDate: QuotedStr | None = None
    nextDataRefreshDate: QuotedStr | None = None
    nextSourceReleaseDate: QuotedStr | None = None
    sourceReleaseFrequency: QuotedStr | None = None
    earliestObservationDate: QuotedStr | None = None
    latestObservationDate: QuotedStr | None = None
    curator: QuotedStr | None = None
    isPartOf: Dcid | None = None
