import csv
from typing import Annotated, Any, overload

from pydantic import BeforeValidator, PlainSerializer, PlainValidator, StringConstraints


def _strip_space_after_dcid(v: Any) -> Any:
    if isinstance(v, str) and v.startswith("dcid:"):
        v = "dcid:" + v[5:].lstrip()
    return v


def _ensure_quoted(s: str) -> str:
    """Ensure a given string is enclosed in double quotes.

    Args:
        s: The input string to quote.

    Returns:
        A string enclosed in double quotes, stripped of leading/trailing whitespace.
    """
    if s.startswith("'") or s.startswith('"'):
        s = s.strip('"').strip("'").strip()
    return f'"{s}"'


def mcf_quoted_str(value: str | list[str] | None) -> str | None:
    """Serialise a string or list of strings to an MCF-compatible quoted string.

    Args:
        value: A string, list of strings, or None to serialise.

    Returns:
        An MCF-compatible quoted string or None if input is None.
    """
    if value is None:
        return None

    if isinstance(value, list):
        if len(value) == 0:
            return None
        if len(value) == 1:
            return _ensure_quoted(value[0])

        return ",".join(_ensure_quoted(str(item)) for item in value)

    return _ensure_quoted(value)


def mcf_str(value: str | list[str] | None) -> str | None:
    """Serialise a string or list of strings without adding quotes.

    Args:
        value: A string, list of strings, or None to serialise.

    Returns:
        A comma-delimited string or None if input is None.
    """
    if value is None:
        return None

    if isinstance(value, list):
        if len(value) == 0:
            return None
        if len(value) == 1:
            return str(value[0])

        return ", ".join(str(item) for item in value)

    return value


def parse_str_or_list(value: str | list[str]) -> str | list[str]:
    """Return a list when a comma-delimited string is provided."""
    if isinstance(value, str):
        parsed = next(csv.reader([value], skipinitialspace=True))
        parsed = [v.strip() for v in parsed]
        return parsed[0] if len(parsed) == 1 else parsed
    return value


def _prepare_dcid_or_list(value: Any) -> str | list[str]:
    """Normalize dcid-or-list input ahead of the inner Dcid-family schema.

    Used as a ``BeforeValidator`` (not ``PlainValidator``, which would replace the inner
    schema rather than run before it) so the ``dcid:``/slug pattern check on the wrapped
    ``Dcid``/``GroupDcid`` type still runs afterwards.

    Splits a comma-delimited string into a list (``parse_str_or_list``), repairs
    ``"dcid: <token>"`` spacing per element the same way ``Dcid``'s own
    ``BeforeValidator`` does, and mints bare tokens to ``dcid:<token>`` via
    ``ensure_dcid``. Repairing the spacing before minting means a value like
    ``"dcid: Foo"`` is fixed up rather than rejected by ``ensure_dcid``'s
    no-whitespace rule, matching what a plain ``Dcid`` field already does.

    Raises:
        ValueError: If the value is not a string or a list of strings. Raising
            ``ValueError`` (rather than letting ``ensure_dcid`` fail on a non-iterable)
            keeps the failure a ``pydantic.ValidationError`` for the caller.
    """
    if not isinstance(value, (str, list)):
        raise ValueError(
            f"expected a string or list of strings, got {type(value).__name__}"
        )
    if isinstance(value, list) and not all(isinstance(v, str) for v in value):
        raise ValueError("expected every element to be a string")

    value = parse_str_or_list(value)
    if isinstance(value, list):
        value = [_strip_space_after_dcid(v) for v in value]
    else:
        value = _strip_space_after_dcid(value)
    return ensure_dcid(value)


# A string annotated for serialisation into an MCF-compatible quoted format.
QuotedStr = Annotated[
    str, PlainSerializer(_ensure_quoted, return_type=str | None, when_used="always")
]

# Accepts a string or list and serialises to quoted MCF format.
QuotedStrListOrStr = Annotated[
    str | list[str],
    PlainValidator(parse_str_or_list),
    PlainSerializer(mcf_quoted_str, return_type=str | None, when_used="always"),
]

# Accepts a string or list and serialises to a comma-separated string.
StrOrListStr = Annotated[
    str | list[str],
    PlainValidator(parse_str_or_list),
    PlainSerializer(mcf_str, return_type=str | None, when_used="always"),
]

Dcid = Annotated[
    str,
    BeforeValidator(_strip_space_after_dcid),
    StringConstraints(strip_whitespace=True, pattern=r"^dcid:\S+$"),
]

