import json
import os
import tempfile

import pandas as pd
import pytest

from dcp_tools import CustomDataManager
from dcp_tools.custom_data.data_management import (
    DEFAULT_GROUP_NAME,
    DEFAULT_STATVAR_MCF_NAME,
    DEFAULT_VERTICAL_SPECS_NAME,
)
from dcp_tools.custom_data.models.config_file import Config
from dcp_tools.custom_data.models.data_files import (
    ColumnMappings,
    InputFile,
)
from dcp_tools.custom_data.models.schema_nodes import EntityTypeNode, PropertyNode
from dcp_tools.custom_data.models.sources import ProvenanceNode, SourceNode
from dcp_tools.custom_data.models.stat_vars import StatVarGroupNode, StatVarNode


def test_custom_data_manager_add_provenance_and_override():
    """
    Verifies source/provenance addition logic in CustomDataManager.
    """
    manager = CustomDataManager()

    # add_provenance without a prior add_source must raise
    with pytest.raises(ValueError):
        manager.add_provenance(dcid="pA", url="http://prov", source="new_source")

    # add_source then add_provenance succeeds
    manager.add_source(dcid="new_source", url="http://src")
    manager.add_provenance(dcid="pA", url="http://prov", source="new_source")

    prov_nodes = manager._mcf_nodes["provenance.mcf"].nodes
    source_node = next(n for n in prov_nodes if n.type_of == "dcid:Source")
    assert isinstance(source_node, SourceNode)
    prov_node = next(n for n in prov_nodes if n.type_of == "dcid:Provenance")
    assert isinstance(prov_node, ProvenanceNode)
    assert source_node.dcid == "dcid:source/new_source"
    assert prov_node.dcid == "dcid:provenance/pA"
    assert prov_node.source == "dcid:source/new_source"

    # duplicate provenance without override raises
    with pytest.raises(ValueError):
        manager.add_provenance(dcid="pA", url="http://prov2", source="new_source")

    # override replaces the node
    manager.add_provenance(
        dcid="pA", url="http://prov2", source="new_source", override=True
    )
    updated_prov = next(
        n
        for n in manager._mcf_nodes["provenance.mcf"].nodes
        if n.type_of == "dcid:Provenance"
    )
    # url is stored raw; QuotedStr serialization wraps it in quotes at dump time
    assert updated_prov.url == "http://prov2"
    assert updated_prov.model_dump()["url"] == '"http://prov2"'


def test_add_source_metadata_lands_on_node():
    """Metadata kwargs on add_source are stored on the Source node."""
    manager = CustomDataManager()
    manager.add_source(
        dcid="MySource",
        name="My Source",
        url="http://mysource.org",
        description="A test source",
        license="CC-BY-4.0",
    )
    nodes = manager._mcf_nodes["provenance.mcf"].nodes
    node = next(n for n in nodes if n.type_of == "dcid:Source")
    assert isinstance(node, SourceNode)
    assert node.dcid == "dcid:source/MySource"
    assert node.name == "My Source"
    # QuotedStr fields are stored raw; quotes applied at serialization
    assert node.description == "A test source"
    assert node.license == "CC-BY-4.0"


def test_add_provenance_metadata_lands_on_node():
    """Metadata kwargs on add_provenance are stored on the Provenance node."""
    manager = CustomDataManager()
    manager.add_source(dcid="SrcX", url="http://srcx.org")
    manager.add_provenance(
        dcid="ProvX",
        name="Prov X",
        url="http://provx.org",
        source="SrcX",
        description="Prov desc",
        last_data_refresh_date="2024-01-01",
    )
    nodes = manager._mcf_nodes["provenance.mcf"].nodes
    prov_node = next(n for n in nodes if n.type_of == "dcid:Provenance")
    assert isinstance(prov_node, ProvenanceNode)
    # QuotedStr fields are stored raw; quotes applied at serialization
    assert prov_node.dcid == "dcid:provenance/ProvX"
    assert prov_node.name == "Prov X"
    assert prov_node.description == "Prov desc"
    assert prov_node.last_data_refresh_date == "2024-01-01"


def test_validate_provenances_raises_for_unknown_provenance(tmp_path):
    """An inputFile referencing a provenance with no matching node raises at export."""
    manager = CustomDataManager()
    # Register a file with a provenance that has no corresponding MCF node
    manager._config.input_files.append(
        InputFile(
            filename="x.csv",
            provenance="dcid:provenance/ghost",
            column_mappings=ColumnMappings(),
        )
    )
    with pytest.raises(ValueError, match="ghost"):
        manager.export_config(tmp_path)


