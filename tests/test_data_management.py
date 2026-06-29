import json
import os
import tempfile

import pandas as pd
import pytest

from dcp_tools import CustomDataManager
from dcp_tools.custom_data.data_management import (
    DEFAULT_GROUP_NAME,
    DEFAULT_VERTICAL_SPECS_NAME,
)
from dcp_tools.custom_data.models.config_file import Config
from dcp_tools.custom_data.models.data_files import (
    ColumnMappings,
    ExplicitSchemaFile,
)


def test_custom_data_manager_add_provenance_and_override():
    """
    Verifies source/provenance addition logic in CustomDataManager.
    """
    manager = CustomDataManager()

    # add_provenance without a prior add_source must raise
    with pytest.raises(ValueError):
        manager.add_provenance(name="pA", url="http://prov", source="new_source")

    # add_source then add_provenance succeeds
    manager.add_source(name="new_source", url="http://src")
    manager.add_provenance(name="pA", url="http://prov", source="new_source")

    prov_nodes = manager._mcf_nodes["provenance.mcf"].nodes
    source_node = next(
        n for n in prov_nodes if getattr(n, "typeOf", None) == "dcid:Source"
    )
    prov_node = next(
        n for n in prov_nodes if getattr(n, "typeOf", None) == "dcid:Provenance"
    )
    assert source_node.Node == "dcid:source/new_source"
    assert prov_node.Node == "dcid:provenance/pA"
    assert prov_node.sourceLink == "dcid:source/new_source"

    # duplicate provenance without override raises
    with pytest.raises(ValueError):
        manager.add_provenance(name="pA", url="http://prov2", source="new_source")

    # override replaces the node
    manager.add_provenance(
        name="pA", url="http://prov2", source="new_source", override=True
    )
    updated_prov = next(
        n
        for n in manager._mcf_nodes["provenance.mcf"].nodes
        if getattr(n, "typeOf", None) == "dcid:Provenance"
    )
    # url is stored raw; QuotedStr serialization wraps it in quotes at dump time
    assert updated_prov.url == "http://prov2"
    assert updated_prov.model_dump()["url"] == '"http://prov2"'


def test_add_source_metadata_lands_on_node():
    """Metadata kwargs on add_source are stored on the Source node."""
    manager = CustomDataManager()
    manager.add_source(
        name="MySource",
        url="http://mysource.org",
        description="A test source",
        license="CC-BY-4.0",
    )
    nodes = manager._mcf_nodes["provenance.mcf"].nodes
    node = next(n for n in nodes if getattr(n, "typeOf", None) == "dcid:Source")
    assert node.Node == "dcid:source/MySource"
    # QuotedStr fields are stored raw; quotes applied at serialization
    assert node.description == "A test source"
    assert node.license == "CC-BY-4.0"


def test_add_provenance_metadata_lands_on_node():
    """Metadata kwargs on add_provenance are stored on the Provenance node."""
    manager = CustomDataManager()
    manager.add_source(name="SrcX", url="http://srcx.org")
    manager.add_provenance(
        name="ProvX",
        url="http://provx.org",
        source="SrcX",
        description="Prov desc",
        lastDataRefreshDate="2024-01-01",
    )
    nodes = manager._mcf_nodes["provenance.mcf"].nodes
    prov_node = next(
        n for n in nodes if getattr(n, "typeOf", None) == "dcid:Provenance"
    )
    # QuotedStr fields are stored raw; quotes applied at serialization
    assert prov_node.description == "Prov desc"
    assert prov_node.lastDataRefreshDate == "2024-01-01"


def test_validate_provenances_raises_for_unknown_provenance(tmp_path):
    """An inputFile referencing a provenance with no matching node raises at export."""
    manager = CustomDataManager()
    # Register a file with a provenance that has no corresponding MCF node
    manager._config.inputFiles.append(
        ExplicitSchemaFile(
            filename="x.csv",
            provenance="dcid:provenance/ghost",
            columnMappings=ColumnMappings(),
        )
    )
    with pytest.raises(ValueError, match="ghost"):
        manager.export_config(tmp_path)