GroupDcid = Annotated[
    Dcid, StringConstraints(strip_whitespace=True, pattern=r"^dcid:.*g/.*")
]

PeerGroupDcid = Annotated[
    Dcid, StringConstraints(strip_whitespace=True, pattern=r"^dcid:.*svpg/.*")
]

TopicDcid = Annotated[
    Dcid, StringConstraints(strip_whitespace=True, pattern=r"^dcid:.*topic/.*")
]

# Accepts a bare or dcid:-prefixed string/list (bare tokens are minted via
# ensure_dcid) and serialises to a comma-separated string.
DcidOrListDcid = Annotated[
    Dcid | list[Dcid],
    BeforeValidator(_prepare_dcid_or_list),
    PlainSerializer(mcf_str, return_type=Dcid | None, when_used="always"),
]

# Accepts a bare or dcid:-prefixed string/list (bare tokens are minted via
# ensure_dcid) and serialises to a comma-separated string.
GroupDcidOrListGroupDcid = Annotated[
    GroupDcid | list[GroupDcid],
    BeforeValidator(_prepare_dcid_or_list),
    PlainSerializer(mcf_str, return_type=GroupDcid | None, when_used="always"),
]

# A custom dimension key, becomes `custom:<name>` and `dcid:<name>` downstream.
CustomDimensionName = Annotated[str, StringConstraints(pattern=r"^\S+$")]


@overload
def ensure_dcid(value: str) -> str: ...


@overload
def ensure_dcid(value: list[str]) -> list[str]: ...


def ensure_dcid(value: str | list[str]) -> str | list[str]:
    """Normalize a node/typeOf/ref token (or list) to a bare dcid.

    Schema nodes (Class, Property, units, measurement methods) and their refs use bare
    dcids (``dcid:MyClass``), not slug-namespaced ones (``dcid:source/<name>``). Use this
    for ``Node``/``typeOf``/``subClassOf`` and the Property ref fields
    (``domainIncludes``/``rangeIncludes``/``subPropertyOf``); use ``mint_dcid`` for
    slug-namespaced refs (sources, provenances).

    A list is mapped element-wise (so ``DcidOrListDcid`` fields accept bare lists).

    Rules (per element):
        Already ``dcid:``-prefixed -> returned verbatim.
        Bare token                 -> prefixed with ``dcid:`` (e.g. ``'MyClass'`` ->
                                       ``'dcid:MyClass'``).
        Empty or whitespace-bearing -> ``ValueError`` (mirrors ``mint_dcid``).

    Args:
        value: A bare token, an already ``dcid:``-prefixed string, or a list of either.

    Returns:
        A ``dcid:``-prefixed string, or a list of them when given a list.

    Raises:
        ValueError: If any element is empty or contains a whitespace character.
    """
    if isinstance(value, list):
        return [ensure_dcid(v) for v in value]
    if not value or any(c.isspace() for c in value):
        raise ValueError(
            f"ensure_dcid: value must be a non-empty token with no whitespace; got {value!r}"
        )
    if value.startswith("dcid:"):
        return value
    return f"dcid:{value}"


def mint_dcid(*, prefix: str, token: str) -> str:
    """Mint a dcid for a source/provenance node id or reference.

    Three-way minting rule (canonical):
        Bare token                     -> ``dcid:<prefix>/<token>``
                                         e.g. ``'CustomSource'`` -> ``'dcid:source/CustomSource'``
        Already ``dcid:``-prefixed    -> returned verbatim (power-user escape hatch)
                                         e.g. ``'dcid:bio/y'`` -> ``'dcid:bio/y'``
        Contains ``/`` (no ``dcid:``) -> prepended with ``dcid:``
                                         e.g. ``'source/Foo'`` -> ``'dcid:source/Foo'``
        Whitespace or empty token      -> ``ValueError`` (strict contract; no slugify)

    Args:
        prefix: Namespace prefix used when minting a bare name (e.g. ``'source'``,
            ``'provenance'``).
        token: The bare token, partially-qualified path, or already-minted dcid.

    Returns:
        A fully-qualified dcid string.

    Raises:
        ValueError: If *token* is empty or contains any whitespace character.
    """
    if not token or any(c.isspace() for c in token):
        raise ValueError(
            f"mint_dcid: token must be non-empty with no whitespace; got {token!r}"
        )
    if token.startswith("dcid:"):
        return token
    if "/" in token:
        return f"dcid:{token}"
    return f"dcid:{prefix}/{token}"
