import pytest
from pydantic import ValidationError

from dcp_tools.custom_data.models.sources import ProvenanceNode, SourceNode


def test_source_to_mcf():
    node = SourceNode(
        dcid="dcid:MySource",
        name="My Source",
        description="Description of My Source",
        url="https://example.com",
        license="https://example.com/license",
        license_type="dcid:MyLicenseType",
        license_attribution="Data provided by My Source",
        is_part_of="dcid:ParentSource",
    )

    assert node.to_mcf() == (
        "Node: dcid:MySource\n"
        'name: "My Source"\n'
        "typeOf: dcid:Source\n"
        'description: "Description of My Source"\n'
        'url: "https://example.com"\n'
        'license: "https://example.com/license"\n'
        "licenseType: dcid:MyLicenseType\n"
        'licenseAttribution: "Data provided by My Source"\n'
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
        source_data_url="https://example.com/data.csv",
        license="https://example.com/license",
        license_type="dcid:MyLicenseType",
        license_attribution="Data provided by My Source",
        last_data_refresh_date="2026-01-01",
        next_data_refresh_date="2026-01-02",
        imported_source_release_date="2025-12-31",
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
        'sourceDataUrl: "https://example.com/data.csv"\n'
        'license: "https://example.com/license"\n'
        "licenseType: dcid:MyLicenseType\n"
        'licenseAttribution: "Data provided by My Source"\n'
        'lastDataRefreshDate: "2026-01-01"\n'
        'nextDataRefreshDate: "2026-01-02"\n'
        'importedSourceReleaseDate: "2025-12-31"\n'
        'nextSourceReleaseDate: "2026-01-03"\n'
        'sourceReleaseFrequency: "P1Y"\n'
        'earliestObservationDate: "2026-01-04"\n'
        'latestObservationDate: "2026-01-05"\n'
        "curator: dcid:MyOrganisation\n"
        "isPartOf: dcid:MyDataset\n"
        "\n"
    )


def test_provenance_source_data_url_list_writes_one_quoted_value_per_url():
    urls = ["https://example.com/A_D.xlsx", "https://example.com/E_K.xlsx"]
    node = ProvenanceNode(dcid="dcid:MyProvenance", source_data_url=urls)

    expected = ",".join(f'"{url}"' for url in urls)
    assert f"sourceDataUrl: {expected}\n" in node.to_mcf()


def test_provenance_source_data_url_string_is_never_split_on_commas():
    url = "https://example.com/data?ids=1,2"
    node = ProvenanceNode(dcid="dcid:MyProvenance", source_data_url=url)

    assert f'sourceDataUrl: "{url}"\n' in node.to_mcf()


def test_provenance_source_data_url_rejects_empty_list():
    with pytest.raises(ValidationError):
        ProvenanceNode(dcid="dcid:MyProvenance", source_data_url=[])


def test_license_type_and_curator_reject_bare_tokens():
    """Dcid-typed properties must carry the ``dcid:`` prefix."""
    with pytest.raises(ValidationError):
        SourceNode(dcid="dcid:MySource", license_type="CreativeCommonsAttribution4_0")

    with pytest.raises(ValidationError):
        ProvenanceNode(dcid="dcid:MyProvenance", curator="MyOrganisation")
