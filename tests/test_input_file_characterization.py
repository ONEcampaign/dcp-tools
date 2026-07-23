"""Characterization tests for the custom-data input-file path.

These tests pin the CURRENT observable behavior of registering, exporting,
and serializing input files (InputFile / add_input_file / ColumnMappings)
through CustomDataManager and the config/data-file utilities.
"""

from unittest.mock import Mock

import pandas as pd
import pytest

from dcp_tools import CustomDataManager
from dcp_tools.custom_data.models.config_file import Config
from dcp_tools.custom_data.models.data_files import (
    ColumnMappings,
    InputFile,
)
from dcp_tools.gcp_utilities.storage import (
    get_missing_csv_files,
    get_unregistered_csv_files,
)

# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _manager(file_name="input.csv", *, with_data=True):
    """Manager with one source + one input file (optionally with data)."""
    mgr = CustomDataManager()
    mgr.add_source(name="s1", url="http://src")
    mgr.add_provenance(name="p1", url="http://prov", source="s1")
    df = pd.DataFrame({"entity": ["e1"], "Year": [2020], "Value": [100]})
    mgr.add_input_file(
        file_name=file_name,
        provenance="p1",
        data=df if with_data else None,
        columnMappings={"observationAbout": "entity", "date": "Year", "value": "Value"},
    )
    return mgr, df


def _make_cfg(
    key: str,
    prov: str,
    *,
    include_subdirs=None,
    custom_namespace=None,
    custom_svg_prefix=None,
    sv_blocklist=None,
):
    """Build a minimal Config with one InputFile."""
    input_files = [
        InputFile(
            filename=key,
            provenance=prov,
            columnMappings=ColumnMappings(
                observationAbout="Country", date="Year", value="Val"
            ),
        )
    ]
    return Config(
        inputFiles=input_files,
        includeInputSubdirs=include_subdirs,
        customIdNamespace=custom_namespace,
        customSvgPrefix=custom_svg_prefix,
        svHierarchyPropsBlocklist=sv_blocklist,
    )


# ---------------------------------------------------------------------------
# Slice 1: Manager-path characterization (B1, B5, B6, B8)
# ---------------------------------------------------------------------------


def test_add_input_file_registers_in_config_and_data():
    """add_input_file registers file in config and data store."""
    manager, df = _manager()

    entry = next(e for e in manager._config.inputFiles if e.filename == "input.csv")
    assert isinstance(entry, InputFile)
    assert entry.provenance == "dcid:provenance/p1"
    assert entry.columnMappings.observationAbout == "entity"
    assert entry.columnMappings.date == "Year"
    assert entry.columnMappings.value == "Value"
    assert entry.data_format == "variablePerRow"

    assert "input.csv" in manager._data
    pd.testing.assert_frame_equal(manager._data["input.csv"], df)


def test_add_input_file_override_and_duplicate_error():
    """Re-adding the same file_name without override raises ValueError;
    with override=True the data is replaced."""
    manager, _ = _manager()

    df_new = pd.DataFrame({"entity": ["e2"], "Year": [2021], "Value": [200]})

    # Duplicate without override must raise
    with pytest.raises(ValueError):
        manager.add_input_file("input.csv", provenance="p1")

    # Override succeeds and replaces stored data
    manager.add_input_file(
        file_name="input.csv",
        provenance="p1",
        data=df_new,
        columnMappings={"observationAbout": "entity", "date": "Year", "value": "Value"},
        override=True,
    )
    pd.testing.assert_frame_equal(manager._data["input.csv"], df_new)


def test_add_data_standalone_success_and_error():
    """Standalone add_data: success path, duplicate error, override, unregistered error."""
    manager, _ = _manager(with_data=False)

    # Data was not supplied at registration time
    assert "input.csv" not in manager._data

    df = pd.DataFrame({"entity": ["e1"], "Year": [2020], "Value": [100]})

    # First add_data call succeeds
    manager.add_data(df, "input.csv")
    pd.testing.assert_frame_equal(manager._data["input.csv"], df)

    # Second call without override raises
    with pytest.raises(ValueError):
        manager.add_data(df, "input.csv")

    # Override succeeds
    df2 = pd.DataFrame({"entity": ["e2"], "Year": [2021], "Value": [200]})
    manager.add_data(df2, "input.csv", override=True)
    pd.testing.assert_frame_equal(manager._data["input.csv"], df2)

    # Unregistered file raises
    with pytest.raises(ValueError):
        manager.add_data(df, "unregistered.csv")


