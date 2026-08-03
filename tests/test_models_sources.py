from dcp_tools.custom_data.models.sources import ProvenanceNode, SourceNode


def test_source_to_mcf():
    node = SourceNode(
        dcid="dcid:MySource",
        name="My Source",
        description="Description of My Source",
        url="https://example.com",
        license="https://example.com/license",
        is_part_of="dcid:ParentSource",
    )

    assert node.to_mcf() == (
        "Node: dcid:MySource\n"
        'name: "My Source"\n'
        "typeOf: dcid:Source\n"
        'description: "Description of My Source"\n'
        'url: "https://example.com"\n'
        'license: "https://example.com/license"\n'
        "isPartOf: dcid:ParentSource\n"
        "\n"
    )


def test_provenance_to_mcf():
    node = ProvenanceNode(
        dcid="dcid:MyProvenance",
        name="My Provenance",
        description="Description of My Provenance",
        url="https://example.com",
        source="dcid:MySource",
        license="https://example.com/license",
        license_type="dcid:MyLicenseType",
        last_data_refresh_date="2026-01-01",
        next_data_refresh_date="2026-01-02",
        next_source_release_date="2026-01-03",
        source_release_frequency="P1Y",
        earliest_observation_date="2026-01-04",
        latest_observation_date="2026-01-05",
        curator="dcid:MyOrganisation",
        is_part_of="dcid:MyDataset",
    )

    assert node.to_mcf() == (
        "Node: dcid:MyProvenance\n"
        'name: "My Provenance"\n'
        "typeOf: dcid:Provenance\n"
        'description: "Description of My Provenance"\n'
        'url: "https://example.com"\n'
        "source: dcid:MySource\n"
        'license: "https://example.com/license"\n'
        'licenseType: "dcid:MyLicenseType"\n'
        'lastDataRefreshDate: "2026-01-01"\n'
        'nextDataRefreshDate: "2026-01-02"\n'
        'nextSourceReleaseDate: "2026-01-03"\n'
        'sourceReleaseFrequency: "P1Y"\n'
        'earliestObservationDate: "2026-01-04"\n'
        'latestObservationDate: "2026-01-05"\n'
        'curator: "dcid:MyOrganisation"\n'
        "isPartOf: dcid:MyDataset\n"
        "\n"
    )