def test_set_additional_config_fields():
    manager = CustomDataManager()

    manager.set_default_custom_root_stat_var_group_name("My Root Group")
    manager.set_custom_id_namespace("test_ns")
    # Default prefix should be auto-populated when namespace is set
    assert manager._config.custom_svg_prefix == "test_ns/g/"

    manager.set_custom_svg_prefix("test_ns/groups/")
    manager.set_sv_hierarchy_props_blocklist(
        [
            "statType",
            "measurementQualifier",
            "statType",
        ]
    )

    assert manager._config.default_custom_root_stat_var_group_name == "My Root Group"
    assert manager._config.custom_id_namespace == "test_ns"
    assert manager._config.custom_svg_prefix == "test_ns/groups/"
    assert manager._config.sv_hierarchy_props_blocklist == [
        "statType",
        "measurementQualifier",
    ]


def test_import_name_set_and_export_default(tmp_path):
    """set_importName stores the value; export_config defaults it to the dir name."""
    # explicit importName survives export unchanged
    manager = CustomDataManager()
    manager.set_import_name("MyImport")
    assert manager._config.import_name == "MyImport"
    out = tmp_path / "OECD_wage_data"
    out.mkdir()
    manager.export_config(out)
    assert Config.from_json(str(out / "config.json")).import_name == "MyImport"

    # unset importName defaults to each export directory name without mutating state,
    # so re-exporting the same manager elsewhere picks up the new directory's name.
    manager2 = CustomDataManager()
    out2 = tmp_path / "frog_data"
    out2.mkdir()
    manager2.export_config(out2)
    assert Config.from_json(str(out2 / "config.json")).import_name == "frog_data"
    assert manager2._config.import_name is None

    out3 = tmp_path / "toad_data"
    out3.mkdir()
    manager2.export_config(out3)
    assert Config.from_json(str(out3 / "config.json")).import_name == "toad_data"


def test_add_input_file_registration_and_override(tmp_path):
    """
    Verifies input file registration in config and data,
    and override/error behaviors.
    """
    manager = CustomDataManager()
    manager.add_source(dcid="s1", url="http://src")
    manager.add_provenance(dcid="p1", url="http://prov", source="s1")

    df3 = pd.DataFrame({"entity": ["e1"], "Year": [2020], "Value": [100]})
    manager.add_input_file(
        file_name="input.csv",
        provenance="p1",
        data=df3,
        column_mappings={
            "observationAbout": "entity",
            "date": "Year",
            "value": "Value",
        },
    )
    assert any(e.filename == "input.csv" for e in manager._config.input_files)
    assert "input.csv" in manager._data

    with pytest.raises(ValueError):
        manager.add_input_file(
            file_name="input.csv",
            provenance="p1",
        )

    df_new = pd.DataFrame({"entity": ["e2"], "Year": [2021], "Value": [200]})
    manager.add_input_file(
        file_name="input.csv",
        provenance="p1",
        data=df_new,
        override=True,
    )
    pd.testing.assert_frame_equal(manager._data["input.csv"], df_new)

    df4 = pd.DataFrame({"X": [1]})
    with pytest.raises(ValueError):
        manager.add_data(df4, "no_file.csv")


def test_add_input_file_without_column_mappings():
    """Ensure missing columnMappings defaults to empty dict without error."""
    manager = CustomDataManager()
    manager.add_source(dcid="s1", url="http://src")
    manager.add_provenance(dcid="p1", url="http://prov", source="s1")

    df = pd.DataFrame({"A": [1]})
    manager.add_input_file(file_name="input.csv", provenance="p1", data=df)

    entry = next(e for e in manager._config.input_files if e.filename == "input.csv")
    assert isinstance(entry, InputFile)
    mappings = entry.column_mappings
    assert mappings.model_dump(exclude_none=True) == {}


def test_add_input_file_pattern_xor_filename():
    """add_input_file raises when neither or both of file_name/pattern are given."""
    manager = CustomDataManager()
    manager.add_source(dcid="s1", url="http://src")
    manager.add_provenance(dcid="p1", url="http://prov", source="s1")

    with pytest.raises(ValueError, match="Exactly one"):
        manager.add_input_file(provenance="p1")

    with pytest.raises(ValueError, match="Exactly one"):
        manager.add_input_file(file_name="a.csv", pattern="a*", provenance="p1")


def test_add_mcf_file_requires_mcf_extension():
    """add_mcf_file rejects a name that is not an MCF file."""
    manager = CustomDataManager()

    with pytest.raises(ValueError, match=r"should match pattern"):
        manager.add_mcf_file("nodes.csv", provenance="p1")


