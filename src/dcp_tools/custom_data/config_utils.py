"""Utilities for merging config files."""

from collections.abc import Iterator
from os import PathLike
from pathlib import Path
from typing import Any, Literal

from dcp_tools.custom_data.models.config_file import Config
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
        "importName",
        "includeInputSubdirs",
        "groupStatVarsByProperty",
        "defaultCustomRootStatVarGroupName",
        "customIdNamespace",
        "customSvgPrefix",
        "verticalSpecsFile",
    ):
        _merge_attribute(existing, new, attr, policy)

    _merge_sequence_attribute(
        existing=existing,
        new=new,
        attribute="svHierarchyPropsBlocklist",
        policy=policy,
    )

    _merge_sequence_attribute(
        existing=existing,
        new=new,
        attribute="dataDownloadUrl",
        policy=policy,
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


def _merge_input_files(existing: Config, new: Config, policy: DuplicatePolicy) -> None:
    """Merge input file entries from *new* into *existing* in-place.

    Entries are keyed by ``filename`` or ``pattern`` (whichever is set).
    Conflict semantics follow *policy*: ``"error"`` raises, ``"override"``
    replaces, ``"ignore"`` and equal entries are skipped.
    """
    existing_by_key: dict[str, int] = {}
    for i, e in enumerate(existing.inputFiles):
        k = e.filename or e.pattern
        if k is not None:
            existing_by_key[k] = i

    for entry in new.inputFiles:
        key = entry.filename or entry.pattern
        if key is None:
            # Should not happen: ExplicitSchemaFile enforces filename XOR pattern.
            continue
        if key not in existing_by_key:
            logger.info(f"Added input file '{key}'")
            existing.inputFiles.append(entry)
            existing_by_key[key] = len(existing.inputFiles) - 1
            continue

        idx = existing_by_key[key]
        tgt = existing.inputFiles[idx]
        if tgt == entry:
            continue

        _handle_conflict(
            field=f"Input file '{key}'",
            target_value=tgt,
            source_value=entry,
            policy=policy,
        )
        if policy == "override":
            existing.inputFiles[idx] = entry


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
    _merge_input_files(existing=existing, new=new, policy=policy)


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
    base = Config(inputFiles=[])
    for path in iter_config_files(Path(directory)):
        logger.info(f"Merging config file {path}")
        config = Config.from_json(str(path))
        merge_configs(existing=base, new=config, policy=policy)
    return base
