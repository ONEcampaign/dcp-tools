from unittest.mock import Mock

import pytest

import pandas as pd

from bblocks.datacommons_tools.gcp_utilities.storage import (
    list_bucket_files,
    upload_directory_to_gcs,
    sync_directory_to_gcs,
    get_unregistered_csv_files,
    get_missing_csv_files,
    delete_bucket_files,
    get_bucket_files,
)
from bblocks.datacommons_tools.custom_data.models.config_file import Config
from bblocks.datacommons_tools.custom_data.models.data_files import (
    ColumnMappings,
    ExplicitSchemaFile,
)
from bblocks.datacommons_tools.custom_data.models.sources import Source


def _minimal_config(key: str = "a.csv") -> Config:
    input_files = {
        key: ExplicitSchemaFile(
            provenance="prov",
            columnMappings=ColumnMappings(),
        )
    }
    sources = {"src": Source(url="http://s", provenances={"prov": "http://p"})}
    return Config(inputFiles=input_files, sources=sources)


def test_upload_directory_to_gcs(tmp_path):
    (tmp_path / "a.csv").write_text("col\n1\n")
    (tmp_path / "b.json").write_text("{}")
    (tmp_path / "skip.txt").write_text("nope")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.mcf").write_text("Node: dcid:x\n")
    # json in subdir should be skipped
    (sub / "d.json").write_text("{}")

    bucket = Mock()
    blobs: dict[str, Mock] = {}

    def blob_side(name: str):
        b = Mock()
        blobs[name] = b
        return b

    bucket.blob.side_effect = blob_side
    bucket.name = "my-bucket"

    upload_directory_to_gcs(bucket, tmp_path, "prefix")

    expected_keys = {"prefix/a.csv", "prefix/b.json", "prefix/sub/c.mcf"}
    assert set(blobs.keys()) == expected_keys
    for b in blobs.values():
        b.upload_from_filename.assert_called_once()


def test_upload_directory_to_gcs_no_prefix(tmp_path):
    (tmp_path / "a.csv").write_text("col\n1\n")

    bucket = Mock()
    blobs: dict[str, Mock] = {}

    def blob_side(name: str):
        b = Mock()
        blobs[name] = b
        return b

    bucket.blob.side_effect = blob_side
    bucket.name = "my-bucket"

    upload_directory_to_gcs(bucket, tmp_path)

    assert set(blobs.keys()) == {"a.csv"}


def test_sync_directory_to_gcs_with_stale_blobs(tmp_path):
    (tmp_path / "a.csv").write_text("col\n1\n")
    (tmp_path / "b.json").write_text("{}")

    bucket = Mock()
    upload_blobs: dict[str, Mock] = {}
    delete_blobs: dict[str, Mock] = {}

    def blob_side(name: str):
        b = Mock()
        # Track whether this is an upload or delete call based on context
        if name not in upload_blobs:
            upload_blobs[name] = b
        else:
            delete_blobs[name] = b
        return b

    bucket.blob.side_effect = blob_side
    bucket.name = "my-bucket"

    # Remote has a stale blob "prefix/old.csv" plus the two that still exist
    blob_a = Mock()
    blob_a.name = "prefix/a.csv"
    blob_b = Mock()
    blob_b.name = "prefix/b.json"
    blob_old = Mock()
    blob_old.name = "prefix/old.csv"
    bucket.list_blobs.return_value = [blob_a, blob_b, blob_old]

    sync_directory_to_gcs(bucket, tmp_path, "prefix")

    # Upload should have been called for a.csv and b.json
    assert "prefix/a.csv" in upload_blobs
    assert "prefix/b.json" in upload_blobs

    # The stale blob should have been deleted
    bucket.blob.assert_any_call("prefix/old.csv")
    # Find the mock that was created for the delete call
    all_blob_calls = [c.args[0] for c in bucket.blob.call_args_list]
    assert "prefix/old.csv" in all_blob_calls


def test_sync_directory_to_gcs_no_stale_blobs(tmp_path):
    (tmp_path / "a.csv").write_text("col\n1\n")

    bucket = Mock()
    blobs: dict[str, Mock] = {}

    def blob_side(name: str):
        b = Mock()
        blobs[name] = b
        return b

    bucket.blob.side_effect = blob_side
    bucket.name = "my-bucket"

    # Remote matches local exactly
    blob_a = Mock()
    blob_a.name = "prefix/a.csv"
    bucket.list_blobs.return_value = [blob_a]

    sync_directory_to_gcs(bucket, tmp_path, "prefix")

    # Only the upload blob should have been created, no delete calls
    assert "prefix/a.csv" in blobs
    # The blob for upload was called, but delete was never called on it
    # (delete_bucket_files is not called when there are no stale blobs)
    blob_calls = [c.args[0] for c in bucket.blob.call_args_list]
    # Only "prefix/a.csv" from the upload
    assert blob_calls == ["prefix/a.csv"]


def test_sync_directory_to_gcs_no_prefix(tmp_path):
    (tmp_path / "a.csv").write_text("col\n1\n")

    bucket = Mock()
    blobs: dict[str, Mock] = {}

    def blob_side(name: str):
        b = Mock()
        blobs[name] = b
        return b

    bucket.blob.side_effect = blob_side
    bucket.name = "my-bucket"

    blob_a = Mock()
    blob_a.name = "a.csv"
    blob_old = Mock()
    blob_old.name = "old.csv"
    bucket.list_blobs.return_value = [blob_a, blob_old]

    sync_directory_to_gcs(bucket, tmp_path)

    # old.csv should be deleted
    all_blob_calls = [c.args[0] for c in bucket.blob.call_args_list]
    assert "old.csv" in all_blob_calls