def test_export_methods(tmp_path):
    """
    Exercises export_config, export_data, and export_mcf_file.
    """
    manager = CustomDataManager()
    manager.add_source(dcid="s1", url="http://src")
    manager.add_provenance(dcid="p1", url="http://prov", source="s1")
    df = pd.DataFrame({"A": [1]})
    manager.add_input_file(
        file_name="data.csv",
        provenance="p1",
        data=df,
        column_mappings={"observationAbout": "A"},
    )
    manager.add_variable_to_mcf(dcid="dcid:vX", name="VX")

    manager.export_config(tmp_path)
    config_file = tmp_path / "config.json"
    assert config_file.exists()
    loaded = Config.from_json(str(config_file))
    assert isinstance(loaded, Config)

    manager.export_data(tmp_path)
    data_file = tmp_path / "data.csv"
    assert data_file.exists()

    manager.export_mcf_file(tmp_path, mcf_file_name="custom_nodes.mcf")
    mcf_file = tmp_path / "custom_nodes.mcf"
    assert mcf_file.exists()
    assert "Node: dcid:vX" in mcf_file.read_text()


def test_export_data_creates_missing_subdirectory(tmp_path):
    """export_data creates the parent directory for a nested file_name."""
    manager = CustomDataManager()
    manager.add_source(dcid="S", url="http://s")
    manager.add_provenance(dcid="P", url="http://p", source="S")
    manager.set_include_input_subdirs(True)
    manager.add_input_file(
        file_name="sub/gdp.csv",
        provenance="P",
        data=pd.DataFrame({"a": [1]}),
        column_mappings={"value": "a"},
    )

    manager.export_data(tmp_path)

    assert (tmp_path / "sub" / "gdp.csv").exists()


def test_export_mcf_file_creates_missing_subdirectory(tmp_path):
    """export_mcf_file creates the parent directory for a nested mcf_file_name."""
    manager = CustomDataManager()
    manager.add_variable_to_mcf(
        dcid="dcid:vX", name="VX", mcf_file_name="sub/custom_nodes.mcf"
    )

    manager.export_mcf_file(tmp_path, mcf_file_name="sub/custom_nodes.mcf")

    assert (tmp_path / "sub" / "custom_nodes.mcf").exists()


def test_export_vertical_specs_creates_missing_subdirectory(tmp_path):
    """export_vertical_specs creates the parent directory for a nested verticalSpecsFile."""
    manager = CustomDataManager()
    manager.add_vertical_spec(
        verticals=["PersonCountVertical"], file_name="sub/vertical_specs.json"
    )

    manager.export_vertical_specs(tmp_path)

    assert (tmp_path / "sub" / "vertical_specs.json").exists()


def test_export_all_overwrites_correctly(tmp_path):
    """export_all overwrites correctly."""
    manager = CustomDataManager()

    manager.add_variable_to_mcf(
        dcid="MyVariable",
        name="My Variable",
    )
    manager.export_all(tmp_path)
    assert (tmp_path / "custom_nodes.mcf").read_text() == (
        "Node: dcid:MyVariable\n"
        'name: "My Variable"\n'
        "typeOf: dcid:StatisticalVariable\n"
        "statType: dcid:measuredValue\n\n"
    )

    manager.remove_variable("dcid:MyVariable")
    manager.export_all(tmp_path)
    assert (tmp_path / "custom_nodes.mcf").read_text() == ""


def test_add_variable_group_to_mcf_and_override():
    """
    Checks StatVarGroup node addition and override behavior.
    """
    manager = CustomDataManager()
    manager.add_variable_group_to_mcf(
        dcid="dcid:test/g/1", name="Group1", specialization_of="dcid:dc/g/Root"
    )
    groups = manager._mcf_nodes[DEFAULT_GROUP_NAME].nodes
    assert any(
        isinstance(n, StatVarGroupNode)
        and n.dcid == "dcid:test/g/1"
        and n.specialization_of == "dcid:dc/g/Root"
        for n in groups
    )

    manager.add_variable_group_to_mcf(
        dcid="dcid:test/g/1",
        name="Group2",
        specialization_of="dcid:dc/g/Root",
        override=True,
    )
    updated = manager._mcf_nodes[DEFAULT_GROUP_NAME].nodes
    assert any(n.name == "Group2" for n in updated if n.dcid == "dcid:test/g/1")


def test_add_variables_to_mcf_from_csv_parse_groups(tmp_path):
    """
    Checks that parse_groups/group_namespace are forwarded correctly: StatVars
    and the minted StatVarGroup nodes both land in the target MCF file.
    """
    csv_path = tmp_path / "vars.csv"
    csv_path.write_text(
        "Node,name,typeOf,memberOf\n"
        "dcid:n1,Name1,dcid:StatisticalVariable,Economic/Employment\n"
    )

    manager = CustomDataManager()
    manager.add_variables_to_mcf_from_csv(
        str(csv_path), parse_groups=True, group_namespace="ns"
    )

    nodes = manager._mcf_nodes[DEFAULT_STATVAR_MCF_NAME].nodes
    node_ids = [n.dcid for n in nodes]
    assert node_ids == ["dcid:n1", "dcid:ns/g/economic", "dcid:ns/g/employment"]

    statvar = next(n for n in nodes if n.dcid == "dcid:n1")
    assert isinstance(statvar, StatVarNode)
    assert statvar.member_of == "dcid:ns/g/employment"


