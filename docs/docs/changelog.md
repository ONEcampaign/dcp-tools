# Changelog

## v1.0.0 (in development)
- Stable release of the `dcp-tools` package
- **Breaking:** removed support for the second, implicit import mechanism —
  `add_implicit_schema_file`, `add_variable_to_config`, and the `ImplicitSchemaFile` /
  `Variable` model classes are gone (`ObservationProperties` is retained, but now carries
  file-level constants on `InputFile`). Loading a legacy
  `variablePerColumn` config now raises `ValueError`. Migrate by using `add_input_file` with
  `columnMappings`; see
  [Data Commons custom data docs](https://docs.datacommons.org/custom_dc/custom_data.html).
- **Breaking:** with a single import format left, the input-file API drops the "explicit"
  qualifier: `ExplicitSchemaFile` is now `InputFile` and `add_explicit_schema_file` is now
  `add_input_file`. Arguments and the generated `config.json` are unchanged.
- **Breaking:** `export_mfc_file` is now spelled `export_mcf_file`, and
  `csv_metadata_to_mfc_file` is now `csv_metadata_to_mcf_file`.
- Fixed `rename_variable`, which left the renamed node unreachable by its new name. A
  following `remove_indicator` raised "not found" until you passed the pre-rename name.
- Fixed `export_data`, `export_mcf_file`, and `export_vertical_specs` raising `OSError`
  when the target file name nested in a subdirectory that did not yet exist (for example
  an `add_input_file` name such as `"sub/gdp.csv"`). Each now creates the parent
  directory before writing.
- Fixed `add_variable_to_mcf`, which did not normalize a bare `Node` to `dcid:<token>`
  like the schema-node builders do, so a bare token raised a `ValidationError` there
  while working everywhere else. Its `populationType`, `measuredProperty`,
  `measurementQualifier` and `measurementDenominator` arguments had the same gap and
  now accept bare tokens too.
- Fixed `DcidOrListDcid`, which used a `PlainValidator` that replaced the wrapped `Dcid`
  schema rather than running before it, so the `dcid:` prefix check never ran. Any
  string, prefixed or not, passed through and landed in the MCF verbatim. This affected
  `typeOf` on every MCF node, `relevantVariable`, `observationProperties` and `member` on
  StatVar nodes, and `includedIn`, `subClassOf`, `domainIncludes`, `rangeIncludes` and
  `subPropertyOf` on the schema-node builders. These fields now normalize a bare token to
  `dcid:<token>` and reject anything empty or whitespace-bearing, and a non-string value
  now raises rather than being accepted silently. Breaking for anyone
  passing a bare token to one of these fields today and relying on it staying bare. The
  group/peer-group/topic variants have the same gap and are not fixed here, since
  `memberOf`'s use as a scratch field in `build_stat_var_groups_from_strings` needs
  sorting out first. That leaves `StatVarMCFNode.memberOf` and
  `TopicMCFNode.relevantVariable` unguarded, the latter because its type unions the fixed
  and unfixed variants. `StatVarMCFNode.relevantVariable` is fixed. Tracked separately.
- **Breaking:** re-pointed the data load flow at the DCP v1.1.0 prep job. `run_data_load`
  now triggers the preprocessing job. The `redeploy` command and `redeploy_service` are removed.
  Load-job settings are renamed: `CLOUD_RUN_JOB_NAME` → `LOAD_JOB_NAME`,
  `CLOUD_JOB_REGION` → `LOAD_JOB_REGION`, plus a new optional `LOAD_JOB_SERVICE_ACCOUNT`.
  New `--imports` flag on `dataload` loads specific named imports.

## v0.1.0 (in development)
- Initial release of the `dcp-tools` package for external preview and testing

## v0.0.9 (2025-09-17)
- Added new configuration options, including `set_customIdNamespace`, `set_customSvgPrefix`,
`set_defaultCustomRootStatVarGroupName` and `set_svHierarchyPropsBlocklist`.

## v0.0.8 (2025-09-03)
- Removed white space between quoted items do defend against a bug with data loading on
the DC side.

## v0.0.7 (2025-08-27)
- Handle linebreaks and trailing spaces by removing them. This prevents errors when serialising
to MCF which could (quietly) break the data loading job.

## v0.0.6 (2025-08-14)
- Node name is now an optional attribute. This enables easily appending data to existing Base DC Nodes.

## v0.0.5 (2025-08-14)
- Nodes can now contain a single `dcid` or a list of `dcids`

## v0.0.4 (2025-07-22)
- Improved how groups strings are transformed to camelCase by dealing with
additional special characters
- Removed option to override input and output folders on the data load job.

## v0.0.3 (2025-07-18)
- Fixes two bugs related to MFC files. It now enforces the `dcid:` prefix for Node and
automatically trims spaces between `dcid:` and the start of the id string.

## v0.0.2 (2025-07-07)
- Minor update to documentation and release to PyPI

## v0.0.1 (2025-07-07)
- Initial release of the `dcp-tools`