def test_set_additional_config_fields():
    manager = CustomDataManager()

    manager.set_defaultCustomRootStatVarGroupName("My Root Group")
    manager.set_customIdNamespace("test_ns")
    # Default prefix should be auto-populated when namespace is set
    assert manager._config.customSvgPrefix == "test_ns/g/"

    manager.set_customSvgPrefix("test_ns/groups/")
    manager.set_svHierarchyPropsBlocklist(
        [
            "statType",
            "measurementQualifier",
            "statType",
        ]
    )

    assert manager._config.defaultCustomRootStatVarGroupName == "My Root Group"
    assert manager._config.customIdNamespace == "test_ns"
    assert manager._config.customSvgPrefix == "test_ns/groups/"
    assert manager._config.svHierarchyPropsBlocklist == [
        "statType",
        "measurementQualifier",
    ]


def test_import_name_set_and_export_default(tmp_path):
    """set_importName stores the value; export_config defaults it to the dir name."""
    # explicit importName survives export unchanged
    manager = CustomDataManager()
    manager.set_importName("MyImport")
    assert manager._config.importName == "MyImport"
    out = tmp_path / "OECD_wage_data"
    out.mkdir()
    manager.export_config(out)
    assert Config.from_json(str(out / "config.json")).importName == "MyImport"

    # unset importName defaults to each export directory name without mutating state,
    # so re-exporting the same manager elsewhere picks up the new directory's name.
    manager2 = CustomDataManager()
    out2 = tmp_path / "frog_data"
    out2.mkdir()
    manager2.export_config(out2)
    assert Config.from_json(str(out2 / "config.json")).importName == "frog_data"
    assert manager2._config.importName is None

    out3 = tmp_path / "toad_data"
    out3.mkdir()
    manager2.export_config(out3)
    assert Config.from_json(str(out3 / "config.json")).importName == "toad_data"


def test_add_explicit_schema_file_registration_and_override(tmp_path):
    """
    Verifies explicit schema file registration in config and data,
    and override/error behaviors.
    """
    manager = CustomDataManager()
    manager.add_source(name="s1", url="http://src")
    manager.add_provenance(name="p1", url="http://prov", source="s1")

    df3 = pd.DataFrame({"entity": ["e1"], "Year": [2020], "Value": [100]})
    manager.add_explicit_schema_file(
        file_name="exp.csv",
        provenance="p1",
        data=df3,
        columnMappings={"entity": "entity", "date": "Year", "value": "Value"},
    )
    assert any(e.filename == "exp.csv" for e in manager._config.inputFiles)
    assert "exp.csv" in manager._data

    with pytest.raises(ValueError):
        manager.add_explicit_schema_file(
            file_name="exp.csv",
            provenance="p1",
        )

    df_new = pd.DataFrame({"entity": ["e2"], "Year": [2021], "Value": [200]})
    manager.add_explicit_schema_file(
        file_name="exp.csv",
        provenance="p1",
        data=df_new,
        override=True,
    )
    pd.testing.assert_frame_equal(manager._data["exp.csv"], df_new)

    df4 = pd.DataFrame({"X": [1]})
    with pytest.raises(ValueError):
        manager.add_data(df4, "no_file.csv")


def test_add_explicit_schema_file_without_column_mappings():
    """Ensure missing columnMappings defaults to empty dict without error."""
    manager = CustomDataManager()
    manager.add_source(name="s1", url="http://src")
    manager.add_provenance(name="p1", url="http://prov", source="s1")

    df = pd.DataFrame({"A": [1]})
    manager.add_explicit_schema_file(file_name="exp.csv", provenance="p1", data=df)

    entry = next(e for e in manager._config.inputFiles if e.filename == "exp.csv")
    mappings = entry.columnMappings
    assert mappings.model_dump(exclude_none=True) == {}


def test_add_explicit_schema_file_pattern_xor_filename():
    """add_explicit_schema_file raises when neither or both of file_name/pattern are given."""
    manager = CustomDataManager()
    manager.add_source(name="s1", url="http://src")
    manager.add_provenance(name="p1", url="http://prov", source="s1")

    with pytest.raises(ValueError, match="Exactly one"):
        manager.add_explicit_schema_file(provenance="p1")

    with pytest.raises(ValueError, match="Exactly one"):
        manager.add_explicit_schema_file(
            file_name="a.csv", pattern="a*", provenance="p1"
        )