def test_add_variables_to_mcf_from_csv_rejects_namespace_without_parse_groups(
    tmp_path,
):
    """group_namespace without parse_groups=True stays a ValueError."""
    csv_path = tmp_path / "vars.csv"
    csv_path.write_text("Node,name,typeOf\ndcid:n1,Name1,dcid:StatisticalVariable\n")

    manager = CustomDataManager()
    with pytest.raises(
        ValueError, match="group_namespace should not be set if parse_groups is False"
    ):
        manager.add_variables_to_mcf_from_csv(str(csv_path), group_namespace="ns")


def test_config_round_trip(tmp_path):
    """
    Ensures a Config can be dumped to JSON and loaded back identically.
    """
    cfg = Config(input_files=[])
    path = tmp_path / "cfg.json"
    path.write_text(cfg.model_dump_json())
    loaded = Config.from_json(str(path))
    assert loaded.model_dump() == cfg.model_dump()


def test_custom_data_manager_repr():
    """
    Sanity-check CustomDataManager.__repr__ for correct counts.
    """
    manager = CustomDataManager()
    manager.add_source(dcid="s1", url="http://src")
    manager.add_provenance(dcid="p1", url="http://prov", source="s1")
    df = pd.DataFrame({"A": [1]})
    manager.add_input_file(
        file_name="f.csv",
        provenance="p1",
        data=df,
        column_mappings={"observationAbout": "A"},
    )
    manager.add_variable_to_mcf(dcid="dcid:vX", name="VX")
    r = repr(manager)
    assert "1 inputFiles" in r
    assert "1 containing data" in r
    assert "1 sources" in r
    assert "1 provenances" in r
    assert "1 variables" in r


def test_remove_variable():
    manager = CustomDataManager()
    manager.add_source(dcid="s1", url="http://src")
    manager.add_provenance(dcid="p1", url="http://prov", source="s1")

    df = pd.DataFrame({"A": [1]})
    manager.add_input_file(
        file_name="a.csv",
        provenance="p1",
        data=df,
        column_mappings={"observationAbout": "A"},
    )
    manager.add_variable_to_mcf(dcid="dcid:sv1", name="Var", provenance="p1")

    manager.remove_variable("dcid:sv1")
    for nodes in manager._mcf_nodes.values():
        assert all(n.dcid != "dcid:sv1" for n in nodes.nodes)

    with pytest.raises(ValueError):
        manager.remove_variable("missing")


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
        InputFile(
            filename=key,
            provenance=prov,
            column_mappings=ColumnMappings(),
        )
    ]
    return Config(
        input_files=input_files,
        include_input_subdirs=include_subdirs,
        group_stat_vars_by_property=group_by_property,
        default_custom_root_stat_var_group_name=root_group_name,
        custom_id_namespace=custom_namespace,
        custom_svg_prefix=custom_svg_prefix,
        sv_hierarchy_props_blocklist=sv_blocklist,
        data_download_url=data_download_url,
        vertical_specs_file=vertical_specs_file,
    )


def test_set_data_download_url():
    manager = CustomDataManager()
    manager.set_data_download_url(["u1", "u2"])
    assert manager._config.data_download_url == ["u1", "u2"]

    manager.set_data_download_url(None)
    assert manager._config.data_download_url is None


def test_add_data_download_url_initializes_and_appends():
    manager = CustomDataManager()

    # Initializes from unset
    manager.add_data_download_url("u1")
    assert manager._config.data_download_url == ["u1"]

    # Appends to existing list
    manager.add_data_download_url("u2")
    assert manager._config.data_download_url == ["u1", "u2"]

    # Unset then re-initialize
    manager.set_data_download_url(None)
    manager.add_data_download_url("u3")
    assert manager._config.data_download_url == ["u3"]


def test_set_vertical_specs_file():
    manager = CustomDataManager()
    manager.set_vertical_specs_file("vs.json")
    assert manager._config.vertical_specs_file == "vs.json"

    manager.set_vertical_specs_file(None)
    assert manager._config.vertical_specs_file is None


def test_add_vertical_spec_appends_and_wires_config():
    manager = CustomDataManager()
    manager.add_vertical_spec(
        verticals=["PersonCountVertical"],
        population_type="Person",
        measured_properties=["count"],
    )

    # Auto-wires verticalSpecsFile to the default name on first use
    assert manager._config.vertical_specs_file == DEFAULT_VERTICAL_SPECS_NAME
    assert len(manager._vertical_specs) == 1
    spec = manager._vertical_specs[0]
    assert spec.population_type == "Person"
    assert spec.measured_properties == ["count"]
    assert spec.verticals == ["PersonCountVertical"]