def test_export_config_round_trip(tmp_path):
    """export_config writes config.json; Config.from_json reloads it correctly."""
    manager, _ = _manager()

    manager.export_config(tmp_path)

    config_file = tmp_path / "config.json"
    assert config_file.exists()

    loaded = Config.from_json(str(config_file))
    assert isinstance(loaded, Config)

    entry = next(e for e in loaded.inputFiles if e.filename == "input.csv")
    mappings = entry.columnMappings
    assert mappings.model_dump(exclude_none=True) == {
        "observationAbout": "entity",
        "date": "Year",
        "value": "Value",
    }
    assert entry.data_format == "variablePerRow"


def test_config_to_dict_shape():
    """config_to_dict returns the expected serialized shape for an InputFile entry.

    Pins the key names and values. The keys use the DC-import aliases:
    'format' for the data format and the 'dcid:' predicate forms for
    columnMappings.
    """
    manager, _ = _manager()

    d = manager.config_to_dict()
    entries = d["inputFiles"]
    entry = next(e for e in entries if e.get("filename") == "input.csv")

    expected = {
        "filename": "input.csv",
        "provenance": "dcid:provenance/p1",
        "format": "variablePerRow",
        "columnMappings": {
            "dcid:observationAbout": "entity",
            "dcid:observationDate": "Year",
            "dcid:value": "Value",
        },
    }
    assert entry == expected


def test_export_mcf_file(tmp_path):
    """variable added via add_variable_to_mcf appears in exported MCF."""
    manager, _ = _manager()
    manager.add_variable_to_mcf(dcid="dcid:vX", name="VX")

    manager.export_mcf_file(tmp_path, mcf_file_name="custom_nodes.mcf")

    mcf_file = tmp_path / "custom_nodes.mcf"
    assert mcf_file.exists()
    assert "Node: dcid:vX" in mcf_file.read_text()


# ---------------------------------------------------------------------------
# Slice 2: Model- and util-path characterization (B2, B7, B9)
# ---------------------------------------------------------------------------


def test_input_file_default_format():
    """InputFile defaults data_format to 'variablePerRow';
    by_alias serialization uses key 'format'."""
    entry = InputFile(
        filename="a.csv",
        provenance="p",
        columnMappings=ColumnMappings(),
    )

    assert entry.data_format == "variablePerRow"
    assert entry.model_dump(by_alias=True)["format"] == "variablePerRow"


def test_config_build_and_from_json_round_trip(tmp_path):
    """A Config with one InputFile survives a serialize → deserialize cycle."""
    cfg = Config(
        inputFiles=[
            InputFile(
                filename="a.csv",
                provenance="p",
                columnMappings=ColumnMappings(
                    observationAbout="Country", date="Year", value="Val"
                ),
            )
        ],
    )

    path = tmp_path / "cfg.json"
    path.write_text(cfg.model_dump_json(by_alias=True))

    loaded = Config.from_json(str(path))
    assert loaded.model_dump() == cfg.model_dump()


def test_merge_configs_from_directory(tmp_path):
    """from_config_files_in_directory merges two configs correctly."""
    d1 = tmp_path / "one"
    d1.mkdir()
    cfg1 = _make_cfg(
        "a.csv",
        "p1",
        custom_namespace="ns",
        sv_blocklist=["measurementDenominator"],
    )
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


def test_merge_configs_from_directory_duplicate_error(tmp_path):
    """from_config_files_in_directory raises ValueError on duplicate keys."""
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


def test_get_unregistered_and_missing_csv_files():
    """get_unregistered_csv_files and get_missing_csv_files work with
    a Config that has one InputFile (they depend only on inputFiles)."""
    cfg = Config(
        inputFiles=[
            InputFile(
                filename="a.csv",
                provenance="p",
                columnMappings=ColumnMappings(
                    observationAbout="Country", date="Year", value="Val"
                ),
            )
        ],
    )

    # --- get_unregistered_csv_files ---
    bucket = Mock()
    blob_a = Mock()
    blob_a.name = "folder/a.csv"
    blob_extra = Mock()
    blob_extra.name = "folder/extra.csv"
    bucket.list_blobs.return_value = [blob_a, blob_extra]
    bucket.name = "my-bucket"

    unregistered = get_unregistered_csv_files(bucket, cfg, gcs_folder_name="folder")
    assert unregistered == ["extra.csv"]

    # --- get_missing_csv_files ---
    cfg.inputFiles.append(
        InputFile(
            filename="extra.csv",
            provenance="p",
            columnMappings=ColumnMappings(
                observationAbout="Country", date="Year", value="Val"
            ),
        )
    )

    bucket2 = Mock()
    blob_a2 = Mock()
    blob_a2.name = "folder/a.csv"
    bucket2.list_blobs.return_value = [blob_a2]
    bucket2.name = "my-bucket"

    missing = get_missing_csv_files(bucket2, cfg, gcs_folder_name="folder")
    assert missing == ["extra.csv"]
