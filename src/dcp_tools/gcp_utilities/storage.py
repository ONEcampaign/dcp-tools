import io
import json
import os
import tempfile
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd
from google.cloud.storage import Bucket

from dcp_tools.custom_data.models.config_file import Config
from dcp_tools.custom_data.models.mcf import MCFNodes
from dcp_tools.logger import logger

_VALID_EXTENSIONS = {".csv", ".json", ".mcf"}


def _iter_local_files(directory: Path) -> Iterable[Path]:
    """Yield all the files to be uploaded under ``directory``.

    Args:
        directory (Path): The directory to iterate through.

    """
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        yield path


def _normalize_gcs_prefix(bucket: Bucket, prefix: str | None) -> str | None:
    """Normalize ``prefix`` for use with :func:`Bucket.list_blobs`.

    Args:
        bucket (Bucket): GCS bucket instance.
        prefix (str | None): The folder path. May include a ``gs://`` prefix.

    Returns:
        str | None: Sanitized prefix with trailing slash or ``None``.

    Raises:
        ValueError: If the bucket specified in ``prefix`` does not match
            ``bucket``.
    """

    if prefix is None:
        return None

    if prefix.startswith("gs://"):
        parsed = urlparse(prefix)
        if parsed.netloc and parsed.netloc != bucket.name:
            raise ValueError(
                f"Bucket '{parsed.netloc}' does not match target bucket '{bucket.name}'"
            )
        prefix = parsed.path.lstrip("/")

    prefix = prefix.strip("/")
    if not prefix:
        return None

    return f"{prefix}/"


def _remote_path(local_path: Path, directory: Path, gcs_folder_name: str | None) -> str:
    """Map a local file path to its remote blob name under ``gcs_folder_name``.

    The relative directory structure under ``directory`` is preserved.
    """
    relative = local_path.relative_to(directory).as_posix()
    return f"{gcs_folder_name}/{relative}" if gcs_folder_name else relative


def _scoped_prefix(gcs_folder_name: str | None, import_name: str | None) -> str | None:
    """Append ``import_name`` to ``gcs_folder_name`` when scoping to one import.

    Args:
        gcs_folder_name (str | None): Base folder path in the GCS bucket.
        import_name (str | None): Single-segment import name (e.g. ``"myImport"``).
            Must not contain ``/``.

    Returns:
        str | None: Effective prefix scoped to the import, or the base prefix
            when ``import_name`` is ``None``.

    Raises:
        ValueError: If ``import_name`` contains a ``/`` (must be a single path segment).
    """
    base = gcs_folder_name.strip("/") if gcs_folder_name else None
    if import_name:
        seg = import_name.strip("/")
        if "/" in seg:
            raise ValueError(
                f"import_name must be a single path segment, got {import_name!r}"
            )
        return f"{base}/{seg}" if base else seg
    return base


def upload_directory_to_gcs(
    bucket: Bucket, directory: Path, *, gcs_folder_name: str | None = None
) -> None:
    """Upload a local directory to Google Cloud Storage. Folder structure
    is maintained in the GCS bucket in a specified base folder.

    Every file matching the supported extensions anywhere under ``directory``
    is uploaded. Import subdirs must therefore contain only files meant for
    upload (no scratch or intermediate ``.json``); callers are responsible for
    keeping the source tree clean.

    Args:
        bucket (Bucket): GCS bucket instance.
        directory (Path): Local directory to upload.
        gcs_folder_name (str | None): Name of the base folder in the GCS bucket
            to store the data. If ``None``, files are uploaded to the bucket
            root while maintaining the directory structure.

    Raises:
        FileNotFoundError: If the specified directory does not exist.
    """
    if not directory.exists():
        raise FileNotFoundError(f"The directory {directory} does not exist.")

    if gcs_folder_name is not None:
        gcs_folder_name = gcs_folder_name.strip("/") or None

    files_uploaded = 0

    for local_path in _iter_local_files(directory):
        if local_path.suffix not in _VALID_EXTENSIONS:
            logger.warning(f"Skipping unsupported file type: {local_path}")
            continue
        remote_path = _remote_path(local_path, directory, gcs_folder_name)
        bucket.blob(remote_path).upload_from_filename(str(local_path))
        logger.info(f"Uploaded {local_path} to {remote_path}")
        files_uploaded += 1

    dest = gcs_folder_name if gcs_folder_name else "root"
    logger.info(
        f"Uploaded {files_uploaded} files to {dest} in GCS bucket {bucket.name}"
    )