def test_add_vertical_spec_respects_existing_and_explicit_filename():
    # A filename set beforehand is left untouched by the default path
    manager = CustomDataManager()
    manager.set_vertical_specs_file("custom.json")
    manager.add_vertical_spec(verticals=["v"])
    assert manager._config.vertical_specs_file == "custom.json"

    # An explicit file_name overrides
    manager.add_vertical_spec(verticals=["v2"], file_name="other.json")
    assert manager._config.vertical_specs_file == "other.json"


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


def test_add_input_file_observation_properties():
    manager = CustomDataManager()

    manager.add_input_file(
        "data.csv",
        provenance="prov1",
        column_mappings={"observationAbout": "Country", "date": "Year"},
        observation_properties={"unit": "USDollar", "customProp": "x"},
    )

    entry = manager._config.input_files[0]
    assert isinstance(entry, InputFile)
    assert entry.observation_properties is not None
    assert entry.observation_properties.unit == "USDollar"
    assert entry.observation_properties.__pydantic_extra__["customProp"] == "x"
    # columnMappings coexists
    assert entry.column_mappings is not None

    # Omitting the kwarg leaves observationProperties absent (None)
    manager.add_input_file(
        "other.csv",
        provenance="prov1",
    )
    other_entry = manager._config.input_files[1]
    assert other_entry.observation_properties is None


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
    assert manager._config.data_download_url == ["u1"]

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
    assert manager2._config.data_download_url == ["u2"]


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
    assert manager._config.vertical_specs_file == "vs.json"


def test_merge_configs_from_directory(tmp_path):
    d1 = tmp_path / "one"
    d1.mkdir()
    cfg1 = _make_cfg(
        "a.csv",
        "p1",
        custom_namespace="ns",
        sv_blocklist=["measurementDenominator"],
    )
    cfg1.include_input_subdirs = True
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

    filenames = {e.filename for e in manager._config.input_files}
    assert filenames == {"a.csv", "b.csv"}
    assert manager._config.include_input_subdirs is True
    assert manager._config.custom_id_namespace == "ns"
    # Blocklist remains the one provided explicitly (none defined in the second config).
    assert manager._config.sv_hierarchy_props_blocklist == ["measurementDenominator"]


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
    assert manager._config.sv_hierarchy_props_blocklist == ["statType", "unit"]


def test_rename_variable_mcf_only():
    """rename_variable operates on MCF nodes exclusively (no config.variables)."""
    manager = CustomDataManager()
    manager.add_variable_to_mcf(dcid="dcid:v1", name="Var1")

    manager.rename_variable("dcid:v1", "dcid:v2")
    for nodes in manager._mcf_nodes.values():
        assert any(n.dcid == "dcid:v2" for n in nodes.nodes)
    for nodes in manager._mcf_nodes.values():
        assert all(n.dcid != "dcid:v1" for n in nodes.nodes)

    # Renaming a missing variable raises ValueError
    with pytest.raises(ValueError):
        manager.rename_variable("missing", "dcid:v3")

    # Renaming to an existing MCF node name raises ValueError
    manager.add_variable_to_mcf(dcid="dcid:v3", name="Var3")
    with pytest.raises(ValueError):
        manager.rename_variable("dcid:v2", "dcid:v3")


def test_rename_variable_mints_bare_tokens():
    """Both old_name and new_name are run through ensure_dcid (#131), consistent
    with add_variable_to_mcf (#130). A bare old_name used to fail the lookup (it
    never matched the stored dcid:-prefixed Node), so minting both is strictly an
    improvement, not a behaviour change any test pinned."""
    manager = CustomDataManager()
    manager.add_variable_to_mcf(dcid="dcid:v1", name="Var1")

    manager.rename_variable("v1", "v2")

    for nodes in manager._mcf_nodes.values():
        assert any(n.dcid == "dcid:v2" for n in nodes.nodes)
        assert all(n.dcid != "dcid:v1" for n in nodes.nodes)


def test_rename_variable_keeps_lookup_index_consistent():
    """A renamed node is addressable by its new name, and its old name is freed."""
    manager = CustomDataManager()
    manager.add_variable_to_mcf(dcid="dcid:v1", name="Var1")
    manager.rename_variable("dcid:v1", "dcid:v2")

    # The old name no longer resolves...
    with pytest.raises(ValueError):
        manager.remove_variable("dcid:v1")

    # ...and the new one does.
    manager.remove_variable("dcid:v2")
    for nodes in manager._mcf_nodes.values():
        assert all(n.dcid not in {"dcid:v1", "dcid:v2"} for n in nodes.nodes)


