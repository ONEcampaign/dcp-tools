# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- `ProvenanceNode.source_link` is renamed to `source`, so a provenance's parent
  source now serializes as `source: dcid:source/<name>` (was `sourceLink:`), the property name
  Data Commons ingestion preprocessing expects.

## [1.0.0a1] - 2026-07-27

### Added

- `imports` arg on the `run_data_load` function and `--imports` flag on the `dataload`
  CLI command. This triggers a load of specific imports rather than all imports.
- Optional `LOAD_JOB_SERVICE_ACCOUNT` setting that sets which service account the load
  job impersonates. When unset, the caller's credentials are used.
- Support for multi-entity observations using custom dimensions, each declared using
  `custom:<name>` in `ColumnMappings` and a matching `dcid:<name>` in the StatVar's
  `observation_properties`.

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
- `Config.input_files` is now `list[InputFile]` (was a dict keyed by file name). Only the
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
  removed implicit (`variablePerColumn`) schema. Behaviour and the serialized `config.json` are
  unchanged; the arguments and field names are the same ones, in the snake_case spelling noted
  below.
- Single-entity StatVars don't emit `observationProperties` by default.
- **Replaced `build_stat_var_groups_from_strings` with `resolve_group_paths`.** The old
  function took a `Nodes` container and used the StatVar node's `member_of` as a scratch
  field, holding a raw path such as `"Economic/Employment"` until it was overwritten with
  the resolved group dcid. That is why `member_of` could not be validated. `resolve_group_paths`
  works on the path strings alone and returns the resolved dcid per path plus the
  `StatVarGroupNode` objects, so a node is never constructed with an invalid `member_of`.
  `csv_metadata_to_nodes` gained `parse_groups` and `group_namespace` and does the resolution
  between reading the CSV and building the nodes. `CustomDataManager.add_variables_to_mcf_from_csv`
  is unchanged.
- `rename_variable` normalizes a bare `old_name`/`new_name` to `dcid:<token>`, the same rule
  `add_variable_to_mcf` applies to `dcid`.
- **Renamed the node model classes to drop the `MCF` qualifier**, treating MCF as one
  serialization of a Data Commons graph node rather than the model's identity: `MCFNode` →
  `Node`, `MCFNodes` → `Nodes`, and every subclass.
- **Collapsed a node's duplicate `Node`/`dcid` properties into a single `dcid`.** A node's
  identifier is now `node.dcid`, which still serializes to the mandatory `Node:` line in MCF;
  the separate optional `dcid` property is removed.
- **`Node.mcf` is now the `Node.to_mcf()` method** (and `Nodes.to_mcf()`), matching the
  `to_dict()`/`to_json()` convention and leaving room for a future `to_jsonld()`.
- **The Python API is now snake_case throughout.** Node and `Config` attributes,
  `CustomDataManager` builder keyword arguments, and the `set_*` methods use snake_case
  (`node.type_of`, `add_variable_to_mcf(measured_property=...)`, `set_import_name(...)`). The
  serialized `config.json` and MCF wire format are unchanged: camelCase keys are preserved via
  pydantic aliases (`alias_generator=to_camel`). CSV column headers (e.g. `memberOf`) keep the
  Data Commons camelCase convention.
- **`export_all` writes and overwrites the complete bundle.** It no longer takes `mcf_file_names`
  or `override`. It writes `config.json`, the data CSVs, `vertical_specs.json` (when specs were
  added), and every MCF file you've added nodes to, overwriting anything already in the directory.
  Pass nothing for the full bundle; use `export_mcf_file` to write a single file.
- **Renamed `override` to `overwrite` on the export helpers and flipped the default to `True`**
  (overwrite). Affects `CustomDataManager.export_mcf_file`, `Nodes.export_to_mcf_file`, and
  `csv_metadata_to_mcf_file`.
- **Replaced `csv2mcf`'s `--override` flag with `--append`.** `csv2mcf` now overwrites the output
  file by default; pass `--append` to add to an existing file instead (which can produce duplicate
  `Node:` blocks on repeated runs).
- **`add_source` and `add_provenance` take separate `dcid`, `name`, and `description` parameters.**
  `dcid` is the identifier (minted with the `source/`/`provenance/` slug prefix); `name` is an
  optional human-readable label; `description` is optional longer text. Previously `name` was used
  as the identifier and the node's own `name` property was never set.