def sync_directory_to_gcs(
    bucket: Bucket, directory: Path, *, gcs_folder_name: str | None = None
) -> None:
    """Upload a local directory then delete stale remote blobs.

    This function first uploads all local files (via
    :func:`upload_directory_to_gcs`) and then removes any blobs that are
    stale (no longer have a local counterpart) within the scopes of the
    import subdirectories that contain files locally.

    Deletion is subset-safe by directory-tree discovery. Blobs under import
    subdirectories with no files locally are never deleted. This includes both
    imports not brought locally at all and import subdirs that are present but
    empty. Pass the parent directory containing all ``<importName>/`` subdirs;
    the function discovers which imports have files and scopes deletion to
    them, so no ``import_name`` argument is required.

    Args:
        bucket (Bucket): GCS bucket instance.
        directory (Path): Local directory to upload (typically the parent of
            all ``<importName>/`` subdirectories).
        gcs_folder_name (str | None): Name of the base folder in the GCS
            bucket. If ``None``, the bucket root is used.
    """
    if gcs_folder_name is not None:
        gcs_folder_name = gcs_folder_name.strip("/") or None

    upload_directory_to_gcs(bucket, directory, gcs_folder_name=gcs_folder_name)

    # Remote prefix with trailing slash (empty string when no prefix)
    base = f"{gcs_folder_name}/" if gcs_folder_name else ""

    # Build the expected set and discover which import subdirs are present
    expected: set[str] = set()
    subtree_scopes: set[str] = set()  # full subtrees safe to prune (import subdirs)
    has_root_level_file = False  # whether any file sits directly under directory

    for local_path in _iter_local_files(directory):
        if local_path.suffix not in _VALID_EXTENSIONS:
            continue
        remote_path = _remote_path(local_path, directory, gcs_folder_name)
        expected.add(remote_path)
        rel = local_path.relative_to(directory)
        if len(rel.parts) > 1:
            # Nested under an import subdir — whole subtree is in scope for pruning
            subtree_scopes.add(f"{base}{rel.parts[0]}/")
        else:
            has_root_level_file = True

    try:
        remote = set(list_bucket_files(bucket, gcs_folder_name=gcs_folder_name))
    except FileNotFoundError:
        remote = set()

    def _deletable(r: str) -> bool:
        # Subtree rule: any depth under a present import subdir
        if any(r.startswith(s) for s in subtree_scopes):
            return True
        # Root rule: ONLY direct children of `base` (no further "/"), and only
        # when this run actually had root-level local files. Deletes legacy
        # prefix/old.csv but never prefix/otherImport/b.csv (deeper "/").
        return has_root_level_file and r.startswith(base) and "/" not in r[len(base) :]

    stale = {r for r in (remote - expected) if _deletable(r)}
    if stale:
        logger.info(
            f"Found {len(stale)} stale blob(s) under "
            f"'{gcs_folder_name or 'root'}', deleting..."
        )
        delete_bucket_files(bucket, list(stale))
    else:
        logger.info(f"No stale blobs found under '{gcs_folder_name or 'root'}'")


def list_bucket_files(
    bucket: Bucket, *, gcs_folder_name: str | None = None
) -> list[str]:
    """Return the list of blob names in ``gcs_folder_name``.

    Args:
        bucket (Bucket): GCS bucket instance.
        gcs_folder_name (str | None): Folder path prefix in the bucket. If
            ``None``, all files in the bucket are returned.

    Returns:
        list[str]: Blob names found under the given prefix.
    """

    prefix = _normalize_gcs_prefix(bucket, gcs_folder_name)
    blobs_iter = bucket.list_blobs(prefix=prefix) if prefix else bucket.list_blobs()
    blob_names = [blob.name for blob in blobs_iter]
    if gcs_folder_name and not blob_names:
        raise FileNotFoundError(
            f"The folder '{gcs_folder_name}' does not exist in bucket '{bucket.name}'"
        )
    return blob_names


