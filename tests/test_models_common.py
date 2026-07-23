import pytest
from pydantic import BaseModel, ValidationError

from dcp_tools.custom_data.models.common import (
    DcidOrListDcid,
    GroupDcidOrListGroupDcid,
    StrOrListStr,
    _ensure_quoted,
    ensure_dcid,
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


def test_ensure_dcid_prefixes_bare_token():
    assert ensure_dcid("MyClass") == "dcid:MyClass"


def test_ensure_dcid_passes_prefixed_verbatim():
    assert ensure_dcid("dcid:bio/Foo") == "dcid:bio/Foo"


def test_ensure_dcid_rejects_empty_or_whitespace():
    with pytest.raises(ValueError):
        ensure_dcid("")
    with pytest.raises(ValueError):
        ensure_dcid("has space")
    with pytest.raises(ValueError):
        ensure_dcid("  leading")
    with pytest.raises(ValueError):
        ensure_dcid("trailing\t")


def test_ensure_dcid_maps_over_list():
    assert ensure_dcid(["Person", "dcid:Number"]) == ["dcid:Person", "dcid:Number"]


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


# --- DcidOrListDcid and friends (regression test for #126) ---
#
# PlainValidator used to replace the inner Dcid/GroupDcid/PeerGroupDcid/TopicDcid schema
# outright, so its dcid:/slug pattern never ran and any string passed through unvalidated.
# These exercise the BeforeValidator fix directly against the type aliases (not just a
# specific model field), matching the Dummy(BaseModel) pattern used for StrOrListStr above.


def test_dcid_or_list_dcid_mints_bare_scalar_and_list():
    class Dummy(BaseModel):
        field: DcidOrListDcid

    assert Dummy(field="MyClass").field == "dcid:MyClass"
    assert Dummy(field=["One", "Two"]).field == ["dcid:One", "dcid:Two"]
    # comma-delimited string is split first, then each element minted
    assert Dummy(field="One, Two").field == ["dcid:One", "dcid:Two"]
    # already dcid:-prefixed values pass through verbatim
    assert Dummy(field="dcid:bio/Foo").field == "dcid:bio/Foo"


def test_dcid_or_list_dcid_rejects_whitespace_bearing_token():
    class Dummy(BaseModel):
        field: DcidOrListDcid

    with pytest.raises(ValidationError):
        Dummy(field="has space")
    with pytest.raises(ValidationError):
        Dummy(field=["ok", "has space"])


def test_dcid_or_list_dcid_repairs_space_after_dcid_prefix():
    """ "dcid: Foo" is repaired to "dcid:Foo", the same as a plain Dcid field, rather
    than rejected by ensure_dcid's own no-whitespace rule. Preserves the one case where
    the old, unvalidated PlainValidator didn't raise on this input either (see #126)."""

    class Dummy(BaseModel):
        field: DcidOrListDcid

    assert Dummy(field="dcid: Foo").field == "dcid:Foo"


def test_dcid_or_list_dcid_rejects_non_string_input():
    """A non-string value raises ValidationError, not a raw TypeError out of ensure_dcid.

    Before #126 a value like 123 was silently accepted, because PlainValidator never
    reached ensure_dcid. The guard keeps the failure a pydantic error for the caller.
    """

    class Dummy(BaseModel):
        field: DcidOrListDcid

    with pytest.raises(ValidationError):
        Dummy(field=123)
    with pytest.raises(ValidationError):
        Dummy(field=["dcid:ok", 5])
    with pytest.raises(ValidationError):
        Dummy(field={"a": "b"})


# --- GroupDcidOrListGroupDcid (regression test for #131) ---
#
# GroupDcidOrListGroupDcid, PeerGroupDcidOrListPeerGroupDcid and TopicDcidOrListTopicDcid
# used to still use PlainValidator (their slug pattern bypassed), tracked separately from
# #126. #131 switched all three to the same BeforeValidator as DcidOrListDcid, once
# StatVarNode.memberOf no longer used the field as a scratch value for an unresolved
# raw group path (see resolve_group_paths in schema_tools.py). PeerGroupDcidOrListPeerGroupDcid
# and TopicDcidOrListTopicDcid were then deleted, along with the TopicDcid they wrapped: no
# field references them (TopicNode.relevantVariable collapsed to plain DcidOrListDcid — see
# test_models_topics.py).


def test_group_dcid_or_list_group_dcid_mints_and_enforces_slug_pattern():
    """Same BeforeValidator as DcidOrListDcid, plus the GroupDcid slug pattern
    (the resolved dcid must contain 'g/')."""

    class Dummy(BaseModel):
        field: GroupDcidOrListGroupDcid

    assert Dummy(field="g/MyGroup").field == "dcid:g/MyGroup"
    assert Dummy(field=["g/One", "g/Two"]).field == ["dcid:g/One", "dcid:g/Two"]
    # already dcid:-prefixed values pass through verbatim
    assert Dummy(field="dcid:ns/g/Foo").field == "dcid:ns/g/Foo"


def test_group_dcid_or_list_group_dcid_rejects_non_group_token():
    """A minted dcid with no 'g/' segment fails the GroupDcid pattern."""

    class Dummy(BaseModel):
        field: GroupDcidOrListGroupDcid

    with pytest.raises(ValidationError):
        Dummy(field="NotAGroup")
