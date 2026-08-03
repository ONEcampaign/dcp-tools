from typing import Literal

from dcp_tools.custom_data.models.common import Dcid, QuotedStr
from dcp_tools.custom_data.models.mcf import Node


class SourceNode(Node):
    """Represents a Data Commons Source node.

    Attributes:
        # Inherited from Node
        dcid: Identifier for the Node (minted as ``dcid:source/<name>``).
        name: The human-readable name for the Node.
        description: Optional human-readable description.

        # Source-specific
        type_of: Fixed type indicating this is a Source (``dcid:Source``).
        url: URL of the data source.
        license: Optional license information.
        is_part_of: Optional DCID of a parent source.
    """

    type_of: Literal["dcid:Source"] = "dcid:Source"
    url: QuotedStr | None = None
    license: QuotedStr | None = None
    is_part_of: Dcid | None = None


class ProvenanceNode(Node):
    """Represents a Data Commons Provenance node.

    Attributes:
        # Inherited from Node
        dcid: Identifier for the Node (minted as ``dcid:provenance/<name>``).
        name: The human-readable name for the Node.
        description: Optional human-readable description.

        # Provenance-specific
        type_of: Fixed type indicating this is a Provenance (``dcid:Provenance``).
        url: URL of the provenance dataset.
        source: DCID of the parent Source node.
        license: Optional license information.
        license_type: Optional license type.
        last_data_refresh_date: Optional date of last data refresh.
        next_data_refresh_date: Optional date of next expected data refresh.
        next_source_release_date: Optional date of next source release.
        source_release_frequency: Optional frequency of source releases.
        earliest_observation_date: Optional earliest observation date in the dataset.
        latest_observation_date: Optional latest observation date in the dataset.
        curator: Optional curator of the dataset.
        is_part_of: Optional DCID of a parent provenance.
    """

    type_of: Literal["dcid:Provenance"] = "dcid:Provenance"
    url: QuotedStr | None = None
    source: Dcid | None = None
    license: QuotedStr | None = None
    license_type: QuotedStr | None = None
    last_data_refresh_date: QuotedStr | None = None
    next_data_refresh_date: QuotedStr | None = None
    next_source_release_date: QuotedStr | None = None
    source_release_frequency: QuotedStr | None = None
    earliest_observation_date: QuotedStr | None = None
    latest_observation_date: QuotedStr | None = None
    curator: QuotedStr | None = None
    is_part_of: Dcid | None = None