def test_export_methods(tmp_path):
    """
    Exercises export_config, export_data, and export_mcf_file.
    """
    manager = CustomDataManager()
    manager.add_source(name="s1", url="http://src")
    manager.add_provenance(name="p1", url="http://prov", source="s1")
    df = pd.DataFrame({"A": [1]})
    manager.add_explicit_schema_file(
        file_name="data.csv",
        provenance="p1",
        data=df,
        columnMappings={"entity": "A"},
    )
    manager.add_variable_to_mcf(Node="dcid:vX", name="VX")

    manager.export_config(tmp_path)
    config_file = tmp_path / "config.json"
    assert config_file.exists()
    loaded = Config.from_json(str(config_file))
    assert isinstance(loaded, Config)

    manager.export_data(tmp_path)
    data_file = tmp_path / "data.csv"
    assert data_file.exists()

    manager.export_mfc_file(tmp_path, mcf_file_name="custom_nodes.mcf")
    mcf_file = tmp_path / "custom_nodes.mcf"
    assert mcf_file.exists()
    assert "Node: dcid:vX" in mcf_file.read_text()


def test_add_variable_group_to_mcf_and_override():
    """
    Checks StatVarGroup node addition and override behavior.
    """
    manager = CustomDataManager()
    manager.add_variable_group_to_mcf(
        Node="dcid:test/g/1", name="Group1", specializationOf="dcid:dc/g/Root"
    )
    groups = manager._mcf_nodes[DEFAULT_GROUP_NAME].nodes
    assert any(
        n.Node == "dcid:test/g/1" and n.specializationOf == "dcid:dc/g/Root"
        for n in groups
    )

    manager.add_variable_group_to_mcf(
        Node="dcid:test/g/1",
        name="Group2",
        specializationOf="dcid:dc/g/Root",
        override=True,
    )
    updated = manager._mcf_nodes[DEFAULT_GROUP_NAME].nodes
    assert any(n.name == "Group2" for n in updated if n.Node == "dcid:test/g/1")


def test_config_round_trip(tmp_path):
    """
    Ensures a Config can be dumped to JSON and loaded back identically.
    """
    cfg = Config(inputFiles=[])
    path = tmp_path / "cfg.json"
    path.write_text(cfg.model_dump_json())
    loaded = Config.from_json(str(path))
    assert loaded.model_dump() == cfg.model_dump()


def test_custom_data_manager_repr():
    """
    Sanity-check CustomDataManager.__repr__ for correct counts.
    """
    manager = CustomDataManager()
    manager.add_source(name="s1", url="http://src")
    manager.add_provenance(name="p1", url="http://prov", source="s1")
    df = pd.DataFrame({"A": [1]})
    manager.add_explicit_schema_file(
        file_name="f.csv",
        provenance="p1",
        data=df,
        columnMappings={"entity": "A"},
    )
    manager.add_variable_to_mcf(Node="dcid:vX", name="VX")
    r = repr(manager)
    assert "1 inputFiles" in r
    assert "1 containing data" in r
    assert "1 sources" in r
    assert "1 provenances" in r
    assert "1 variables" in r


def test_remove_indicator():
    manager = CustomDataManager()
    manager.add_source(name="s1", url="http://src")
    manager.add_provenance(name="p1", url="http://prov", source="s1")

    df = pd.DataFrame({"A": [1]})
    manager.add_explicit_schema_file(
        file_name="a.csv",
        provenance="p1",
        data=df,
        columnMappings={"entity": "A"},
    )
    manager.add_variable_to_mcf(Node="dcid:sv1", name="Var", provenance="p1")

    manager.remove_indicator("dcid:sv1")
    for nodes in manager._mcf_nodes.values():
        assert all(n.Node != "dcid:sv1" for n in nodes.nodes)

    with pytest.raises(ValueError):
        manager.remove_indicator("missing")


