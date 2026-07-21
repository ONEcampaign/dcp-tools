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
  passing a bare token to one of these fields today and relying on it staying bare.
- **Breaking:** `memberOf` on a StatVar now has to be a real group dcid. It had the same
  bypass, so any string reached the MCF verbatim; it now requires a `g/` segment, so
  `one/g/economy` is minted to `dcid:one/g/economy` and `dcid:economy` is rejected. Check the
  `memberOf` values in your StatVar CSVs and `add_variable_to_mcf` calls.
- **Breaking:** `relevantVariable` on a Topic node is now plain `DcidOrListDcid`. Its type used
  to combine the fixed variant with two unfixed ones, so a value the fixed one rejected still
  got through the others. It accepts the same StatVar, group and topic dcids as before, and
  now rejects the malformed values that used to slip past.
- **Breaking:** MCF nodes now validate on assignment, not only on construction. Setting a
  field to an invalid value, for example `node.memberOf = "garbage"` or renaming a node to a
  token with no `dcid:` prefix, raises instead of quietly writing it to the MCF file.
- **Breaking:** `build_stat_var_groups_from_strings` is replaced by `resolve_group_paths`. It
  used `memberOf` to hold an unresolved group path such as `"Economic/Employment"` until it
  was overwritten, which is what blocked validating the field. Group paths are now resolved
  before the nodes are built. If you call it directly, use
  `csv_metadata_to_nodes(..., parse_groups=True, group_namespace=...)` instead.
  `add_variables_to_mcf_from_csv` is unchanged.
- Fixed `add_variables_to_mcf_from_csv(parse_groups=True)` raising `AttributeError` when the
  CSV had no `memberOf` column or a row left it blank. The missing column now raises a clear
  `ValueError`, and a blank value leaves that node's `memberOf` unset.
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