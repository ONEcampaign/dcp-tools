# Changelog

## [Unreleased]

### Added
- `imports` arg on the `run_data_load` function and `--imports` flag on the `dataload`
  CLI command. This triggers a load of specific imports rather than all imports.
- Optional `LOAD_JOB_SERVICE_ACCOUNT` setting that sets which service account the load
  job impersonates. When unset, the caller's credentials are used.

### Changed
- **Renamed the package from `bblocks-datacommons-tools` to `dcp-tools`.** The import
  path is now `dcp_tools` (was `bblocks.datacommons_tools`). Installing the old
  `bblocks-datacommons-tools` distribution now pulls in `dcp-tools` and re-exports it
  with a `DeprecationWarning`; update imports to `dcp_tools` at your convenience.
- Minimum supported Python is now 3.13 (was 3.11).
- Packaging now follows the `bblocks-projects` copier template (ruff lint preset, `ty`
  type checking, pre-commit hooks, PyPI trusted publishing).
- Re-pointed the data load flow at the DCP prep job, using the `IngestionJobClient`.
- Renamed load job settings: `CLOUD_RUN_JOB_NAME` -> `LOAD_JOB_NAME` and
  `CLOUD_JOB_REGION` -> `LOAD_JOB_REGION`.

### Removed
- `add_implicit_schema_file` method on `CustomDataManager`.
- `add_variable_to_config` method on `CustomDataManager`.
- `ImplicitSchemaFile`, `ObservationProperties`, and `Variable` model classes.
- The `redeploy` CLI command and the `redeploy_service` and
  `redeploy_cloud_run_service` functions. The service restart is now owned by the
  ingestion workflow.
- Settings which are no longer used: `CLOUD_SQL_DB_NAME`, `CLOUD_SQL_REGION`,
  `CLOUD_SERVICE_REGION`, `CLOUD_RUN_SERVICE_NAME`, and `DATACOMMONS_SERVICE_IMAGE`. 

### Changed
- `Config.inputFiles` is now `Dict[str, ExplicitSchemaFile]` — the implicit
  (`variablePerColumn`) path is no longer supported. Loading a legacy config that contains
  `"format": "variablePerColumn"` now raises a clear `ValueError` with a migration message
  instead of a generic Pydantic `ValidationError`.
- `ExplicitSchemaFile` now rejects unknown keys (`extra="forbid"`).

**Migration:**
- Replace `add_implicit_schema_file` calls with `add_explicit_schema_file` and supply a
  `columnMappings` argument. See the [Data Commons custom data documentation](https://docs.datacommons.org/custom_dc/custom_data.html) for the
  explicit-schema format.
- Drop any `redeploy` calls, and update your settings: rename
  `CLOUD_RUN_JOB_NAME` → `LOAD_JOB_NAME` and `CLOUD_JOB_REGION` → `LOAD_JOB_REGION`, add
  `LOAD_JOB_SERVICE_ACCOUNT` if the job runs under an impersonated service account.

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