def test_rename_variable_frees_the_old_name_for_reuse():
    """After a rename the old name is available again, and both nodes survive."""
    manager = CustomDataManager()
    manager.add_variable_to_mcf(dcid="dcid:v1", name="Var1")
    manager.rename_variable("dcid:v1", "dcid:v2")

    manager.add_variable_to_mcf(dcid="dcid:v1", name="A different Var1")

    stored = {n.dcid for nodes in manager._mcf_nodes.values() for n in nodes.nodes}
    assert {"dcid:v1", "dcid:v2"} <= stored


def test_validate_all_input_files_have_data(tmp_path):
    """Verify the optional data-completeness validation on export_all and the standalone method."""
    manager = CustomDataManager()
    manager.add_source(dcid="s1", url="http://src")
    manager.add_provenance(dcid="p1", url="http://prov", source="s1")

    df = pd.DataFrame({"A": [1, 2]})

    # Register one file WITH data and one WITHOUT data
    manager.add_input_file(
        file_name="with_data.csv",
        provenance="p1",
        data=df,
    )
    manager.add_input_file(
        file_name="no_data.csv",
        provenance="p1",
    )

    # Standalone validation method raises because no_data.csv has no data
    with pytest.raises(ValueError, match=r"no_data\.csv"):
        manager.validate_all_input_files_have_data()

    # validate_data=False does not surface the missing-data error
    manager.export_all(tmp_path, validate_data=False)

    # export_all with validate_data=True should raise before writing anything
    with pytest.raises(ValueError, match=r"no_data\.csv"):
        manager.export_all(tmp_path, validate_data=True)

    # After adding data for the second file, validation passes
    manager.add_data(df, "no_data.csv")
    manager.validate_all_input_files_have_data()  # should not raise

    manager.export_all(tmp_path, validate_data=True)  # should not raise
    assert (tmp_path / "config.json").exists()
    assert (tmp_path / "with_data.csv").exists()
    assert (tmp_path / "no_data.csv").exists()


def test_loading_legacy_variable_per_column_config_raises_with_message():
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
        date="Year",
        value="Val",
        unit="Unit_column",
        scaling_factor="Scale_column",
        measurement_method="Method_column",
        observation_period="Period_column",
        custom_dimensions={
            "sourceCountry": "Source",
            "destinationCountry": "Destination",
        },
    )

    result = cm.model_dump(by_alias=True, exclude_none=True)

    assert result == {
        "dcid:variableMeasured": "Var",
        "dcid:observationDate": "Year",
        "dcid:value": "Val",
        "dcid:unit": "Unit_column",
        "scalingFactor": "Scale_column",
        "dcid:measurementMethod": "Method_column",
        "dcid:observationPeriod": "Period_column",
        "custom:sourceCountry": "Source",
        "custom:destinationCountry": "Destination",
    }


def test_column_mappings_dump_respects_exclude_none_flag():
    cm = ColumnMappings(variable="Var", custom_dimensions={"sourceCountry": "Source"})
    assert cm.model_dump(exclude_none=True) == {
        "dcid:variableMeasured": "Var",
        "custom:sourceCountry": "Source",
    }

    full_dump = cm.model_dump()
    assert "dcid:observationDate" in full_dump
    assert full_dump["dcid:observationDate"] is None


def test_column_mappings_accepts_dcid_keys_on_input():
    """Verify ColumnMappings accepts dcid: keys on input (read-back guard)."""
    cm = ColumnMappings.model_validate(
        {
            "dcid:observationAbout": "Country",
            "dcid:observationDate": "Year",
            "dcid:value": "Val",
        }
    )
    assert cm.observation_about == "Country"
    assert cm.date == "Year"
    assert cm.value == "Val"

    # Short-key input must also still work
    cm2 = ColumnMappings.model_validate({"observationAbout": "Country"})
    assert cm2.observation_about == "Country"


def test_column_mappings_round_trip_preserves_custom_prefix():
    mappings_dict = {
        "dcid:variableMeasured": "statvar",
        "dcid:observationDate": "year",
        "dcid:value": "amount",
        "custom:sourceCountry": "provider",
        "custom:destinationCountry": "recipient",
    }
    result = ColumnMappings.model_validate(mappings_dict).model_dump(
        by_alias=True, exclude_none=True
    )
    assert result == mappings_dict


@pytest.mark.parametrize(
    "dimension_name", ["source country", "", None, " sourceCountry"]
)
def test_column_mappings_rejects_malformed_custom_dimension_names(dimension_name):
    with pytest.raises(ValueError):
        ColumnMappings(
            variable="Var",
            date="Year",
            value="Val",
            custom_dimensions={dimension_name: "Source"},
        )