def _make_cfg(
    key: str,
    prov: str,
    *,
    include_subdirs: bool | None = None,
    group_by_property: bool | None = None,
    root_group_name: str | None = None,
    custom_namespace: str | None = None,
    custom_svg_prefix: str | None = None,
    sv_blocklist: list[str] | None = None,
    data_download_url: list[str] | None = None,
    vertical_specs_file: str | None = None,
):
    input_files = [
        ExplicitSchemaFile(
            filename=key,
            provenance=prov,
            columnMappings=ColumnMappings(),
        )
    ]
    return Config(
        inputFiles=input_files,
        includeInputSubdirs=include_subdirs,
        groupStatVarsByProperty=group_by_property,
        defaultCustomRootStatVarGroupName=root_group_name,
        customIdNamespace=custom_namespace,
        customSvgPrefix=custom_svg_prefix,
        svHierarchyPropsBlocklist=sv_blocklist,
        dataDownloadUrl=data_download_url,
        verticalSpecsFile=vertical_specs_file,
    )


def test_set_data_download_url():
    manager = CustomDataManager()
    manager.set_dataDownloadUrl(["u1", "u2"])
    assert manager._config.dataDownloadUrl == ["u1", "u2"]

    manager.set_dataDownloadUrl(None)
    assert manager._config.dataDownloadUrl is None


def test_add_data_download_url_initializes_and_appends():
    manager = CustomDataManager()

    # Initializes from unset
    manager.add_dataDownloadUrl("u1")
    assert manager._config.dataDownloadUrl == ["u1"]

    # Appends to existing list
    manager.add_dataDownloadUrl("u2")
    assert manager._config.dataDownloadUrl == ["u1", "u2"]

    # Unset then re-initialize
    manager.set_dataDownloadUrl(None)
    manager.add_dataDownloadUrl("u3")
    assert manager._config.dataDownloadUrl == ["u3"]


def test_set_vertical_specs_file():
    manager = CustomDataManager()
    manager.set_verticalSpecsFile("vs.json")
    assert manager._config.verticalSpecsFile == "vs.json"

    manager.set_verticalSpecsFile(None)
    assert manager._config.verticalSpecsFile is None


def test_add_vertical_spec_appends_and_wires_config():
    manager = CustomDataManager()
    manager.add_vertical_spec(
        verticals=["PersonCountVertical"],
        population_type="Person",
        measured_properties=["count"],
    )

    # Auto-wires verticalSpecsFile to the default name on first use
    assert manager._config.verticalSpecsFile == DEFAULT_VERTICAL_SPECS_NAME
    assert len(manager._vertical_specs) == 1
    spec = manager._vertical_specs[0]
    assert spec.populationType == "Person"
    assert spec.measuredProperties == ["count"]
    assert spec.verticals == ["PersonCountVertical"]


def test_add_vertical_spec_respects_existing_and_explicit_filename():
    # A filename set beforehand is left untouched by the default path
    manager = CustomDataManager()
    manager.set_verticalSpecsFile("custom.json")
    manager.add_vertical_spec(verticals=["v"])
    assert manager._config.verticalSpecsFile == "custom.json"

    # An explicit file_name overrides
    manager.add_vertical_spec(verticals=["v2"], file_name="other.json")
    assert manager._config.verticalSpecsFile == "other.json"


def test_export_vertical_specs_writes_specs_json(tmp_path):
    manager = CustomDataManager()
    manager.add_vertical_spec(
        verticals=["PersonCountVertical"],
        population_type="Person",
        measured_properties=["count"],
    )
    manager.export_vertical_specs(tmp_path)

    written = json.loads((tmp_path / DEFAULT_VERTICAL_SPECS_NAME).read_text())
    assert written == {
        "specs": [
            {
                "populationType": "Person",
                "measuredProperties": ["count"],
                "verticals": ["PersonCountVertical"],
            }
        ]
    }


def test_export_vertical_specs_raises_when_empty(tmp_path):
    manager = CustomDataManager()
    with pytest.raises(ValueError):
        manager.export_vertical_specs(tmp_path)


def test_export_all_includes_vertical_specs(tmp_path):
    manager = CustomDataManager()
    manager.add_vertical_spec(verticals=["PersonCountVertical"])

    manager.export_all(tmp_path)

    assert (tmp_path / DEFAULT_VERTICAL_SPECS_NAME).exists()
    config = json.loads((tmp_path / "config.json").read_text())
    assert config["verticalSpecsFile"] == DEFAULT_VERTICAL_SPECS_NAME


