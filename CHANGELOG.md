# Changelog

## [0.1.1] - 2026-02-19

### Added
- `--sync` flag for `upload` and `pipeline` CLI commands. When enabled, remote blobs
  that no longer have a local counterpart are deleted after uploading.
- `sync_directory_to_gcs` function in `storage.py` that composes upload + stale blob cleanup.
- `sync` parameter on `upload_to_cloud_storage` in `pipeline.py`.

## [0.1.0] - 2025-02-13

### Added
- Support for Application Default Credentials (ADC) as an alternative to service account JSON keys.
  `GCP_CREDENTIALS` is now optional — when not provided, Google client libraries automatically
  use ADC (e.g. via `gcloud auth application-default login`).

### Changed
- Switched build system from Poetry to uv.
- Switched linter/formatter from Black to Ruff.
- Widened `google-cloud-run` version constraint from `<0.11.0` to `<1.0.0`.
- Updated all package dependencies.

### Fixed
- Config file merge order is now deterministic across platforms (sorted by path).
