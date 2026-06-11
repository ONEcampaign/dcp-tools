# Changelog

## [Unreleased]

### Removed
- `add_implicit_schema_file` method on `CustomDataManager`.
- `add_variable_to_config` method on `CustomDataManager`.
- `ImplicitSchemaFile`, `ObservationProperties`, and `Variable` model classes.

### Changed
- `Config.inputFiles` is now `Dict[str, ExplicitSchemaFile]` — the implicit
  (`variablePerColumn`) path is no longer supported. Loading a legacy config that contains
  `"format": "variablePerColumn"` now raises a clear `ValueError` with a migration message
  instead of a generic Pydantic `ValidationError`.
- `ExplicitSchemaFile` now rejects unknown keys (`extra="forbid"`).

**Migration:** replace `add_implicit_schema_file` calls with `add_explicit_schema_file` and
supply a `columnMappings` argument. See the
[Data Commons custom data documentation](https://docs.datacommons.org/custom_dc/custom_data.html)
for the explicit-schema format.

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