def test_list_bucket_files_with_prefix():
    bucket = Mock()
    blob_a = Mock()
    blob_a.name = "folder/a.csv"
    blob_b = Mock()
    blob_b.name = "folder/b.csv"
    bucket.list_blobs.return_value = [blob_a, blob_b]
    bucket.name = "my-bucket"
    files = [f.replace("\\", "/") for f in list_bucket_files(bucket, "folder")]
    assert files == ["folder/a.csv", "folder/b.csv"]
    bucket.list_blobs.assert_called_once_with(prefix="folder/")


def test_list_bucket_files_with_gs_path():
    bucket = Mock()
    blob = Mock()
    blob.name = "one-data/a.csv"
    bucket.list_blobs.return_value = [blob]
    bucket.name = "one-datacommons-staging"

    result = list_bucket_files(bucket, "gs://one-datacommons-staging/one-data")

    assert [f.replace("\\", "/") for f in result] == ["one-data/a.csv"]
    bucket.list_blobs.assert_called_once_with(prefix="one-data/")


def test_list_bucket_files_root():
    bucket = Mock()
    blob_a = Mock()
    blob_a.name = "a.csv"
    bucket.list_blobs.return_value = [blob_a]
    bucket.name = "my-bucket"
    assert list_bucket_files(bucket) == ["a.csv"]
    bucket.list_blobs.assert_called_once_with()


def test_list_bucket_files_missing_folder():
    bucket = Mock()
    bucket.list_blobs.return_value = []
    bucket.name = "my-bucket"

    with pytest.raises(FileNotFoundError):
        list_bucket_files(bucket, "missing")

    bucket.list_blobs.assert_called_once_with(prefix="missing/")


def test_get_unregistered_csv_files():
    bucket = Mock()
    blob_a = Mock()
    blob_a.name = "folder/a.csv"
    blob_extra = Mock()
    blob_extra.name = "folder/extra.csv"
    bucket.list_blobs.return_value = [blob_a, blob_extra]
    bucket.name = "my-bucket"
    cfg = _minimal_config()
    missing = get_unregistered_csv_files(bucket, cfg, "folder")
    assert missing == ["extra.csv"]


def test_get_unregistered_csv_files_with_prefix_removed():
    bucket = Mock()
    blob_a = Mock()
    blob_a.name = "prefix/sub/a.csv"
    blob_extra = Mock()
    blob_extra.name = "prefix/sub/b.csv"
    bucket.list_blobs.return_value = [blob_a, blob_extra]
    bucket.name = "my-bucket"

    cfg = _minimal_config("sub/a.csv")
    missing = get_unregistered_csv_files(bucket, cfg, "prefix")
    missing = [f.replace("\\", "/") for f in missing]

    assert missing == ["sub/b.csv"]


def test_get_missing_csv_files():
    bucket = Mock()
    blob_a = Mock()
    blob_a.name = "folder/a.csv"
    bucket.list_blobs.return_value = [blob_a]

    cfg = _minimal_config()
    cfg.inputFiles["extra.csv"] = ExplicitSchemaFile(
        provenance="prov",
        columnMappings=ColumnMappings(),
    )

    missing = get_missing_csv_files(bucket, cfg, "folder")

    assert missing == ["extra.csv"]


def test_get_missing_csv_files_with_prefix_added():
    bucket = Mock()
    blob_a = Mock()
    blob_a.name = "prefix/sub/a.csv"
    bucket.list_blobs.return_value = [blob_a]

    cfg = _minimal_config("sub/a.csv")
    cfg.inputFiles["sub/b.csv"] = ExplicitSchemaFile(
        provenance="prov",
        columnMappings=ColumnMappings(),
    )

    missing = get_missing_csv_files(bucket, cfg, "prefix")
    missing = [f.replace("\\", "/") for f in missing]

    assert missing == ["sub/b.csv"]


def test_delete_bucket_files():
    bucket = Mock()
    blobs: dict[str, Mock] = {}

    def blob_side(name: str):
        b = Mock()
        blobs[name] = b
        return b

    bucket.blob.side_effect = blob_side

    delete_bucket_files(bucket, ["a.csv", "b.csv"])

    assert set(blobs.keys()) == {"a.csv", "b.csv"}
    for b in blobs.values():
        b.delete.assert_called_once()


def test_get_bucket_files_csv_single():
    bucket = Mock()
    blob = Mock()
    blob.download_as_bytes.return_value = b"a,b\n1,2\n"
    bucket.blob.return_value = blob

    result = get_bucket_files(bucket, "a.csv")

    bucket.blob.assert_called_once_with("a.csv")
    blob.download_as_bytes.assert_called_once_with()
    expected = pd.DataFrame({"a": [1], "b": [2]})
    pd.testing.assert_frame_equal(result, expected)


def test_get_bucket_files_multiple_types():
    bucket = Mock()
    blob_csv = Mock()
    blob_json = Mock()
    blob_mcf = Mock()

    blob_csv.download_as_bytes.return_value = b"a,b\n1,2\n"
    blob_json.download_as_bytes.return_value = b'{"x": 1}'
    blob_mcf.download_as_bytes.return_value = (
        b'Node: dcid:n\nname: "N"\ntypeOf: dcid:T\n\n'
    )

    def blob_side(name: str):
        return {"a.csv": blob_csv, "b.json": blob_json, "c.mcf": blob_mcf}[name]

    bucket.blob.side_effect = blob_side

    result = get_bucket_files(bucket, ["a.csv", "b.json", "c.mcf"])

    expected_df = pd.DataFrame({"a": [1], "b": [2]})
    pd.testing.assert_frame_equal(result["a.csv"], expected_df)
    assert result["b.json"] == {"x": 1}
    assert result["c.mcf"].nodes[0].Node == "dcid:n"