- **Renamed `CustomDataManager.remove_indicator` to `remove_variable`** (parameter `indicator_id`
  → `dcid`), matching the `variable` terminology used elsewhere (`rename_variable`,
  `add_variable_to_mcf`).

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
- The `PeerGroupDcidOrListPeerGroupDcid` and `TopicDcidOrListTopicDcid` type aliases.
  `PeerGroupDcidOrListPeerGroupDcid` was never referenced by any field, which is how the bypass
  in it went unnoticed. `TopicDcidOrListTopicDcid` was the permissive member of
  `TopicNode.relevant_variable`'s union, and nothing references it now that the union has
  collapsed. The `PeerGroupDcid` and `TopicDcid` they wrapped are still used, as the types of
  `StatVarPeerGroupNode.dcid` and `TopicNode.dcid`.

### Fixed

- `rename_variable` left the `Nodes` lookup index keyed by the old name, so variable removal
  raised "not found" for the renamed node and still resolved the old name. The rename now goes
  through a new `Nodes.rename`, which keeps the index in step.
- `export_data`, `export_mcf_file`, and `export_vertical_specs` raised `OSError` when the
  target file name (an `add_input_file` path, an `mcf_file_name`, or a `vertical_specs_file`)
  nested in a subdirectory that did not yet exist. Each now creates the parent directory
  before writing.
- `add_variable_to_mcf` did not normalize a bare `dcid` to `dcid:<token>`, unlike the
  schema-node builders, so a bare token raised a `ValidationError` there while working
  everywhere else. It now goes through the same `ensure_dcid` normalization, as do its
  `population_type`, `measured_property`, `measurement_qualifier` and
  `measurement_denominator` arguments, which had the same gap.
- `DcidOrListDcid` used a `PlainValidator`, which replaces the wrapped `Dcid` schema
  instead of running before it, so the `dcid:` prefix check never executed. Any string,
  including one with no `dcid:` prefix at all, passed through unvalidated and landed in
  the MCF verbatim. This affected `type_of` on every node, `relevant_variable`,
  `observation_properties` and `member` on StatVar nodes, and `included_in`, `sub_class_of`,
  `domain_includes`, `range_includes` and `sub_property_of` on the schema-node builders.
  These fields now normalize a bare token to `dcid:<token>` (the same rule `ensure_dcid`
  already applied at the builder level) and reject anything empty or whitespace-bearing.
  A non-string value now raises `ValidationError` rather than being accepted silently.
  This is a behaviour change for anyone passing a bare token to one of these fields today
  and relying on it staying bare.
- `GroupDcidOrListGroupDcid` had the same `PlainValidator` bypass, so `StatVarNode.member_of`
  accepted any string and wrote it to the MCF verbatim. It now enforces the `GroupDcid`
  pattern, which requires a `g/` segment, so `member_of="dcid:myGroup"` now raises and
  `member_of="one/g/economy"` is minted to `dcid:one/g/economy`. `TopicNode.relevant_variable`
  was a union of the fixed type with two unfixed ones, so a value the fixed branch rejected
  still validated through a permissive branch. Its type is now plain `DcidOrListDcid`, which
  accepts exactly the same values the union was meant to allow, group and topic dcids included.
- `Node` now validates on assignment (`validate_assignment=True`). Restoring the patterns
  above would otherwise guard construction only, and the value that reaches the MCF file is
  often written by assignment, so `node.member_of = "garbage"` and `Nodes.rename` could
  still put an invalid dcid in the output. Both now raise. Assigned values are also cleaned
  of line breaks and trailing spaces the way constructed ones are, for declared fields and
  for the extra keys that carry arbitrary MCF properties.
- `csv_metadata_to_nodes` returned a `Nodes` whose lookup index did not include the
  StatVarGroup nodes it appended, so a later `remove` or `rename` of a group node on the
  returned container raised "not found".
- `add_variables_to_mcf_from_csv(parse_groups=True)` raised `AttributeError` when the CSV had
  no `memberOf` column, or when a row left it blank. The missing column now raises a
  `ValueError` naming it, and a blank value leaves that node's `member_of` unset.
- A group path with a whitespace-only segment, such as `"Economic/\t/Health"`, minted a group
  whose dcid ended in a bare `g/` with no slug. Only `/` and spaces were stripped, so a tab or
  line break survived the split and `to_camelCase` reduced it to an empty slug. Such segments
  are now dropped.
