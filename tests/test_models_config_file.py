import pytest

from dcp_tools.custom_data.models.config_file import Config


def test_config_validators_raise_on_invalid_input_files(tmp_path):
    """
    Validates that non-CSV file keys and unknown provenances cause errors.
    """
    # Non-CSV file extension
    config1 = tmp_path / "config1.json"
    config1.write_text(
        '{"inputFiles": {"data.txt": {"provenance": "p1"}},'
        ' "sources": {"s1": {"url": "http://example.com",'
        ' "provenances": {"p1": "http://ex.com"}}}}'
    )
    with pytest.raises(ValueError):
        Config.from_json(str(config1))

    # Unknown provenance reference
    config2 = tmp_path / "config2.json"
    config2.write_text(
        '{"inputFiles": {"data.csv": {"provenance": "unknown"}},'
        ' "sources": {"s1": {"url": "http://example.com",'
        ' "provenances": {"p1": "http://ex.com"}}}}'
    )
    with pytest.raises(ValueError):
        Config.from_json(str(config2))
