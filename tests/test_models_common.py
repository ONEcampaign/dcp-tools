from pydantic import BaseModel

from bblocks.datacommons_tools.custom_data.models.common import (
    _ensure_quoted,
    mcf_quoted_str,
    mcf_str,
    parse_str_or_list,
    StrOrListStr,
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
