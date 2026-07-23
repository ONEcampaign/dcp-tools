import json
from pathlib import Path

import pytest

from dcp_tools.custom_data.data_management import CustomDataManager
from dcp_tools.custom_data.models.config_file import Config
from dcp_tools.custom_data.models.mcf import Node
from dcp_tools.custom_data.schema_tools import csv_metadata_to_nodes

GOLDEN_DIR = Path(__file__).parent / "goldens"


def test_node_snapshot():
    got = (GOLDEN_DIR / "sample_node.mcf").read_text()

    node = Node(
        dcid="dcid:X/foo",
        name='"Some Name"',
        typeOf="dcid:StatisticalVariable",
        description='"Foo description',
        provenance='"Some foo provenance"',
        shortDisplayName='"F"',
        subClassOf="dcid:Parent",
    )
    assert node.mcf.strip() == got


def test_config_json_snapshot(tmp_path):
    manager = CustomDataManager()
    manager.set_importName("test_import")
    manager.set_includeInputSubdirs(True).set_groupStatVarsByProperty(False)

    manager.add_source(name="S1", url="http://source1")
    manager.add_provenance(name="provA", url="http://prova", source="S1")
    manager.add_provenance(name="provB", url="http://provb", source="S1")

    manager.add_input_file(
        "a.csv",
        provenance="provA",
        columnMappings={"observationAbout": "Country", "date": "Year", "value": "Val"},
    )
    manager.add_input_file(
        "b.csv",
        provenance="provB",
        columnMappings={"observationAbout": "Country", "date": "Year", "value": "Val"},
    )

    # export
    manager.export_config(str(tmp_path))
    got = json.loads(Path(tmp_path / "config.json").read_text())
    expected = json.loads((GOLDEN_DIR / "config.json").read_text())
    assert "sources" not in got
    assert got == expected


def test_config_json_snapshot_multi_entity(tmp_path):
    manager = CustomDataManager()
    manager.set_importName("test_import_multi_entity")
    manager.add_source(name="S1", url="http://source1")
    manager.add_provenance(name="provC", url="http://provc", source="S1")
    manager.add_input_file(
        "c.csv",
        provenance="provC",
        columnMappings={
            "dcid:observationDate": "Year",
            "dcid:value": "Val",
            "dcid:variableMeasured": "Var",
            "custom:originCountry": "Provider",
            "custom:destinationCountry": "Recipient",
        },
    )
    manager.export_config(str(tmp_path))

    got = json.loads(Path(tmp_path / "config.json").read_text())
    expected = json.loads((GOLDEN_DIR / "config_multi_entity.json").read_text())
    assert got == expected


def test_provenance_mcf_snapshot(tmp_path):
    manager = CustomDataManager()
    manager.add_source(name="S1", url="http://source1")
    manager.add_provenance(name="provA", url="http://prova", source="S1")
    manager.add_provenance(name="provB", url="http://provb", source="S1")

    manager.export_mcf_file(str(tmp_path), mcf_file_name="provenance.mcf")
    got = (tmp_path / "provenance.mcf").read_text()
    expected = (GOLDEN_DIR / "provenance.mcf").read_text()
    assert got == expected


def test_full_mcf_export(tmp_path):
    mgr = CustomDataManager()
    mgr.add_variable_group_to_mcf(
        dcid="dcid:one/g/group1", name="Group One", specializationOf="dcid:dc/g/Root"
    )
    mgr.add_variable_to_mcf(
        dcid="dcid:var/one",
        name="Test Var",
        description="Test var",
        memberOf="dcid:one/g/group1",
    )
    mgr.export_mcf_file(str(tmp_path), mcf_file_name="custom_nodes.mcf")
    got = (tmp_path / "custom_nodes.mcf").read_text()
    expected = (GOLDEN_DIR / "custom_nodes.mcf").read_text()
    assert got == expected


def test_mcf_export_multi_entity(tmp_path):
    manager = CustomDataManager()
    manager.add_variable_to_mcf(
        dcid="dcid:var/one",
        name="Test Var",
        description="Test var",
        observationProperties=["dcid:originCountry", "dcid:destinationCountry"],
    )

    manager.export_mcf_file(str(tmp_path), mcf_file_name="custom_nodes.mcf")

    got = (tmp_path / "custom_nodes.mcf").read_text()
    expected = (GOLDEN_DIR / "custom_nodes_multi_entity.mcf").read_text()
    assert got == expected


def test_csv_to_mcf_snapshot():

    nodes = csv_metadata_to_nodes(GOLDEN_DIR / "sample.csv", ignore_columns=None)
    got = nodes.mcf if hasattr(nodes, "mcf") else "".join(n.mcf for n in nodes.nodes)
    expected = (GOLDEN_DIR / "sample_csv_nodes.mcf").read_text()
    assert got == expected


@pytest.mark.parametrize(
    "golden_file", ["config.json", "config_all_fields.json", "config_multi_entity.json"]
)
def test_round_trip_config(tmp_path, golden_file):
    data = json.loads((GOLDEN_DIR / golden_file).read_text())
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(data))

    loaded = Config.from_json(str(config_file))

    got = loaded.model_dump_json(indent=4, exclude_none=True, by_alias=True)
    assert json.loads(got) == data
