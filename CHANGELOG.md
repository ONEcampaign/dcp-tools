# Changelog

## [Unreleased]

### Added
- `imports` arg on the `run_data_load` function and `--imports` flag on the `dataload`
  CLI command. This triggers a load of specific imports rather than all imports.
- Optional `LOAD_JOB_SERVICE_ACCOUNT` setting that sets which service account the load
  job impersonates. When unset, the caller's credentials are used.
- Support for multi-entity observations using custom dimensions, each declared using
  `custom:<name>` in `ColumnMappings` and a matching `dcid:<name>` in the StatVar's
  `observationProperties`.

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
- `Config.inputFiles` is now `list[InputFile]` (was a dict keyed by file name). Only the
  variable-per-row format is supported: loading a legacy config that contains
  `"format": "variablePerColumn"` now raises a clear `ValueError` with a migration message
  instead of a generic Pydantic `ValidationError`.
- `InputFile` now rejects unknown keys (`extra="forbid"`).
- **Renamed `export_mfc_file` to `export_mcf_file` and `csv_metadata_to_mfc_file` to
  `csv_metadata_to_mcf_file`**, correcting a transposition in both names
  (`csv_metadata_to_mcf_file` is exported from the package root). The old spellings are
  gone; update any calls.
- **Renamed the input-file API now that there is a single import format.** The
  `ExplicitSchemaFile` model is now `InputFile`, and `CustomDataManager.add_explicit_schema_file`
  is now `add_input_file`. The "explicit schema" name only made sense as a contrast with the
  removed implicit (`variablePerColumn`) schema. Signatures, field names, and the serialized
  `config.json` are unchanged.
- Single-entity StatVars don't emit `observationProperties` by default.

### Fixed
- `rename_variable` left the `MCFNodes` lookup index keyed by the old name, so
  `remove_indicator` raised "not found" for the renamed node and still resolved the old
  name. The rename now goes through a new `MCFNodes.rename`, which keeps the index in step.
- `export_data`, `export_mcf_file`, and `export_vertical_specs` raised `OSError` when the
  target file name (an `add_input_file` path, an `mcf_file_name`, or a `verticalSpecsFile`)
  nested in a subdirectory that did not yet exist. Each now creates the parent directory
  before writing.
- `add_variable_to_mcf` did not normalize a bare `Node` to `dcid:<token>`, unlike the
  schema-node builders, so a bare token raised a `ValidationError` there while working
  everywhere else. It now goes through the same `ensure_dcid` normalization, as do its
  `populationType`, `measuredProperty`, `measurementQualifier` and
  `measurementDenominator` arguments, which had the same gap.
- `DcidOrListDcid` used a `PlainValidator`, which replaces the wrapped `Dcid` schema
  instead of running before it, so the `dcid:` prefix check never executed. Any string,
  including one with no `dcid:` prefix at all, passed through unvalidated and landed in
  the MCF verbatim. This affected `typeOf` on every MCF node, `relevantVariable`,
  `observationProperties` and `member` on StatVar nodes, and `includedIn`, `subClassOf`,
  `domainIncludes`, `rangeIncludes` and `subPropertyOf` on the schema-node builders.
  These fields now normalize a bare token to `dcid:<token>` (the same rule `ensure_dcid`
  already applied at the builder level) and reject anything empty or whitespace-bearing.
  A non-string value now raises `ValidationError` rather than being accepted silently.
  This is a behaviour change for anyone passing a bare token to one of these fields today
  and relying on it staying bare. The group/peer-group/topic variants
  (`GroupDcidOrListGroupDcid` and friends) have the same gap and are not fixed here.
  `memberOf`'s use as a scratch field in `build_stat_var_groups_from_strings` needs sorting
  out first, and it is tracked separately. Two fields therefore stay unguarded:
  `StatVarMCFNode.memberOf`, and `TopicMCFNode.relevantVariable`, whose type is a union of
  the fixed and unfixed variants, so a value the fixed branch rejects still validates
  through an unfixed one. `StatVarMCFNode.relevantVariable` is unaffected and is fixed.

### Removed
- `add_implicit_schema_file` method on `CustomDataManager`.
- `add_variable_to_config` method on `CustomDataManager`.
- `ImplicitSchemaFile` and `Variable` model classes. `ObservationProperties` is retained but
  repurposed: it is no longer nested under a variable definition, and now carries the
  file-level constant observation properties on `InputFile`. It also accepts custom keys
  (`extra="allow"`, was `extra="forbid"`); the four standard fields are unchanged.
- The `redeploy` CLI command and the `redeploy_service` and
  `redeploy_cloud_run_service` functions. The service restart is now owned by the
  ingestion workflow.
- Settings which are no longer used: `CLOUD_SQL_DB_NAME`, `CLOUD_SQL_REGION`,
  `CLOUD_SERVICE_REGION`, `CLOUD_RUN_SERVICE_NAME`, and `DATACOMMONS_SERVICE_IMAGE`.
- **BREAKING**: `entity` key on `ColumnMappings`. Use `observationAbout` for single-entity data or
  `custom:<name>` for multi-entity dimensions.

**Migration:**
- Replace `add_implicit_schema_file` calls with `add_input_file` and supply a
  `columnMappings` argument. Data must be in the variable-per-row format (one observation
  per row). See the [Data Commons custom data documentation](https://docs.datacommons.org/custom_dc/custom_data.html).
- Drop any `redeploy` calls, and update your settings: rename
  `CLOUD_RUN_JOB_NAME` → `LOAD_JOB_NAME` and `CLOUD_JOB_REGION` → `LOAD_JOB_REGION`, add
  `LOAD_JOB_SERVICE_ACCOUNT` if the job runs under an impersonated service account.
- Replace `entity` on `ColumnMappings` with `observationAbout`.
- Rename `ExplicitSchemaFile` → `InputFile` and `add_explicit_schema_file` → `add_input_file`.
  Names only; arguments and behaviour are unchanged.
- Rename `export_mfc_file` → `export_mcf_file`.

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
