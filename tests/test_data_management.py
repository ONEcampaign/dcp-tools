import pandas as pd
import pytest

from bblocks.datacommons_tools import CustomDataManager
from bblocks.datacommons_tools.custom_data.data_management import DEFAULT_GROUP_NAME
from bblocks.datacommons_tools.custom_data.models.config_file import Config
from bblocks.datacommons_tools.custom_data.models.data_files import (
    ImplicitSchemaFile,
    ObservationProperties,
)
from bblocks.datacommons_tools.custom_data.models.sources import Source


def test_custom_data_manager_add_provenance_and_override():
    """
    Verifies provenance addition logic in CustomDataManager.
    """
    manager = CustomDataManager()
    # Missing source_url should fail
    with pytest.raises(ValueError):
        manager.add_provenance(
            provenance_name="pA", provenance_url="http://prov", source_name="new_source"
        )
    # Provide source_url to succeed
    manager.add_provenance(
        provenance_name="pA",
        provenance_url="http://prov",
        source_name="new_source",
        source_url="http://src",
    )

    # Adding same provenance without override should error
    with pytest.raises(ValueError):
        manager.add_provenance(
            provenance_name="pA",
            provenance_url="http://prov2",
            source_name="new_source",
        )

    # Override existing provenance URL
    manager.add_provenance(
        provenance_name="pA",
        provenance_url="http://prov2",
        source_name="new_source",
        override=True,
    )
    # Confirm update
    src = manager._config.sources["new_source"]
    assert src.provenances["pA"].unicode_string() == "http://prov2/"


def test_custom_data_manager_add_variable_to_config_and_override():
    """
    Ensures variables are registered and override works in config.
    """
    manager = CustomDataManager()
    manager.add_variable_to_config(statVar="v1", name="Var1")
    # Duplicate without override errors
    with pytest.raises(ValueError):
        manager.add_variable_to_config(statVar="v1", name="Var1New")
    # Override succeeds
    manager.add_variable_to_config(statVar="v1", name="Var1New", override=True)
    assert manager._config.variables["v1"].name == "Var1New"


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


def test_add_implicit_and_explicit_schema_file_registration_and_override(tmp_path):
    """
    Verifies implicit/explicit schema file registration in config and data,
    and override/error behaviors.
    """
    manager = CustomDataManager()
    manager.add_provenance("p1", "http://prov", "s1", source_url="http://src")

    df1 = pd.DataFrame({"A": [1, 2]})
    manager.add_implicit_schema_file(
        file_name="imp.csv",
        provenance="p1",
        data=df1,
        entityType="Country",
        observationProperties={"unit": "U"},
    )
    assert "imp.csv" in manager._config.inputFiles
    assert "imp.csv" in manager._data

    df2 = pd.DataFrame({"A": [3, 4]})
    with pytest.raises(ValueError):
        manager.add_implicit_schema_file(
            "imp.csv", provenance="p1", entityType="Country"
        )

    manager.add_implicit_schema_file(
        file_name="imp.csv",
        provenance="p1",
        data=df2,
        override=True,
        entityType="State",
    )
    pd.testing.assert_frame_equal(manager._data["imp.csv"], df2)

    df3 = pd.DataFrame({"entity": ["e1"], "Year": [2020], "Value": [100]})
    manager.add_explicit_schema_file(
        file_name="exp.csv",
        provenance="p1",
        data=df3,
        columnMappings={"entity": "entity", "date": "Year", "value": "Value"},
    )
    assert "exp.csv" in manager._config.inputFiles
    assert "exp.csv" in manager._data

    df4 = pd.DataFrame({"X": [1]})
    with pytest.raises(ValueError):
        manager.add_data(df4, "no_file.csv")


def test_add_explicit_schema_file_without_column_mappings():
    """Ensure missing columnMappings defaults to empty dict without error."""
    manager = CustomDataManager()
    manager.add_provenance("p1", "http://prov", "s1", source_url="http://src")

    df = pd.DataFrame({"A": [1]})
    manager.add_explicit_schema_file(file_name="exp.csv", provenance="p1", data=df)

    assert "exp.csv" in manager._config.inputFiles
    mappings = manager._config.inputFiles["exp.csv"].columnMappings
    assert mappings.model_dump(exclude_none=True) == {}