def test_add_explicit_schema_file_observation_properties():
    manager = CustomDataManager()

    manager.add_explicit_schema_file(
        "data.csv",
        provenance="prov1",
        columnMappings={"entity": "Country", "date": "Year"},
        observationProperties={"unit": "USDollar", "customProp": "x"},
    )

    entry = manager._config.inputFiles[0]
    assert entry.observationProperties is not None
    assert entry.observationProperties.unit == "USDollar"
    assert entry.observationProperties.__pydantic_extra__["customProp"] == "x"
    # columnMappings coexists
    assert entry.columnMappings is not None

    # Omitting the kwarg leaves observationProperties absent (None)
    manager.add_explicit_schema_file(
        "other.csv",
        provenance="prov1",
    )
    other_entry = manager._config.inputFiles[1]
    assert other_entry.observationProperties is None


def test_merge_data_download_url(tmp_path):
    d1 = tmp_path / "one"
    d1.mkdir()
    cfg1 = _make_cfg("a.csv", "p1", data_download_url=["u1"])
    (d1 / "config.json").write_text(
        cfg1.model_dump_json(indent=2, exclude_none=True, by_alias=True)
    )

    d2 = tmp_path / "two"
    d2.mkdir()
    cfg2 = _make_cfg("b.csv", "p2")
    (d2 / "config.json").write_text(
        cfg2.model_dump_json(indent=2, exclude_none=True, by_alias=True)
    )

    manager = CustomDataManager.from_config_files_in_directory(tmp_path)
    assert manager._config.dataDownloadUrl == ["u1"]

    # Override policy: second config has different urls → takes the new list
    d3 = tmp_path / "three"
    d3.mkdir()
    cfg3 = _make_cfg("c.csv", "p3", data_download_url=["u2"])
    (d3 / "config.json").write_text(
        cfg3.model_dump_json(indent=2, exclude_none=True, by_alias=True)
    )

    manager2 = CustomDataManager.from_config_files_in_directory(
        tmp_path, policy="override"
    )
    assert manager2._config.dataDownloadUrl == ["u2"]


def test_merge_vertical_specs_file(tmp_path):
    d1 = tmp_path / "one"
    d1.mkdir()
    cfg1 = _make_cfg("a.csv", "p1", vertical_specs_file="vs.json")
    (d1 / "config.json").write_text(
        cfg1.model_dump_json(indent=2, exclude_none=True, by_alias=True)
    )

    d2 = tmp_path / "two"
    d2.mkdir()
    cfg2 = _make_cfg("b.csv", "p2")
    (d2 / "config.json").write_text(
        cfg2.model_dump_json(indent=2, exclude_none=True, by_alias=True)
    )

    manager = CustomDataManager.from_config_files_in_directory(tmp_path)
    assert manager._config.verticalSpecsFile == "vs.json"


def test_merge_configs_from_directory(tmp_path):
    d1 = tmp_path / "one"
    d1.mkdir()
    cfg1 = _make_cfg(
        "a.csv",
        "p1",
        custom_namespace="ns",
        sv_blocklist=["measurementDenominator"],
    )
    cfg1.includeInputSubdirs = True
    (d1 / "config.json").write_text(
        cfg1.model_dump_json(indent=2, exclude_none=True, by_alias=True)
    )

    d2 = tmp_path / "two"
    d2.mkdir()
    cfg2 = _make_cfg(
        "b.csv",
        "p2",
        custom_svg_prefix="ns/custom/",
    )
    (d2 / "config.json").write_text(
        cfg2.model_dump_json(indent=2, exclude_none=True, by_alias=True)
    )

    manager = CustomDataManager.from_config_files_in_directory(tmp_path)

    filenames = {e.filename for e in manager._config.inputFiles}
    assert filenames == {"a.csv", "b.csv"}
    assert manager._config.includeInputSubdirs is True
    assert manager._config.customIdNamespace == "ns"
    # Blocklist remains the one provided explicitly (none defined in the second config).
    assert manager._config.svHierarchyPropsBlocklist == ["measurementDenominator"]


