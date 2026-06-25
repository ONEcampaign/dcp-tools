"""Utilities for merging config files."""

from collections.abc import Iterator
from os import PathLike
from pathlib import Path
from typing import Any, Literal

from dcp_tools.custom_data.models.config_file import Config
from dcp_tools.custom_data.models.sources import Source
from dcp_tools.logger import logger

DuplicatePolicy = Literal["error", "override", "ignore"]


def iter_config_files(directory: Path, pattern: str = "config.json") -> Iterator[Path]:
    """Yield all ``config.json`` files under ``directory`` recursively.

    Files are yielded in sorted order so that merge results are deterministic
    across platforms.
    """
    for path in sorted(directory.rglob(pattern)):
        if path.is_file():
            yield path


def _merge_simple_attrs(existing: Config, new: Config, policy: DuplicatePolicy) -> None:
    """Merge simple attributes that are booleans, strings, or None."""
    for attr in (
        "includeInputSubdirs",
        "groupStatVarsByProperty",
        "defaultCustomRootStatVarGroupName",
        "customIdNamespace",
        "customSvgPrefix",
    ):
        _merge_attribute(existing, new, attr, policy)

    _merge_sequence_attribute(
        existing=existing,
        new=new,
        attribute="svHierarchyPropsBlocklist",
        policy=policy,
    )


def _merge_source(
    target_sources: dict[str, Source],
    name: str,
    source: Source,
    policy: DuplicatePolicy,
) -> None:
    """Merge a *Source* entry and its nested structures."""
    if name not in target_sources:
        logger.info(f"Added source '{name}'")
        target_sources[name] = source
        return

    target = target_sources[name]
    if target.url != source.url:
        _handle_conflict(
            field=f"URL for source '{name}'",
            target_value=target,
            source_value=source,
            policy=policy,
        )
        if policy == "override":
            target.url = source.url

    _merge_dict(
        target_dict=target.provenances,
        source_dict=source.provenances,
        policy=policy,
        context=f"provenance of source '{name}'",
    )


def _handle_conflict(
    field: str, target_value: Any, source_value: Any, policy: DuplicatePolicy
) -> None:
    """Log or raise depending on *policy* when a conflict is detected."""
    if policy == "override":
        logger.warning(f"Overriding {field}: {target_value} -> {source_value}")
    elif policy == "ignore":
        logger.info(f"Ignoring {field}: {target_value} -> {source_value}")
    else:
        raise ValueError(f"Conflicting {field}: {target_value!r} vs {source_value!r}")


def _merge_dict(
    target_dict: dict[Any, Any],
    source_dict: dict[Any, Any],
    policy: DuplicatePolicy,
    context: str,
) -> None:
    """Merge two mapping-like structures, according to *policy*."""
    for key, src_val in source_dict.items():
        if key not in target_dict:
            target_dict[key] = src_val
            continue

        tgt_val = target_dict[key]
        if tgt_val == src_val:
            continue

        _handle_conflict(
            field=f"{context} '{key}'",
            target_value=tgt_val,
            source_value=src_val,
            policy=policy,
        )
        if policy == "override":
            target_dict[key] = src_val


def _merge_attribute(
    existing: Config, new: Config, attribute: str, policy: DuplicatePolicy
) -> None:
    """Merge a single attribute, handling collisions with *policy*."""
    src_val = getattr(new, attribute)
    if src_val is None:
        return

    tgt_val = getattr(existing, attribute)
    if tgt_val is None or tgt_val == src_val:
        setattr(existing, attribute, src_val if tgt_val is None else tgt_val)
        return

    _handle_conflict(
        field=attribute, target_value=tgt_val, source_value=src_val, policy=policy
    )
    if policy == "override":
        setattr(existing, attribute, src_val)


def _merge_sequence_attribute(
    existing: Config, new: Config, attribute: str, policy: DuplicatePolicy
) -> None:
    """Merge a sequence attribute, normalising duplicates when overriding."""
    src_val = getattr(new, attribute)
    if not src_val:
        return

    tgt_val = getattr(existing, attribute)
    if not tgt_val:
        setattr(existing, attribute, list(dict.fromkeys(src_val)))
        return

    if tgt_val == src_val:
        return

    _handle_conflict(
        field=attribute, target_value=tgt_val, source_value=src_val, policy=policy
    )

    if policy == "override":
        # Preserve the order of the incoming values but drop duplicates
        setattr(existing, attribute, list(dict.fromkeys(src_val)))


def merge_configs(
    existing: Config, new: Config, *, policy: DuplicatePolicy = "error"
) -> None:
    """Merge ``new`` into ``existing`` in-place.

    Args:
        existing: target config.
        new: the config to be merged with *existing*.
        policy: How to resolve collisions.

    Raises:
        ValueError: If policy is `"error" and conflicting
            values are encountered.
    """
    # Merge attributes that are booleans or None
    _merge_simple_attrs(existing=existing, new=new, policy=policy)

    # Merge the input file list
    _merge_dict(
        target_dict=existing.inputFiles,
        source_dict=new.inputFiles,
        policy=policy,
        context="Input file",
    )

    # Merge the sources
    for name, src in new.sources.items():
        _merge_source(
            target_sources=existing.sources, name=name, source=src, policy=policy
        )


def merge_configs_from_directory(
    directory: str | PathLike[str], *, policy: DuplicatePolicy = "error"
) -> Config:
    """Return a ``Config`` merging all configs found under ``directory``.

    Args:
        directory: Directory to search for config files.
        policy: How to resolve collisions.
    Raises:
        ValueError: If policy is `"error"` and conflicting
            values are encountered.

    """
    base = Config(inputFiles={}, sources={})
    for path in iter_config_files(Path(directory)):
        logger.info(f"Merging config file {path}")
        config = Config.from_json(str(path))
        merge_configs(existing=base, new=config, policy=policy)
    return base
