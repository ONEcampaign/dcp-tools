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
        license_type: Optional DCID of the license the data is published under.
        license_attribution: Optional attribution text required by the license.
        is_part_of: Optional DCID of a parent source.
    """

    type_of: Literal["dcid:Source"] = "dcid:Source"
    url: QuotedStr | None = None
    license: QuotedStr | None = None
    license_type: Dcid | None = None
    license_attribution: QuotedStr | None = None
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
        url: Optional URL of the provenance landing page.
        source: DCID of the parent Source node.
        source_data_url: Optional URL of the source data.
        license: Optional license information.
        license_type: Optional DCID of the license the data is published under.
        license_attribution: Optional attribution text required by the license.
        last_data_refresh_date: Optional date of last data refresh.
        next_data_refresh_date: Optional date of next expected data refresh.
        imported_source_release_date: Optional release date of the imported source data.
        next_source_release_date: Optional date of next source release.
        source_release_frequency: Optional frequency of source releases.
        earliest_observation_date: Optional earliest observation date in the dataset.
        latest_observation_date: Optional latest observation date in the dataset.
        curator: Optional DCID of the curator of the dataset.
        is_part_of: Optional DCID of a parent provenance.
    """

    type_of: Literal["dcid:Provenance"] = "dcid:Provenance"
    url: QuotedStr | None = None
    source: Dcid | None = None
    source_data_url: QuotedStr | None = None
    license: QuotedStr | None = None
    license_type: Dcid | None = None
    license_attribution: QuotedStr | None = None
    last_data_refresh_date: QuotedStr | None = None
    next_data_refresh_date: QuotedStr | None = None
    imported_source_release_date: QuotedStr | None = None
    next_source_release_date: QuotedStr | None = None
    source_release_frequency: QuotedStr | None = None
    earliest_observation_date: QuotedStr | None = None
    latest_observation_date: QuotedStr | None = None
    curator: Dcid | None = None
    is_part_of: Dcid | None = None