def test_merge_configs_duplicate_error(tmp_path):
    d1 = tmp_path / "one"
    d1.mkdir()
    cfg1 = _make_cfg("a.csv", "p1")
    (d1 / "config.json").write_text(
        cfg1.model_dump_json(indent=2, exclude_none=True, by_alias=True)
    )

    d2 = tmp_path / "two"
    d2.mkdir()
    cfg2 = _make_cfg("a.csv", "p2")
    (d2 / "config.json").write_text(
        cfg2.model_dump_json(indent=2, exclude_none=True, by_alias=True)
    )

    with pytest.raises(ValueError):
        CustomDataManager.from_config_files_in_directory(tmp_path)


def test_merge_configs_blocklist_override(tmp_path):
    d1 = tmp_path / "one"
    d1.mkdir()
    cfg1 = _make_cfg("a.csv", "p1", sv_blocklist=["measurementDenominator", "statType"])
    (d1 / "config.json").write_text(
        cfg1.model_dump_json(indent=2, exclude_none=True, by_alias=True)
    )

    d2 = tmp_path / "two"
    d2.mkdir()
    cfg2 = _make_cfg("b.csv", "p2", sv_blocklist=["statType", "unit"])
    (d2 / "config.json").write_text(
        cfg2.model_dump_json(indent=2, exclude_none=True, by_alias=True)
    )

    manager = CustomDataManager.from_config_files_in_directory(
        tmp_path, policy="override"
    )

    # When overriding, we take the latest list but still remove duplicates.
    assert manager._config.svHierarchyPropsBlocklist == ["statType", "unit"]


def test_rename_variable_mcf_only():
    """rename_variable operates on MCF nodes exclusively (no config.variables)."""
    manager = CustomDataManager()
    manager.add_variable_to_mcf(Node="dcid:v1", name="Var1")

    manager.rename_variable("dcid:v1", "dcid:v2")
    for nodes in manager._mcf_nodes.values():
        assert any(n.Node == "dcid:v2" for n in nodes.nodes)
    for nodes in manager._mcf_nodes.values():
        assert all(n.Node != "dcid:v1" for n in nodes.nodes)

    # Renaming a missing variable raises ValueError
    with pytest.raises(ValueError):
        manager.rename_variable("missing", "dcid:v3")

    # Renaming to an existing MCF node name raises ValueError
    manager.add_variable_to_mcf(Node="dcid:v3", name="Var3")
    with pytest.raises(ValueError):
        manager.rename_variable("dcid:v2", "dcid:v3")


def test_validate_all_input_files_have_data(tmp_path):
    """Verify the optional data-completeness validation on export_all and the standalone method."""
    manager = CustomDataManager()
    manager.add_source(name="s1", url="http://src")
    manager.add_provenance(name="p1", url="http://prov", source="s1")

    df = pd.DataFrame({"A": [1, 2]})

    # Register one file WITH data and one WITHOUT data
    manager.add_explicit_schema_file(
        file_name="with_data.csv",
        provenance="p1",
        data=df,
    )
    manager.add_explicit_schema_file(
        file_name="no_data.csv",
        provenance="p1",
    )

    # Standalone validation method raises because no_data.csv has no data
    with pytest.raises(ValueError, match=r"no_data\.csv"):
        manager.validate_all_input_files_have_data()

    # validate_data=False does not surface the missing-data error
    manager.export_all(tmp_path, validate_data=False, mcf_file_names=["provenance.mcf"])

    # export_all with validate_data=True should raise before writing anything
    with pytest.raises(ValueError, match=r"no_data\.csv"):
        manager.export_all(tmp_path, validate_data=True)

    # After adding data for the second file, validation passes
    manager.add_data(df, "no_data.csv")
    manager.validate_all_input_files_have_data()  # should not raise

    manager.export_all(
        tmp_path, validate_data=True, mcf_file_names=["provenance.mcf"]
    )  # should not raise
    assert (tmp_path / "config.json").exists()
    assert (tmp_path / "with_data.csv").exists()
    assert (tmp_path / "no_data.csv").exists()