- **Breaking:** `TopicNode.dcid` is now typed `TopicDcid` rather than a hand-rolled pattern that
  looked for a `topic/` segment anywhere in the string without requiring the `dcid:` prefix.
  `dcid="topic/x"` validated and reached the MCF unprefixed, as did `"xtopic/y"` and
  `"notdcid:topic/x"`. Every other node type's id already required the prefix, and
  `rename_variable` mints one on lookup, so a topic stored under a bare id could not be found.
  Those values now raise, whitespace inside the id is rejected instead of being carried into
  the MCF, and `"dcid: topic/x"` is normalized to `"dcid:topic/x"`. Add the `dcid:` prefix to
  the `Node` column of any topic CSV; Data Commons rejects unprefixed node ids on load anyway.

**Migration:**

- Replace `add_implicit_schema_file` calls with `add_input_file` and supply a
  `column_mappings` argument. Data must be in the variable-per-row format (one observation
  per row). See the [Data Commons custom data documentation](https://docs.datacommons.org/custom_dc/custom_data.html).
- Drop any `redeploy` calls, and update your settings: rename
  `CLOUD_RUN_JOB_NAME` → `LOAD_JOB_NAME` and `CLOUD_JOB_REGION` → `LOAD_JOB_REGION`, add
  `LOAD_JOB_SERVICE_ACCOUNT` if the job runs under an impersonated service account.
- Replace `entity` on `ColumnMappings` with `observationAbout`.
- Rename `ExplicitSchemaFile` → `InputFile` and `add_explicit_schema_file` → `add_input_file`.
  Names only; behaviour is unchanged, and the arguments are the same ones in the snake_case
  spelling below.
- Rename `export_mfc_file` → `export_mcf_file`.
- Check any `member_of` value you pass to `add_variable_to_mcf`, or any `memberOf` value you
  supply in a StatVar CSV (the CSV header keeps the camelCase spelling). It
  must now resolve to a group dcid containing `g/`, for example `one/g/economy` or
  `dcid:one/g/economy`. A value such as `dcid:economy` is rejected instead of being written to
  the MCF as-is.
- Replace direct calls to `build_stat_var_groups_from_strings` with either
  `csv_metadata_to_nodes(..., parse_groups=True, group_namespace=...)` or `resolve_group_paths`.
- Drop the `MCF` infix from node model class names (`MCFNode` → `Node`, `StatVarMCFNode` →
  `StatVarNode`, and so on) and the `MCFNodes` container → `Nodes`.
- Read a node's id via `.dcid` (not `.Node`); the separate `dcid` property is gone.
- Call `node.to_mcf()` instead of `node.mcf`.
- Convert builder keyword arguments, node/`Config` attributes and `set_*` methods to
  snake_case (`measuredProperty` → `measured_property`, `typeOf` → `type_of`, `set_importName`
  → `set_import_name`, and so on). The exported `config.json` and MCF are unchanged.
- Drop `mcf_file_names` and `override` from `export_all` calls: pass nothing for the full bundle,
  and use `export_mcf_file` for a single file. `export_all` now overwrites what's already there.
- Rename `override=` → `overwrite=` on `export_mcf_file`, `Nodes.export_to_mcf_file` and
  `csv_metadata_to_mcf_file` (all now overwrite by default).
- Replace `csv2mcf --override` with the default (overwrite), or `--append` to add to an existing
  file.
- In `add_source`/`add_provenance` calls, pass the identifier as `dcid=` (was `name=`); optionally
  pass `name=` for a human-readable label.
- Rename `remove_indicator(...)` calls to `remove_variable(...)`; the positional id argument is
  unchanged, and the keyword is now `dcid` (was `indicator_id`).

## [0.1.1] - 2026-02-19

### Added

- `--sync` flag for `upload` and `pipeline` CLI commands. When enabled, remote blobs
  that no longer have a local counterpart are deleted after uploading.
- `sync_directory_to_gcs` function in `storage.py` that composes upload + stale blob cleanup.
- `sync` parameter on `upload_to_cloud_storage` in `pipeline.py`.

## [0.1.0] - 2026-02-13

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

[0.1.0]: https://github.com/ONEcampaign/dcp-tools/releases/tag/v0.1.0
[0.1.1]: https://github.com/ONEcampaign/dcp-tools/compare/v0.1.0...v0.1.1
[1.0.0a1]: https://github.com/ONEcampaign/dcp-tools/compare/v0.1.1...v1.0.0a1
[unreleased]: https://github.com/ONEcampaign/dcp-tools/compare/v1.0.0a1...HEAD