def test_export_methods(tmp_path):
    """
    Exercises export_config, export_data, and export_mcf_file.
    """
    manager = CustomDataManager()
    manager.add_provenance("p1", "http://prov", "s1", source_url="http://src")
    df = pd.DataFrame({"A": [1]})
    manager.add_implicit_schema_file(
        file_name="data.csv",
        provenance="p1",
        data=df,
        entityType="Country",
        observationProperties={"unit": "U"},
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
    cfg = Config(inputFiles={}, sources={})
    path = tmp_path / "cfg.json"
    path.write_text(cfg.model_dump_json())
    loaded = Config.from_json(str(path))
    assert loaded.model_dump() == cfg.model_dump()


def test_custom_data_manager_repr():
    """
    Sanity-check CustomDataManager.__repr__ for correct counts.
    """
    manager = CustomDataManager()
    manager.add_provenance("p1", "http://prov", "s1", source_url="http://src")
    manager.add_variable_to_config(statVar="dcid:v1", name="Var1")
    df = pd.DataFrame({"A": [1]})
    manager.add_implicit_schema_file(
        file_name="f.csv",
        provenance="p1",
        data=df,
        entityType="Country",
        observationProperties={"unit": "u"},
    )
    manager.add_variable_to_mcf(Node="dcid:vX", name="VX")
    r = repr(manager)
    assert "1 inputFiles" in r
    assert "1 containing data" in r
    assert "1 sources" in r
    assert "2 variables" in r


def test_remove_indicator_and_provenance():
    manager = CustomDataManager()
    manager.add_provenance("p1", "http://prov", "s1", source_url="http://src")

    df = pd.DataFrame({"A": [1]})
    manager.add_implicit_schema_file(
        file_name="a.csv",
        provenance="p1",
        data=df,
        entityType="Country",
        observationProperties={"unit": "u"},
    )
    manager.add_variable_to_config(statVar="dcid:sv1", name="Var")
    manager.add_variable_to_mcf(Node="dcid:sv1", name="Var", provenance="p1")

    manager.remove_indicator("dcid:sv1")
    assert "dcid:sv1" not in (manager._config.variables or {})
    for nodes in manager._mcf_nodes.values():
        assert all(n.Node != "dcid:sv1" for n in nodes.nodes)

    with pytest.raises(ValueError):
        manager.remove_indicator("missing")

    manager.add_variable_to_mcf(Node="dcid:sv2", name="Var2", provenance="p1")
    manager.add_variable_to_config(statVar="dcid:sv2", name="Var2")
    manager.add_explicit_schema_file(file_name="b.csv", provenance="p1", data=df)

    manager.remove_by_provenance("p1")

    assert not any(
        info.provenance == "p1" for info in manager._config.inputFiles.values()
    )
    assert "a.csv" not in manager._data and "b.csv" not in manager._data
    for nodes in manager._mcf_nodes.values():
        assert all(getattr(n, "provenance", None) != '"p1"' for n in nodes.nodes)

    with pytest.raises(ValueError):
        manager.remove_by_provenance("unknown")


def test_remove_provenance_and_source_methods():
    manager = CustomDataManager()
    manager.add_provenance("p1", "http://prov1", "s1", source_url="http://src")
    manager.add_provenance("p2", "http://prov2", "s1")

    df = pd.DataFrame({"A": [1]})
    manager.add_implicit_schema_file(
        file_name="a.csv",
        provenance="p1",
        data=df,
        entityType="Country",
        observationProperties={"unit": "u"},
    )
    manager.add_explicit_schema_file(file_name="b.csv", provenance="p2", data=df)

    manager.remove_provenance("p1")

    # provenance removed from sources and data
    assert "p1" not in manager._config.sources["s1"].provenances
    assert "a.csv" not in manager._config.inputFiles
    assert "a.csv" not in manager._data

    manager.remove_by_source("s1")

    # remaining provenance data removed but source still present
    assert "b.csv" not in manager._config.inputFiles
    assert "b.csv" not in manager._data
    assert "s1" in manager._config.sources

    # remove_source works on a fresh manager
    manager2 = CustomDataManager()
    manager2.add_provenance("p1", "http://prov", "s1", source_url="http://src")
    manager2.add_implicit_schema_file(
        file_name="c.csv",
        provenance="p1",
        data=df,
        entityType="Country",
        observationProperties={"unit": "u"},
    )

    manager2.remove_source("s1")

    assert "s1" not in manager2._config.sources
    assert "c.csv" not in manager2._config.inputFiles


def _make_cfg(
    key: str,
    prov: str,
    source: str,
    *,
    include_subdirs: bool | None = None,
    group_by_property: bool | None = None,
    root_group_name: str | None = None,
    custom_namespace: str | None = None,
    custom_svg_prefix: str | None = None,
    sv_blocklist: list[str] | None = None,
):
    input_files = {
        key: ImplicitSchemaFile(
            provenance=prov,
            entityType="Country",
            observationProperties=ObservationProperties(),
        )
    }
    sources = {source: Source(url="http://src", provenances={prov: "http://p"})}
    return Config(
        inputFiles=input_files,
        sources=sources,
        includeInputSubdirs=include_subdirs,
        groupStatVarsByProperty=group_by_property,
        defaultCustomRootStatVarGroupName=root_group_name,
        customIdNamespace=custom_namespace,
        customSvgPrefix=custom_svg_prefix,
        svHierarchyPropsBlocklist=sv_blocklist,
    )


def test_merge_configs_from_directory(tmp_path):
    d1 = tmp_path / "one"
    d1.mkdir()
    cfg1 = _make_cfg(
        "a.csv",
        "p1",
        "s",
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
        "s",
        custom_svg_prefix="ns/custom/",
    )
    (d2 / "config.json").write_text(
        cfg2.model_dump_json(indent=2, exclude_none=True, by_alias=True)
    )

    manager = CustomDataManager.from_config_files_in_directory(tmp_path)

    assert set(manager._config.inputFiles.keys()) == {"a.csv", "b.csv"}
    provs = manager._config.sources["s"].provenances
    assert set(provs.keys()) == {"p1", "p2"}
    assert manager._config.includeInputSubdirs is True
    assert manager._config.customIdNamespace == "ns"
    # Blocklist remains the one provided explicitly (none defined in the second config).
    assert manager._config.svHierarchyPropsBlocklist == ["measurementDenominator"]


def test_merge_configs_duplicate_error(tmp_path):
    d1 = tmp_path / "one"
    d1.mkdir()
    cfg1 = _make_cfg("a.csv", "p1", "s")
    (d1 / "config.json").write_text(
        cfg1.model_dump_json(indent=2, exclude_none=True, by_alias=True)
    )

    d2 = tmp_path / "two"
    d2.mkdir()
    cfg2 = _make_cfg("a.csv", "p2", "s")
    (d2 / "config.json").write_text(
        cfg2.model_dump_json(indent=2, exclude_none=True, by_alias=True)
    )

    with pytest.raises(ValueError):
        CustomDataManager.from_config_files_in_directory(tmp_path)


def test_merge_configs_blocklist_override(tmp_path):
    d1 = tmp_path / "one"
    d1.mkdir()
    cfg1 = _make_cfg(
        "a.csv", "p1", "s", sv_blocklist=["measurementDenominator", "statType"]
    )
    (d1 / "config.json").write_text(
        cfg1.model_dump_json(indent=2, exclude_none=True, by_alias=True)
    )

    d2 = tmp_path / "two"
    d2.mkdir()
    cfg2 = _make_cfg("b.csv", "p2", "s", sv_blocklist=["statType", "unit"])
    (d2 / "config.json").write_text(
        cfg2.model_dump_json(indent=2, exclude_none=True, by_alias=True)
    )

    manager = CustomDataManager.from_config_files_in_directory(
        tmp_path, policy="override"
    )

    # When overriding, we take the latest list but still remove duplicates.
    assert manager._config.svHierarchyPropsBlocklist == ["statType", "unit"]


def test_rename_provenance_updates_all_references():
    manager = CustomDataManager()
    manager.add_provenance("p1", "http://prov1", "s1", source_url="http://src")

    df = pd.DataFrame({"A": [1]})
    manager.add_implicit_schema_file(
        file_name="a.csv",
        provenance="p1",
        data=df,
        entityType="Country",
        observationProperties={"unit": "u"},
    )
    manager.add_variable_to_config(
        "dcid:sv1", name="Var", properties={"provenance": "p1"}
    )
    manager.add_variable_to_mcf(Node="dcid:sv1", name="Var", provenance="p1")

    manager.rename_provenance("p1", "pX")

    assert "pX" in manager._config.sources["s1"].provenances
    assert manager._config.inputFiles["a.csv"].provenance == "pX"
    assert manager._config.variables["dcid:sv1"].properties["provenance"] == "pX"
    for nodes in manager._mcf_nodes.values():
        assert any(getattr(n, "provenance", None) == '"pX"' for n in nodes.nodes)

    with pytest.raises(ValueError):
        manager.rename_provenance("pX", "pX")


def test_rename_variable_and_source_methods():
    manager = CustomDataManager()
    manager.add_provenance("p1", "http://prov1", "s1", source_url="http://src")
    manager.add_variable_to_config("dcid:v1", name="Var1")
    manager.add_variable_to_mcf(Node="dcid:v1", name="Var1")

    manager.rename_variable("dcid:v1", "dcid:v2")
    assert "dcid:v2" in manager._config.variables
    for nodes in manager._mcf_nodes.values():
        assert any(n.Node == "dcid:v2" for n in nodes.nodes)

    manager.add_variable_to_config("dcid:v3", name="Var3")
    with pytest.raises(ValueError):
        manager.rename_variable("dcid:v2", "dcid:v3")
    with pytest.raises(ValueError):
        manager.rename_variable("missing", "dcid:v4")

    manager.rename_source("s1", "s2")
    assert "s2" in manager._config.sources and "s1" not in manager._config.sources

    with pytest.raises(ValueError):
        manager.rename_source("unknown", "x")
    with pytest.raises(ValueError):
        manager.rename_source("s2", "s2")


def test_validate_all_input_files_have_data(tmp_path):
    """Verify the optional data-completeness validation on export_all and the standalone method."""
    manager = CustomDataManager()
    manager.add_provenance("p1", "http://prov", "s1", source_url="http://src")

    df = pd.DataFrame({"A": [1, 2]})

    # Register one file WITH data and one WITHOUT data
    manager.add_implicit_schema_file(
        file_name="with_data.csv",
        provenance="p1",
        data=df,
        entityType="Country",
    )
    manager.add_implicit_schema_file(
        file_name="no_data.csv",
        provenance="p1",
        entityType="Country",
    )

    # Standalone validation method raises because no_data.csv has no data
    with pytest.raises(ValueError, match="no_data.csv"):
        manager.validate_all_input_files_have_data()

    # export_all without validate_data=True should NOT raise (default off)
    # It will raise because export_data needs at least one file — so just confirm
    # validate_data=False doesn't surface the missing-data error
    try:
        manager.export_all(tmp_path, validate_data=False)
    except ValueError as exc:
        assert "no_data.csv" not in str(exc), (
            "validate_data=False should not raise about missing data"
        )

    # export_all with validate_data=True should raise before writing anything
    with pytest.raises(ValueError, match="no_data.csv"):
        manager.export_all(tmp_path, validate_data=True)

    # After adding data for the second file, validation passes
    manager.add_data(df, "no_data.csv")
    manager.validate_all_input_files_have_data()  # should not raise

    manager.export_all(tmp_path, validate_data=True)  # should not raise
    assert (tmp_path / "config.json").exists()
    assert (tmp_path / "with_data.csv").exists()
    assert (tmp_path / "no_data.csv").exists()