def test_export_all_requires_provenance_mcf(tmp_path):
    """export_all raises (before writing) if a referenced provenance's MCF file is omitted."""
    manager = CustomDataManager()
    manager.add_source(name="s1", url="http://src")
    manager.add_provenance(name="p1", url="http://prov", source="s1")
    manager.add_explicit_schema_file(
        file_name="data.csv", provenance="p1", data=pd.DataFrame({"A": [1]})
    )

    # Omitting mcf_file_names would ship a config.json referencing a node not on disk.
    with pytest.raises(ValueError, match=r"provenance\.mcf"):
        manager.export_all(tmp_path)
    assert not (tmp_path / "config.json").exists(), "must not write a partial bundle"

    # Listing the provenance MCF file makes the bundle complete.
    manager.export_all(tmp_path, mcf_file_names=["provenance.mcf"])
    assert (tmp_path / "config.json").exists()
    assert (tmp_path / "provenance.mcf").exists()


def test_export_all_requires_linked_source_mcf(tmp_path):
    """The guard follows sourceLink: a Source kept in a separate MCF file must be exported too."""
    manager = CustomDataManager()
    manager.add_source(name="s1", url="http://src", mcf_file_name="sources.mcf")
    manager.add_provenance(name="p1", url="http://prov", source="s1")
    manager.add_explicit_schema_file(
        file_name="data.csv", provenance="p1", data=pd.DataFrame({"A": [1]})
    )

    # Exporting only provenance.mcf leaves the sourceLink dangling -> raises, names sources.mcf.
    with pytest.raises(ValueError, match=r"sources\.mcf"):
        manager.export_all(tmp_path, mcf_file_names=["provenance.mcf"])
    assert not (tmp_path / "config.json").exists(), "must not write a partial bundle"

    # Exporting both the provenance and its source file makes the bundle complete.
    manager.export_all(tmp_path, mcf_file_names=["provenance.mcf", "sources.mcf"])
    assert (tmp_path / "provenance.mcf").exists()
    assert (tmp_path / "sources.mcf").exists()


def test_loading_legacy_implicit_config_raises_with_message():
    """Loading a JSON config with variablePerColumn format raises ValueError with a clear message."""
    cfg = {
        "inputFiles": {
            "legacy.csv": {
                "provenance": "p",
                "entityType": "Country",
                "observationProperties": {},
                "format": "variablePerColumn",
            }
        },
        "sources": {"S": {"url": "http://s/", "provenances": {"p": "http://p/"}}},
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "config.json")
        with open(path, "w") as f:
            json.dump(cfg, f)
        with pytest.raises(ValueError, match="is no longer supported") as exc_info:
            Config.from_json(path)
        assert "legacy.csv" in str(exc_info.value)


def test_column_mappings_emit_dcid_keys():
    """Verify ColumnMappings emits dcid: prefixed keys on serialization."""
    cm = ColumnMappings(
        variable="Var",
        entity="Country",
        date="Year",
        value="Val",
        unit="USD",
        scalingFactor="1000",
        measurementMethod="Census",
        observationPeriod="P1Y",
    )
    result = cm.model_dump(by_alias=True)
    print()
    print(result)

    # All 7 aliased fields must emit dcid: keys
    assert result["dcid:variableMeasured"] == "Var"
    assert result["dcid:observationAbout"] == "Country"
    assert result["dcid:observationDate"] == "Year"
    assert result["dcid:value"] == "Val"
    assert result["dcid:unit"] == "USD"
    assert result["dcid:measurementMethod"] == "Census"
    assert result["dcid:observationPeriod"] == "P1Y"

    # scalingFactor stays short on both sides
    assert "scalingFactor" in result
    assert "dcid:scalingFactor" not in result

    # Short keys must NOT appear for aliased fields
    for short_key in [
        "variable",
        "entity",
        "date",
        "value",
        "unit",
        "measurementMethod",
        "observationPeriod",
    ]:
        assert short_key not in result


def test_column_mappings_accepts_dcid_keys_on_input():
    """Verify ColumnMappings accepts dcid: keys on input (read-back guard)."""
    cm = ColumnMappings.model_validate(
        {
            "dcid:observationAbout": "Country",
            "dcid:observationDate": "Year",
            "dcid:value": "Val",
        }
    )
    assert cm.entity == "Country"
    assert cm.date == "Year"
    assert cm.value == "Val"

    # Short-key input must also still work
    cm2 = ColumnMappings.model_validate({"entity": "Country"})
    assert cm2.entity == "Country"
