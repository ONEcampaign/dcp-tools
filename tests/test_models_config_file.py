import pytest

from dcp_tools.custom_data.models.config_file import Config
from dcp_tools.custom_data.models.data_files import ColumnMappings, ExplicitSchemaFile


def test_config_validators_raise_on_invalid_input_files():
    """
    Validates that a non-CSV filename causes an error on ExplicitSchemaFile construction.
    """
    with pytest.raises(ValueError):
        ExplicitSchemaFile(
            filename="data.txt",
            provenance="p1",
            columnMappings=ColumnMappings(),
        )


def test_explicit_schema_file_filename_pattern_xor():
    """Exactly one of filename/pattern must be set; providing both or neither raises."""
    # Neither provided
    with pytest.raises(ValueError):
        ExplicitSchemaFile(
            provenance="p1",
            columnMappings=ColumnMappings(),
        )

    # Both provided
    with pytest.raises(ValueError):
        ExplicitSchemaFile(
            filename="a.csv",
            pattern="a*",
            provenance="p1",
            columnMappings=ColumnMappings(),
        )

    # filename only — valid
    ef = ExplicitSchemaFile(
        filename="a.csv",
        provenance="p1",
        columnMappings=ColumnMappings(),
    )
    assert ef.filename == "a.csv"
    assert ef.pattern is None

    # pattern only — valid (no .csv check on pattern)
    ep = ExplicitSchemaFile(
        pattern="data_*",
        provenance="p1",
        columnMappings=ColumnMappings(),
    )
    assert ep.pattern == "data_*"
    assert ep.filename is None


def test_explicit_schema_file_provenance_minted():
    """ExplicitSchemaFile mints the provenance to dcid:provenance/<name>."""
    ef = ExplicitSchemaFile(
        filename="a.csv",
        provenance="myProv",
        columnMappings=ColumnMappings(),
    )
    assert ef.provenance == "dcid:provenance/myProv"

    # Already-minted provenance is returned verbatim
    ef2 = ExplicitSchemaFile(
        filename="b.csv",
        provenance="dcid:provenance/myProv",
        columnMappings=ColumnMappings(),
    )
    assert ef2.provenance == "dcid:provenance/myProv"


def test_config_round_trips_import_name(tmp_path):
    """A platform config.json with a top-level importName loads and round-trips."""
    config = tmp_path / "config.json"
    config.write_text(
        '{"importName": "OECD_wage_data",'
        ' "inputFiles": [{"filename": "data.csv", "provenance": "p1", "columnMappings": {},'
        ' "format": "variablePerRow"}]}'
    )
    loaded = Config.from_json(str(config))
    assert loaded.importName == "OECD_wage_data"
    assert loaded.model_dump(exclude_none=True)["importName"] == "OECD_wage_data"