# --- Schema node builder tests ---


def test_add_variable_to_mcf_normalizes_bare_node():
    """add_variable_to_mcf normalizes a bare Node to dcid:, matching the other builders."""
    manager = CustomDataManager()
    manager.add_variable_to_mcf(dcid="StatVar", name="Variable Name")
    node = manager._mcf_nodes[DEFAULT_STATVAR_MCF_NAME].nodes[0]
    assert node.dcid == "dcid:StatVar"


def test_add_variable_to_mcf_normalizes_bare_reference_fields():
    """The Dcid-typed reference kwargs accept bare tokens too, like Node."""
    manager = CustomDataManager()
    manager.add_variable_to_mcf(
        dcid="StatVar",
        name="Variable Name",
        population_type="Person",
        measured_property="count",
        measurement_qualifier="Commitment",
        measurement_denominator="Area",
    )
    node = manager._mcf_nodes[DEFAULT_STATVAR_MCF_NAME].nodes[0]
    assert isinstance(node, StatVarNode)
    assert node.population_type == "dcid:Person"
    assert node.measured_property == "dcid:count"
    assert node.measurement_qualifier == "dcid:Commitment"
    assert node.measurement_denominator == "dcid:Area"


def test_add_variable_to_mcf_passes_prefixed_reference_fields_through():
    """Already dcid:-prefixed values are not double-prefixed."""
    manager = CustomDataManager()
    manager.add_variable_to_mcf(
        dcid="dcid:StatVar",
        name="Variable Name",
        population_type="dcid:Person",
        measured_property="dcid:count",
    )
    node = manager._mcf_nodes[DEFAULT_STATVAR_MCF_NAME].nodes[0]
    assert isinstance(node, StatVarNode)
    assert node.dcid == "dcid:StatVar"
    assert node.population_type == "dcid:Person"
    assert node.measured_property == "dcid:count"


def test_add_entity_type_lands_node():
    """add_entity_type normalizes bare Node to dcid: and sets typeOf."""
    manager = CustomDataManager()
    manager.add_entity_type(dcid="MyClass", name="My Class")
    nodes = manager._mcf_nodes["custom_nodes.mcf"].nodes
    node = next(n for n in nodes if n.type_of == "dcid:Class")
    assert node.dcid == "dcid:MyClass"
    assert node.type_of == "dcid:Class"


def test_add_entity_type_dcid_prefixed_node_verbatim():
    """An already dcid:-prefixed Node is passed through verbatim."""
    manager = CustomDataManager()
    manager.add_entity_type(dcid="dcid:Already", name="x")
    nodes = manager._mcf_nodes["custom_nodes.mcf"].nodes
    node = nodes[0]
    assert node.dcid == "dcid:Already"


def test_add_event_type_default_subclassof():
    """add_event_type defaults subClassOf to dcid:Event."""
    manager = CustomDataManager()
    manager.add_event_type(dcid="Quake", name="Q")
    nodes = manager._mcf_nodes["custom_nodes.mcf"].nodes
    node = nodes[0]
    assert node.type_of == "dcid:Class"
    assert node.sub_class_of == "dcid:Event"


def test_add_event_type_subclassof_override():
    """A bare subClassOf override is normalized to dcid:."""
    manager = CustomDataManager()
    manager.add_event_type(dcid="Quake", name="Q", sub_class_of="DisasterEvent")
    node = manager._mcf_nodes["custom_nodes.mcf"].nodes[0]
    assert node.sub_class_of == "dcid:DisasterEvent"


def test_add_property_lands_node():
    """add_property emits a Property node with dcid:Property typeOf."""
    manager = CustomDataManager()
    manager.add_property(
        dcid="myProp",
        name="My Prop",
        domain_includes="dcid:Person",
        range_includes="dcid:Number",
    )
    node = manager._mcf_nodes["custom_nodes.mcf"].nodes[0]
    assert node.dcid == "dcid:myProp"
    assert node.type_of == "dcid:Property"
    assert isinstance(node, PropertyNode)
    assert node.domain_includes == "dcid:Person"
    assert node.range_includes == "dcid:Number"


def test_add_property_normalizes_bare_refs():
    """Bare domainIncludes/rangeIncludes/subPropertyOf refs are normalized to dcid:."""
    manager = CustomDataManager()
    manager.add_property(
        dcid="myProp",
        name="x",
        domain_includes="Person",
        range_includes=["Number", "dcid:Already"],
        sub_property_of="baseProp",
    )
    node = manager._mcf_nodes["custom_nodes.mcf"].nodes[0]
    assert isinstance(node, PropertyNode)
    assert node.domain_includes == "dcid:Person"
    assert node.range_includes == ["dcid:Number", "dcid:Already"]
    assert node.sub_property_of == "dcid:baseProp"


