import json
from pathlib import Path

from bblocks.datacommons_tools.custom_data.data_management import CustomDataManager
from bblocks.datacommons_tools.custom_data.models.config_file import Config
from bblocks.datacommons_tools.custom_data.models.mcf import MCFNode
from bblocks.datacommons_tools.custom_data.schema_tools import csv_metadata_to_nodes

GOLDEN_DIR = Path(__file__).parent / "goldens"


def test_mcfnode_snapshot():
    got = (GOLDEN_DIR / "sample_node.mcf").read_text()

    node = MCFNode(
        Node="dcid:X/foo",
        name='"Some Name"',
        typeOf="dcid:StatisticalVariable",
        dcid="dcid:foo",
        description='"Foo description',
        provenance='"Some foo provenance"',
        shortDisplayName='"F"',
        subClassOf="dcid:Parent",
    )
    assert node.mcf.strip() == got


def test_config_json_snapshot(tmp_path):
    manager = CustomDataManager()
    manager.set_includeInputSubdirs(True).set_groupStatVarsByProperty(False)

    manager.add_implicit_schema_file(
        "a.csv",
        provenance="provA",
        observationProperties={"unit": "USDollar"},
        entityType="Country",
    )
    manager.add_explicit_schema_file(
        "b.csv",
        provenance="provB",
        columnMappings={"entity": "Country", "date": "Year", "value": "Val"},
    )
    # add variable and source
    manager.add_provenance("provA", "http://prova/", "S1", source_url="http://source1/")
    manager.add_provenance("provB", "http://provb/", "S1", source_url="http://source1/")
    manager.add_variable_to_config("v1", name="Var One")

    # export
    manager.export_config(str(tmp_path))
    got = json.loads(Path(tmp_path / "config.json").read_text())
    expected = json.loads((GOLDEN_DIR / "config.json").read_text())
    assert got == expected


def test_full_mcf_export(tmp_path):
    mgr = CustomDataManager()
    mgr.add_variable_group_to_mcf(
        Node="dcid:one/g/group1", name="Group One", specializationOf="dcid:dc/g/Root"
    )
    mgr.add_variable_to_mcf(
        Node="dcid:var/one",
        name="Test Var",
        description="Test var",
        memberOf="dcid:one/g/group1",
    )
    mgr.export_mfc_file(str(tmp_path), mcf_file_name="custom_nodes.mcf")
    got = (tmp_path / "custom_nodes.mcf").read_text()
    expected = (GOLDEN_DIR / "custom_nodes.mcf").read_text()
    assert got == expected


def test_csv_to_mcf_snapshot():

    nodes = csv_metadata_to_nodes(GOLDEN_DIR / "sample.csv", ignore_columns=None)
    got = nodes.mcf if hasattr(nodes, "mcf") else "".join(n.mcf for n in nodes.nodes)
    expected = (GOLDEN_DIR / "sample_csv_nodes.mcf").read_text()
    assert got == expected


def test_round_trip_config_snapshot(tmp_path):

    # manually build dict
    data = json.loads((GOLDEN_DIR / "config.json").read_text())
    # write and read
    config_file = tmp_path / "c.json"
    config_file.write_text(json.dumps(data))

    config_file = Config.from_json(str(config_file))

    got = config_file.model_dump_json(indent=4, exclude_none=True, by_alias=True)
    expected = json.dumps(data, indent=4)
    assert json.loads(got) == json.loads(expected)
