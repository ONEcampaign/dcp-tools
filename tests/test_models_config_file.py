import json
from pathlib import Path

import pytest

from dcp_tools.custom_data.models.config_file import Config
from dcp_tools.custom_data.models.data_files import (
    ColumnMappings,
    InputFile,
    ObservationProperties,
)

GOLDEN_DIR = Path(__file__).parent / "goldens"


def test_config_validators_raise_on_invalid_input_files():
    """
    Validates that a non-CSV filename causes an error on InputFile construction.
    """
    with pytest.raises(ValueError):
        InputFile(
            filename="data.txt",
            provenance="p1",
            column_mappings=ColumnMappings(),
        )


def test_input_file_filename_pattern_xor():
    """Exactly one of filename/pattern must be set; providing both or neither raises."""
    # Neither provided
    with pytest.raises(ValueError):
        InputFile(
            provenance="p1",
            column_mappings=ColumnMappings(),
        )

    # Both provided
    with pytest.raises(ValueError):
        InputFile(
            filename="a.csv",
            pattern="a*",
            provenance="p1",
            column_mappings=ColumnMappings(),
        )

    # filename only — valid
    by_filename = InputFile(
        filename="a.csv",
        provenance="p1",
        column_mappings=ColumnMappings(),
    )
    assert by_filename.filename == "a.csv"
    assert by_filename.pattern is None

    # pattern only — valid (no .csv check on pattern)
    by_pattern = InputFile(
        pattern="data_*",
        provenance="p1",
        column_mappings=ColumnMappings(),
    )
    assert by_pattern.pattern == "data_*"
    assert by_pattern.filename is None


def test_input_file_rejects_mcf_filename():
    """`filename` entries are treated as data-bearing CSV targets, so a `.mcf` filename
    would silently be handled as a CSV.
    """
    with pytest.raises(ValueError, match="csv extension"):
        InputFile(filename="nodes.mcf", provenance="p1")


def test_input_file_provenance_minted():
    """InputFile mints the provenance to dcid:provenance/<name>."""
    entry = InputFile(
        filename="a.csv",
        provenance="myProv",
        column_mappings=ColumnMappings(),
    )
    assert entry.provenance == "dcid:provenance/myProv"

    # Already-minted provenance is returned verbatim
    already_minted = InputFile(
        filename="b.csv",
        provenance="dcid:provenance/myProv",
        column_mappings=ColumnMappings(),
    )
    assert already_minted.provenance == "dcid:provenance/myProv"


def test_mcf_input_file_carries_only_provenance():
    """An .mcf entry needs no columnMappings and emits no format."""
    entry = InputFile(pattern="*.mcf", provenance="myProv")

    assert entry.is_mcf
    assert entry.model_dump(exclude_none=True, by_alias=True) == {
        "pattern": "*.mcf",
        "provenance": "dcid:provenance/myProv",
    }


@pytest.mark.parametrize(
    "golden_file",
    [
        "single_entity_import/config.json",
        "multi_entity_import/config.json",
        "multi_provenance_import/config.json",
    ],
)
def test_config_round_trips_from_json(tmp_path, golden_file):
    data = json.loads((GOLDEN_DIR / golden_file).read_text())
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(data))

    loaded = Config.from_json(str(config_file))

    got = loaded.model_dump_json(indent=4, exclude_none=True, by_alias=True)
    assert json.loads(got) == data


def test_observation_properties_preserves_custom_keys():
    """ObservationProperties with a custom key round-trips with the key intact."""
    op = ObservationProperties.model_validate({"unit": "USD", "customKey": "v"})
    dumped = op.model_dump(exclude_none=True, by_alias=True)
    assert dumped == {"unit": "USD", "customKey": "v"}

    # JSON load→dump also preserves the custom key
    raw = json.dumps({"unit": "USD", "customKey": "v"})
    reloaded = ObservationProperties.model_validate_json(raw)
    assert reloaded.model_dump(exclude_none=True, by_alias=True) == {
        "unit": "USD",
        "customKey": "v",
    }


def test_observation_properties_exclude_none_drops_unset_standard_fields():
    """Unset standard fields are absent from the serialised output."""
    op = ObservationProperties(unit="USDollar")
    dumped = op.model_dump(exclude_none=True, by_alias=True)
    assert dumped == {"unit": "USDollar"}
    assert "scalingFactor" not in dumped
    assert "measurementMethod" not in dumped
    assert "observationPeriod" not in dumped


