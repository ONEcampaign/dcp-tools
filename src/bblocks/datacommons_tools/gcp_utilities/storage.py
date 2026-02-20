import io
import json
import os
import tempfile
from pathlib import Path
from typing import Iterable, Sequence, Any
from urllib.parse import urlparse

import pandas as pd

from bblocks.datacommons_tools.custom_data.models.config_file import Config

from google.cloud.storage import Bucket

from bblocks.datacommons_tools.custom_data.models.mcf import MCFNodes
from bblocks.datacommons_tools.logger import logger

_SKIP_IN_SUBDIR = {".json"}
_VALID_EXTENSIONS = {".csv", ".json", ".mcf"}


def _iter_local_files(directory: Path) -> Iterable[Path]:
    """Yield all the files to be uploaded (excluding the skipped ones in subdirectories)

    Args:
        directory (Path): The directory to iterate through.

    """
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        if path.parent != directory and path.suffix in _SKIP_IN_SUBDIR:
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


def upload_directory_to_gcs(
    bucket: Bucket, directory: Path, gcs_folder_name: str | None = None
) -> None:
    """Upload a local directory to Google Cloud Storage. Folder structures
    is maintained in the GCS bucket in a specified base folder

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

    files_uploaded = 0

    for local_path in _iter_local_files(directory):
        if local_path.suffix not in _VALID_EXTENSIONS:
            logger.warning(f"Skipping unsupported file type: {local_path}")
            continue
        relative = local_path.relative_to(directory).as_posix()
        remote_path = f"{gcs_folder_name}/{relative}" if gcs_folder_name else relative
        bucket.blob(remote_path).upload_from_filename(str(local_path))
        logger.info(f"Uploaded {local_path} to {remote_path}")
        files_uploaded += 1

    dest = gcs_folder_name if gcs_folder_name else "root"
    logger.info(
        f"Uploaded {files_uploaded} files to {dest} in GCS bucket {bucket.name}"
    )


def sync_directory_to_gcs(
    bucket: Bucket, directory: Path, gcs_folder_name: str | None = None
) -> None:
    """Upload a local directory then delete stale remote blobs.

    This function first uploads all local files (via
    :func:`upload_directory_to_gcs`) and then removes any blobs under
    ``gcs_folder_name`` that no longer have a local counterpart.

    Args:
        bucket (Bucket): GCS bucket instance.
        directory (Path): Local directory to upload.
        gcs_folder_name (str | None): Name of the base folder in the GCS
            bucket. If ``None``, the bucket root is used.
    """
    upload_directory_to_gcs(bucket, directory, gcs_folder_name)

    # Build the set of expected remote paths from local files
    expected: set[str] = set()
    for local_path in _iter_local_files(directory):
        if local_path.suffix not in _VALID_EXTENSIONS:
            continue
        relative = local_path.relative_to(directory).as_posix()
        remote_path = f"{gcs_folder_name}/{relative}" if gcs_folder_name else relative
        expected.add(remote_path)

    # List current remote blobs
    prefix = gcs_folder_name or None
    try:
        remote = set(list_bucket_files(bucket, prefix))
    except FileNotFoundError:
        remote = set()

    stale = remote - expected
    if stale:
        logger.info(
            f"Found {len(stale)} stale blob(s) under "
            f"'{gcs_folder_name or 'root'}', deleting..."
        )
        delete_bucket_files(bucket, list(stale))
    else:
        logger.info(f"No stale blobs found under '{gcs_folder_name or 'root'}'")


def list_bucket_files(bucket: Bucket, gcs_folder_name: str | None = None) -> list[str]:
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
    bucket: Bucket, config: Config | dict, gcs_folder_name: str | None = None
) -> list[str]:
    """Identify CSV files in the bucket not referenced in ``config``.

    Args:
        bucket (Bucket): GCS bucket instance.
        config (Config): Parsed configuration object.
        gcs_folder_name (str | None): Folder path prefix in the bucket. If
            ``None``, search the entire bucket.

    Returns:
        list[str]: CSV file names present in the bucket but missing from
            ``config.inputFiles``.
    """

    blob_names = list_bucket_files(bucket=bucket, gcs_folder_name=gcs_folder_name)
    csv_files: list[str] = []
    for name in blob_names:
        path = Path(name)
        if path.suffix != ".csv":
            continue
        if gcs_folder_name:
            try:
                prefix = gcs_folder_name.rstrip("/")
                path = path.relative_to(prefix)
            except ValueError:
                pass
        csv_files.append(str(path).replace(os.sep, "/"))

    if isinstance(config, dict):
        config = Config.model_validate(config)

    registered = set(config.inputFiles.keys())
    return [name for name in csv_files if name not in registered]


def get_missing_csv_files(
    bucket: Bucket, config: Config | dict, gcs_folder_name: str | None = None
) -> list[str]:
    """Identify CSV files referenced in ``config`` but absent from ``bucket``.

    Args:
        bucket (Bucket): GCS bucket instance.
        config (Config | dict): Parsed configuration object.
        gcs_folder_name (str | None): Folder path prefix in the bucket. If
            ``None``, search the entire bucket.

    Returns:
        list[str]: CSV file names present in ``config.inputFiles`` but missing
            from the bucket.
    """

    blob_names = set(list_bucket_files(bucket=bucket, gcs_folder_name=gcs_folder_name))

    if isinstance(config, dict):
        config = Config.model_validate(config)

    missing: list[str] = []
    for name in config.inputFiles.keys():
        path = Path(name)
        if path.suffix != ".csv":
            continue
        blob_name = f"{gcs_folder_name}/{name}" if gcs_folder_name else name
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
            tmp = tempfile.NamedTemporaryFile(suffix=".mcf", delete=False)
            try:
                tmp.write(raw)
                tmp.close()
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