def test_add_unit_lands_node_and_typeof_override():
    """add_unit normalizes bare typeOf override and stores shortDisplayName."""
    manager = CustomDataManager()
    manager.add_unit(
        dcid="USD",
        name="US Dollar",
        short_display_name="$",
        type_of="CurrencyUnitOfMeasure",
    )
    node = manager._mcf_nodes["custom_nodes.mcf"].nodes[0]
    assert node.type_of == "dcid:CurrencyUnitOfMeasure"
    assert node.short_display_name == "$"


def test_add_measurement_method_lands_node_and_typeof_override():
    """add_measurement_method normalizes bare typeOf and allows absent name."""
    manager = CustomDataManager()
    manager.add_measurement_method(dcid="MyCensus", type_of="CensusSurveyEnum")
    node = manager._mcf_nodes["custom_nodes.mcf"].nodes[0]
    assert node.type_of == "dcid:CensusSurveyEnum"
    assert node.name is None


def test_included_in_expands_to_provenance_and_source():
    """includedIn expands to both the provenance dcid and its linked source dcid."""
    manager = CustomDataManager()
    manager.add_source(dcid="src", url="http://s")
    manager.add_provenance(dcid="prov", url="http://p", source="src")
    manager.add_entity_type(dcid="T", name="T", included_in="prov")

    entity_node = manager._mcf_nodes["custom_nodes.mcf"].nodes[0]
    assert isinstance(entity_node, EntityTypeNode)
    assert entity_node.included_in == ["dcid:provenance/prov", "dcid:source/src"]
    assert (
        entity_node.model_dump()["includedIn"]
        == "dcid:provenance/prov, dcid:source/src"
    )


def test_included_in_accepts_list_of_provenances():
    """A list of provenance names expands all four dcids in order."""
    manager = CustomDataManager()
    manager.add_source(dcid="srcA", url="http://a")
    manager.add_source(dcid="srcB", url="http://b")
    manager.add_provenance(dcid="provA", url="http://pa", source="srcA")
    manager.add_provenance(dcid="provB", url="http://pb", source="srcB")
    manager.add_entity_type(dcid="T", name="T", included_in=["provA", "provB"])

    node = manager._mcf_nodes["custom_nodes.mcf"].nodes[0]
    assert isinstance(node, EntityTypeNode)
    assert node.included_in == [
        "dcid:provenance/provA",
        "dcid:source/srcA",
        "dcid:provenance/provB",
        "dcid:source/srcB",
    ]


def test_included_in_dedups_shared_source():
    """Two provenances sharing a source emit that source exactly once."""
    manager = CustomDataManager()
    manager.add_source(dcid="src", url="http://s")
    manager.add_provenance(dcid="provA", url="http://pa", source="src")
    manager.add_provenance(dcid="provB", url="http://pb", source="src")
    manager.add_entity_type(dcid="T", name="T", included_in=["provA", "provB"])

    node = manager._mcf_nodes["custom_nodes.mcf"].nodes[0]
    assert isinstance(node, EntityTypeNode)
    # provA is processed first: emits provenance/provA then source/src.
    # provB is processed second: emits provenance/provB; source/src already seen → skipped.
    assert node.included_in == [
        "dcid:provenance/provA",
        "dcid:source/src",
        "dcid:provenance/provB",
    ]


def test_included_in_raises_for_missing_provenance():
    """includedIn referencing an unregistered provenance raises ValueError."""
    manager = CustomDataManager()
    with pytest.raises(ValueError, match="ghost"):
        manager.add_event_type(dcid="E", name="E", included_in="ghost")


def test_add_entity_type_override():
    """Duplicate Node without override raises; with override=True replaces."""
    manager = CustomDataManager()
    manager.add_entity_type(dcid="T", name="First")
    with pytest.raises(ValueError):
        manager.add_entity_type(dcid="T", name="Second")
    manager.add_entity_type(dcid="T", name="Updated", override=True)
    node = manager._mcf_nodes["custom_nodes.mcf"].nodes[0]
    assert node.name == "Updated"


def test_add_unit_custom_mcf_file_name():
    """add_unit with mcf_file_name lands the node in the specified file."""
    manager = CustomDataManager()
    manager.add_unit(dcid="MyUnit", name="My Unit", mcf_file_name="units.mcf")
    assert "units.mcf" in manager._mcf_nodes
    assert "custom_nodes.mcf" not in manager._mcf_nodes or not any(
        n.dcid == "dcid:MyUnit"
        for n in manager._mcf_nodes.get(
            "custom_nodes.mcf", type("", (), {"nodes": []})()
        ).nodes
    )
    node = manager._mcf_nodes["units.mcf"].nodes[0]
    assert node.dcid == "dcid:MyUnit"
