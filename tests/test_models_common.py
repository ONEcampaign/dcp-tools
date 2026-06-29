import pytest
from pydantic import BaseModel

from dcp_tools.custom_data.models.common import (
    StrOrListStr,
    _ensure_quoted,
    mcf_quoted_str,
    mcf_str,
    mint_dcid,
    parse_str_or_list,
)


def test_ensure_quoted_handles_quotes_and_whitespace():
    """
    Ensures that strings already quoted or with whitespace
    are normalized to double-quoted form without extra spaces.
    """
    assert _ensure_quoted("value") == '"value"'
    assert _ensure_quoted("'value'") == '"value"'


def test_mcf_quoted_str_with_single_and_multiple_items():
    """
    Serializes strings and lists into MCF-compatible quoted strings.
    """
    # Single string
    assert mcf_quoted_str("abc") == '"abc"'
    # Single-element list
    assert mcf_quoted_str(["x"]) == '"x"'
    # Multi-element list
    multi = mcf_quoted_str(["a", "b", "c"])
    assert multi == '"a","b","c"'
    # None input
    assert mcf_quoted_str(None) is None


def test_mcf_quoted_str_empty_list_returns_none():
    """Empty list must return None, not raise IndexError (regression for #84)."""
    assert mcf_quoted_str([]) is None


def test_mcf_str_with_single_and_multiple_items():
    assert mcf_str("abc") == "abc"
    assert mcf_str(["x"]) == "x"
    multi = mcf_str(["a", "b", "c"])
    assert multi == "a, b, c"
    assert mcf_str(None) is None


def test_mcf_str_empty_list_returns_none():
    """Empty list must return None, not raise IndexError (regression for #84)."""
    assert mcf_str([]) is None


def test_str_or_list_str_annotation_serialization():
    class Dummy(BaseModel):
        field: StrOrListStr

    d1 = Dummy(field="A, B")
    assert d1.field == ["A", "B"]
    assert d1.model_dump()["field"] == "A, B"

    d2 = Dummy(field=["x", "y"])
    assert d2.model_dump()["field"] == "x, y"


def test_parse_str_or_list_honours_quotes():
    assert parse_str_or_list('"A, B"') == "A, B"
    assert parse_str_or_list('"A, B", C') == ["A, B", "C"]


def test_mint_dcid_three_way_rule():
    """Covers each branch of the canonical minting rule."""
    # Bare name -> dcid:<prefix>/<name> (the real source/provenance callers)
    assert mint_dcid(prefix="source", name="CustomSource") == "dcid:source/CustomSource"
    assert (
        mint_dcid(prefix="provenance", name="CustomProv")
        == "dcid:provenance/CustomProv"
    )
    # Already dcid:-prefixed -> returned verbatim (escape hatch)
    assert mint_dcid(prefix="source", name="dcid:bio/y") == "dcid:bio/y"
    # Contains "/" but no dcid: -> prepended with dcid:
    assert mint_dcid(prefix="source", name="source/Foo") == "dcid:source/Foo"


def test_mint_dcid_rejects_empty_or_whitespace_names():
    """Empty or whitespace-bearing names violate the strict contract."""
    with pytest.raises(ValueError):
        mint_dcid(prefix="source", name="")
    with pytest.raises(ValueError):
        mint_dcid(prefix="source", name="has space")
    with pytest.raises(ValueError):
        mint_dcid(prefix="source", name="  leading")
    with pytest.raises(ValueError):
        mint_dcid(prefix="source", name="trailing\t")