def get_unregistered_csv_files(
    bucket: Bucket,
    config: Config | dict,
    *,
    gcs_folder_name: str | None = None,
    import_name: str | None = None,
) -> list[str]:
    """Identify CSV files in the bucket not referenced in ``config``.

    When ``import_name`` is provided, the check is scoped to that import's
    subdirectory (e.g. ``import_name="myImport"`` checks under
    ``gcs_folder_name/myImport/``). Blobs from sibling imports are not
    returned. When omitted, behaves as today — compares against ``gcs_folder_name``
    directly.

    Args:
        bucket (Bucket): GCS bucket instance.
        config (Config): Parsed configuration object.
        gcs_folder_name (str | None): Folder path prefix in the bucket. If
            ``None``, search the entire bucket.
        import_name (str | None): Single-segment import name used to scope
            the listing to ``gcs_folder_name/<import_name>/``. Must not
            contain ``/``.

    Returns:
        list[str]: CSV file names present in the bucket but missing from
            ``config.inputFiles``.
    """
    effective = _scoped_prefix(gcs_folder_name, import_name)
    try:
        blob_names = list_bucket_files(bucket=bucket, gcs_folder_name=effective)
    except FileNotFoundError:
        blob_names = []

    csv_files: list[str] = []
    for name in blob_names:
        path = Path(name)
        if path.suffix != ".csv":
            continue
        if effective:
            try:
                prefix = effective.rstrip("/")
                path = path.relative_to(prefix)
            except ValueError:
                pass
        csv_files.append(str(path).replace(os.sep, "/"))

    if isinstance(config, dict):
        config = Config.model_validate(config)

    registered = set(config.inputFiles.keys())
    return [name for name in csv_files if name not in registered]


def get_missing_csv_files(
    bucket: Bucket,
    config: Config | dict,
    *,
    gcs_folder_name: str | None = None,
    import_name: str | None = None,
) -> list[str]:
    """Identify CSV files referenced in ``config`` but absent from ``bucket``.

    When ``import_name`` is provided, the check is scoped to that import's
    subdirectory (e.g. ``import_name="myImport"`` checks under
    ``gcs_folder_name/myImport/``). When omitted, behaves as today — compares
    against ``gcs_folder_name`` directly.

    Args:
        bucket (Bucket): GCS bucket instance.
        config (Config | dict): Parsed configuration object.
        gcs_folder_name (str | None): Folder path prefix in the bucket. If
            ``None``, search the entire bucket.
        import_name (str | None): Single-segment import name used to scope
            the check to ``gcs_folder_name/<import_name>/``. Must not
            contain ``/``.

    Returns:
        list[str]: CSV file names present in ``config.inputFiles`` but missing
            from the bucket.
    """
    effective = _scoped_prefix(gcs_folder_name, import_name)
    try:
        blob_names = set(list_bucket_files(bucket=bucket, gcs_folder_name=effective))
    except FileNotFoundError:
        blob_names = set()

    if isinstance(config, dict):
        config = Config.model_validate(config)

    missing: list[str] = []
    for name in config.inputFiles:
        path = Path(name)
        if path.suffix != ".csv":
            continue
        blob_name = f"{effective}/{name}" if effective else name
        if blob_name not in blob_names:
            missing.append(name)

    return missing


def delete_bucket_files(bucket: Bucket, blob_names: list[str] | str) -> None:
    """Delete the specified blobs from ``bucket``.

    Args:
        bucket (Bucket): GCS bucket instance.
        blob_names (Iterable[str]): Names of the blobs to delete.
    """
    if isinstance(blob_names, str):
        blob_names = [blob_names]

    for name in blob_names:
        bucket.blob(name).delete()
        logger.info(f"Deleted {name} from bucket {bucket.name}")


def get_bucket_files(
    bucket: Bucket, blob_names: Sequence[str] | str
) -> Any | dict[str, Any]:
    """Download files from ``bucket`` and return their content.

    Args:
        bucket (Bucket): GCS bucket instance.
        blob_names (Sequence[str] | str): Name or names of the blobs to download.

    Returns:
        Any: Parsed object(s) from the downloaded blob(s).
    """

    single = False
    if isinstance(blob_names, str):
        blob_names = [blob_names]
        single = True

    results: dict[str, Any] = {}
    for name in blob_names:
        raw = bucket.blob(name).download_as_bytes()
        ext = Path(name).suffix.lower()
        if ext == ".csv":
            results[name] = pd.read_csv(io.BytesIO(raw))
        elif ext == ".json":
            results[name] = json.loads(raw.decode("utf-8"))
        elif ext == ".mcf":
            with tempfile.NamedTemporaryFile(suffix=".mcf", delete=False) as tmp:
                tmp.write(raw)
            try:
                results[name] = MCFNodes().load_from_mcf_file(tmp.name)
            finally:
                os.unlink(tmp.name)
        else:
            results[name] = raw
        logger.info(f"Downloaded {name} from bucket {bucket.name}")

    if single:
        # Return the only item directly
        return next(iter(results.values()))

    return results
