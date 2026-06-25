# Changelog

## v1.0.0 (in development)
- Stable release of the `dcp-tools` package
- **Breaking:** removed implicit-schema support — `add_implicit_schema_file`,
  `add_variable_to_config`, and the `ImplicitSchemaFile` / `ObservationProperties` / `Variable`
  model classes are gone. Loading a legacy `variablePerColumn` config now raises `ValueError`.
  Migrate by using `add_explicit_schema_file` with `columnMappings`; see
  [Data Commons custom data docs](https://docs.datacommons.org/custom_dc/custom_data.html).

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