def test_config_accepts_data_download_url_and_vertical_specs_file(tmp_path):
    """Config.from_json accepts both new top-level fields (no extra='forbid' rejection)."""
    config_data = {
        "importName": "test_import",
        "dataDownloadUrl": ["https://example.org/data.csv"],
        "verticalSpecsFile": "vert.json",
        "inputFiles": [
            {
                "filename": "data.csv",
                "provenance": "p1",
                "columnMappings": {},
                "format": "variablePerRow",
            }
        ],
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_data))

    loaded = Config.from_json(str(config_file))
    assert loaded.data_download_url == ["https://example.org/data.csv"]
    assert loaded.vertical_specs_file == "vert.json"

    # Both fields survive a round-trip through model_dump
    dumped = loaded.model_dump(exclude_none=True, by_alias=True)
    assert dumped["dataDownloadUrl"] == ["https://example.org/data.csv"]
    assert dumped["verticalSpecsFile"] == "vert.json"


def test_input_file_observation_properties_roundtrip():
    """observationProperties coexists with columnMappings; custom keys survive dump+reload."""
    entry = InputFile(
        filename="data.csv",
        provenance="prov1",
        column_mappings=ColumnMappings(observation_about="Country", date="Year"),
        observation_properties=ObservationProperties.model_validate(
            {"unit": "USD", "customProp": "x"}
        ),
    )
    dumped = entry.model_dump(exclude_none=True, by_alias=True)
    assert "observationProperties" in dumped
    assert dumped["observationProperties"]["unit"] == "USD"
    assert dumped["observationProperties"]["customProp"] == "x"
    assert "columnMappings" in dumped

    # Reload from the dumped dict
    reloaded = InputFile.model_validate(dumped)
    assert reloaded.observation_properties is not None
    assert reloaded.observation_properties.unit == "USD"
    assert reloaded.observation_properties.model_extra == {"customProp": "x"}


def test_config_loads_spec_keyed_file_and_exports_dcid_keys(tmp_path):
    """A config.json written with the spec's bare keys exports in the canonical form."""
    config_data = {
        "inputFiles": [
            {
                "filename": "data.csv",
                "provenance": "dcid:provenance/p1",
                "columnMappings": {
                    "variableMeasured": "Var",
                    "observationDate": "Year",
                    "value": "Val",
                    "observationAbout": "Country",
                },
                "observationProperties": {"scaling_factor": "100"},
                "format": "variablePerRow",
            }
        ],
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_data))

    loaded = Config.from_json(str(config_file))

    entry = loaded.model_dump(mode="json", exclude_none=True, by_alias=True)[
        "inputFiles"
    ][0]
    assert entry["columnMappings"] == {
        "dcid:variableMeasured": "Var",
        "dcid:observationDate": "Year",
        "dcid:value": "Val",
        "dcid:observationAbout": "Country",
    }
    assert entry["observationProperties"] == {"scalingFactor": "100"}


@pytest.mark.parametrize(
    "properties",
    [
        {
            "unit": "USDollar",
            "scaling_factor": "100",
            "measurement_method": "dcAggregate/Census",
            "observation_period": "P1Y",
        },
        {
            "unit": "USDollar",
            "scalingFactor": "100",
            "measurementMethod": "dcAggregate/Census",
            "observationPeriod": "P1Y",
        },
    ],
    ids=["snake_case", "camelCase"],
)
def test_observation_properties_serialise_camel_case(properties):
    """Standard fields serialise camelCase whichever spelling the caller passed."""
    dumped = ObservationProperties.model_validate(properties).model_dump(
        exclude_none=True, by_alias=True
    )
    assert dumped == {
        "unit": "USDollar",
        "scalingFactor": "100",
        "measurementMethod": "dcAggregate/Census",
        "observationPeriod": "P1Y",
    }


def test_observation_properties_keeps_custom_keys_verbatim():
    """Custom keys keep their spelling, snake_case included."""
    dumped = ObservationProperties.model_validate(
        {"custom_prop": "a", "customProp": "b"}
    ).model_dump(exclude_none=True, by_alias=True)
    assert dumped == {"custom_prop": "a", "customProp": "b"}


@pytest.mark.parametrize(
    "field_name", ["scaling_factor", "measurement_method", "observation_period"]
)
def test_observation_properties_rejects_both_spellings_of_one_field(field_name):
    alias = ObservationProperties.model_fields[field_name].alias
    assert alias is not None
    with pytest.raises(ValueError, match="not both"):
        ObservationProperties.model_validate({field_name: "a", alias: "b"})
