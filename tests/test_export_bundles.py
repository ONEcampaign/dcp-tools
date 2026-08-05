from pathlib import Path

import pandas as pd

from dcp_tools.custom_data.data_management import CustomDataManager

GOLDEN_DIR = Path(__file__).parent / "goldens"


def _get_files_in_bundle(directory: Path) -> set[Path]:
    return {
        path.relative_to(directory) for path in directory.rglob("*") if path.is_file()
    }


def assert_bundle_equal(golden_dir: Path, actual_dir: Path) -> None:
    golden_files = _get_files_in_bundle(golden_dir)
    actual_files = _get_files_in_bundle(actual_dir)
    missing = golden_files - actual_files
    unexpected = actual_files - golden_files
    assert not missing and not unexpected, (
        f"Files missing from export: {missing}\n"
        f"Unexpected files in export: {unexpected}"
    )
    for golden_file in golden_files:
        assert (actual_dir / golden_file).read_text() == (
            golden_dir / golden_file
        ).read_text(), f"{golden_file} differs"


def test_export_bundle_single_entity(tmp_path):
    import_name = "single_entity_import"
    manager = CustomDataManager()
    manager.set_import_name(import_name)
    manager.set_include_input_subdirs(True)
    manager.set_group_stat_vars_by_property(False)
    manager.set_data_download_url(
        ["https://example.org/data/file1.csv", "https://example.org/data/file2.csv"]
    )
    manager.add_vertical_spec(
        verticals=["MyVertical"], population_type="Thing", file_name="verticals.json"
    )
    manager.add_source(
        dcid="MySource",
        name="My Source",
        url="https://mysource.com",
        description="Description for My Source.",
    )
    manager.add_provenance(
        dcid="MyProvenance",
        name="My Provenance",
        url="https://mysource.com/myprovenance",
        source="MySource",
        description="Description for My Provenance.",
    )
    manager.add_variable_group_to_mcf(
        dcid="dcid:one/g/group1", name="Group One", specialization_of="dcid:dc/g/Root"
    )
    manager.add_variable_to_mcf(
        dcid="dcid:TestVar",
        name="Test Var",
        description="Description for Test Var.",
        member_of="dcid:one/g/group1",
        constraint_properties=["age", "gender"],
    )
    manager.add_input_file(
        "subdir/data.csv",
        provenance="MyProvenance",
        data=pd.DataFrame(
            {
                "Var": ["dcid:TestVar"],
                "Country": ["country/FRA"],
                "Year": [2026],
                "Val": [1.0],
            }
        ),
        column_mappings={
            "variable": "Var",
            "observationAbout": "Country",
            "date": "Year",
            "value": "Val",
        },
        observation_properties={
            "unit": "USDollar",
            "measurementMethod": "dcAggregate/Census",
            "customProp": "customValue",
        },
    )
    manager.add_mcf_file("*.mcf", provenance="MyProvenance")

    output_dir = tmp_path / import_name
    output_dir.mkdir(parents=True, exist_ok=True)
    manager.export_all(output_dir)

    assert_bundle_equal((GOLDEN_DIR / import_name), (tmp_path / import_name))


def test_export_bundle_multi_provenance(tmp_path):
    import_name = "multi_provenance_import"
    manager = CustomDataManager()
    manager.set_import_name(import_name)
    manager.add_source(
        dcid="MySource",
        name="My Source",
        url="https://mysource.com",
    )
    manager.add_mcf_file("provenance.mcf", provenance="ProvA")
    manager.add_mcf_file("custom_nodes.mcf", provenance="ProvA")
    manager.add_mcf_file("provenance_b.mcf", provenance="ProvB")
    manager.add_mcf_file("nodes_b.mcf", provenance="ProvB")
    manager.add_provenance(
        dcid="ProvA",
        name="Prov A",
        url="https://mysource.com/a",
        source="MySource",
    )
    manager.add_provenance(
        dcid="ProvB",
        name="Prov B",
        url="https://mysource.com/b",
        source="MySource",
        mcf_file_name="provenance_b.mcf",
    )
    manager.add_variable_to_mcf(dcid="dcid:VarA", name="Var A")
    manager.add_variable_to_mcf(
        dcid="dcid:VarB", name="Var B", mcf_file_name="nodes_b.mcf"
    )

    manager.add_input_file(
        "data_a.csv",
        provenance="ProvA",
        data=pd.DataFrame(
            {
                "Var": ["dcid:VarA"],
                "Country": ["country/FRA"],
                "Year": [2026],
                "Val": [1.0],
            }
        ),
        column_mappings={
            "variable": "Var",
            "observationAbout": "Country",
            "date": "Year",
            "value": "Val",
        },
    )

    output_dir = tmp_path / import_name
    output_dir.mkdir(parents=True, exist_ok=True)
    manager.export_all(output_dir)

    assert_bundle_equal((GOLDEN_DIR / import_name), (tmp_path / import_name))


def test_export_bundle_multi_entity(tmp_path):
    import_name = "multi_entity_import"
    manager = CustomDataManager()
    manager.set_import_name(import_name)
    manager.add_source(
        dcid="MySource",
        name="My Source",
        url="https://mysource.com",
        description="Description for My Source.",
    )
    manager.add_provenance(
        dcid="MyProvenance",
        name="My Provenance",
        url="https://mysource.com/myprovenance",
        source="MySource",
        description="Description for My Provenance.",
    )
    manager.add_property(
        dcid="originCountry",
        name="Origin Country",
    )
    manager.add_property(
        dcid="destinationCountry",
        name="Destination Country",
    )
    manager.add_variable_to_mcf(
        dcid="dcid:TestVar",
        name="Test Var",
        description="Description for Test Var.",
        observation_properties=["dcid:originCountry", "dcid:destinationCountry"],
    )
    manager.add_input_file(
        "data.csv",
        provenance="MyProvenance",
        data=pd.DataFrame(
            {
                "Var": ["dcid:TestVar"],
                "Year": [2026],
                "Val": [1.0],
                "Origin": ["country/FRA"],
                "Destination": ["country/KEN"],
            }
        ),
        column_mappings={
            "variable": "Var",
            "date": "Year",
            "value": "Val",
            "custom:originCountry": "Origin",
            "custom:destinationCountry": "Destination",
        },
    )
    manager.add_mcf_file("*.mcf", provenance="MyProvenance")

    output_dir = tmp_path / import_name
    output_dir.mkdir(parents=True, exist_ok=True)
    manager.export_all(output_dir)

    assert_bundle_equal((GOLDEN_DIR / import_name), (tmp_path / import_name))
