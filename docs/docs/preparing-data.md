# Preparing data

`CustomDataManager` builds a Data Commons Platform import bundle (a `config.json` file, CSV data,
and `.mcf` files) without hand-editing any of the three. Each section below is a standalone
recipe. Jump to the one you need.

!!! note
    Assumes `dcp-tools` is installed (`pip install dcp-tools`). See
    [Getting started](getting-started.md) if it isn't.

## How to create a `CustomDataManager`

```python
from dcp_tools import CustomDataManager

manager = CustomDataManager()
```

This creates a blank config (an empty `inputFiles` list) and one empty MCF collection named
`custom_nodes.mcf`. Every `add_*`/`set_*` method below returns the manager, so calls chain.

To load files you already have:

```python
manager = CustomDataManager(
    config_file="path/to/config.json",
    mcf_files=["path/to/provenance.mcf", "path/to/custom_nodes.mcf"],
)
```

`mcf_files` takes one path or a list. Each file is loaded and keyed internally by its filename.
To merge several `config.json` files from a directory tree into one manager, see
[How to merge config files](#how-to-merge-config-files).

## How to register a source and provenance

Every input file must reference a provenance, and every provenance must reference a source. Add
the source first:

```python
from dcp_tools import CustomDataManager

manager = CustomDataManager()

manager.add_source(
    name="ONEData",
    url="https://data.one.org",
)
manager.add_provenance(
    name="ONEClimateFinance",
    url="https://datacommons.one.org/data/climate-finance-files",
    source="ONEData",
)
```

This writes two nodes to `provenance.mcf` (the default file for both methods): a `dcid:Source`
node at `dcid:source/ONEData`, and a `dcid:Provenance` node at `dcid:provenance/ONEClimateFinance`
linking to it. `add_provenance` raises `ValueError` if `source` isn't registered yet.

!!! note
    `name` mints part of a dcid. A bare name becomes `dcid:source/<name>` or
    `dcid:provenance/<name>`. An already `dcid:`-prefixed name is used as-is. Names can't
    contain whitespace (`"ONEData"`, not `"ONE Data"`). Put a whitespace-friendly display string
    in `description=` instead. See [Why config.json and MCF](dc-schemas.md) for why the importer
    needs dcids shaped this way.

Both methods take `description`, `license`, and `isPartOf`. `add_provenance` additionally takes
`licenseType`, `lastDataRefreshDate`, `nextDataRefreshDate`, `nextSourceReleaseDate`,
`sourceReleaseFrequency`, `earliestObservationDate`, `latestObservationDate`, and `curator`. Use
`additional_properties={"someProperty": "value"}` for anything else. Pass `override=True` to
replace a node that's already registered under the same name.

!!! warning "Heads up"
    `provenance.mcf` isn't exported automatically. List it explicitly when you export:

    ```python
    manager.export_all("output", mcf_file_names=["provenance.mcf"])
    ```

    If a registered input file references a provenance whose MCF file isn't in
    `mcf_file_names`, `export_all` raises before writing anything, rather than shipping a
    `config.json` with a dangling reference. See
    [How to validate and export the bundle](#how-to-validate-and-export-the-bundle).

## How to register a single-entity input file

Use this when each row of data is about one entity (a country, a facility, a person).

```python
import pandas as pd

df = pd.DataFrame({
    "country": ["country/KEN", "country/BGD", "country/KEN"],
    "year": [2022, 2022, 2023],
    "variable": ["climateFinanceProvidedCommitments"] * 3,
    "value": [4.2, 1.8, 5.1],
})

manager.add_input_file(
    file_name="climate_finance_commitments.csv",
    provenance="ONEClimateFinance",
    data=df,
    columnMappings={
        "observationAbout": "country",
        "date": "year",
        "variable": "variable",
        "value": "value",
    },
    observationProperties={"unit": "USDollar"},
)
```

`columnMappings` keys map a role to a CSV column name. Allowed keys: `variable`,
`observationAbout`, `date`, `value`, `unit`, `scalingFactor`, `measurementMethod`,
`observationPeriod`, plus `custom:<name>` for multi-entity data (see the next section).
`observationAbout` is the entity column for single-entity data. It holds a dcid per row (here,
country dcids like `country/KEN`).

`observationProperties` here differs from `add_variable_to_mcf`'s parameter of the same
name. On `add_input_file` it's a dict of file-level constants applied to every row (every
observation in this file is in US dollars), not a list of dcid refs.

Data is optional at registration:

```python
manager.add_input_file(
    file_name="climate_finance_disbursements.csv",
    provenance="ONEClimateFinance",
    columnMappings={
        "observationAbout": "country",
        "date": "year",
        "variable": "variable",
        "value": "value",
    },
)
# ...later, once the DataFrame is ready:
manager.add_data(df, "climate_finance_disbursements.csv")
```

`add_data` raises `ValueError` if `file_name` isn't already registered via `add_input_file`. To
register many files by glob pattern instead of one at a time, pass `pattern=` instead of
`file_name=`. Pattern entries are config-only and can't carry a `data=` DataFrame.

## How to register multi-entity observations with custom dimensions

Use this when a row of data is about more than one entity, such as a bilateral flow between a
provider and a recipient country, rather than a value about a single country.

```python
import pandas as pd

flows = pd.DataFrame({
    "provider": ["country/KEN", "country/KEN", "country/BGD"],
    "recipient": ["country/BGD", "country/UGA", "country/UGA"],
    "year": [2022, 2022, 2022],
    "variable": ["climateFinanceBilateralFlow"] * 3,
    "value": [1.4, 0.9, 0.6],
})

manager.add_input_file(
    file_name="bilateral_climate_finance_flows.csv",
    provenance="ONEClimateFinance",
    data=flows,
    columnMappings={
        "variable": "variable",
        "date": "year",
        "value": "value",
        "custom:providerCountry": "provider",
        "custom:recipientCountry": "recipient",
    },
)

manager.add_variable_to_mcf(
    Node="climateFinanceBilateralFlow",
    name="Climate finance bilateral flow",
    description="Bilateral climate finance commitments between a provider and a recipient country.",
    statType="dcid:measuredValue",
    observationProperties=["dcid:providerCountry", "dcid:recipientCountry"],
)
```

There's no `observationAbout` here. Multi-entity rows use one `custom:<name>` mapping key per
dimension instead (`ColumnMappings` collects any `custom:`-prefixed key automatically, so you
don't build the `customDimensions` dict by hand). Each `custom:<name>` key must have a matching
`dcid:<name>` entry in the StatVar's `observationProperties` list. `custom:providerCountry` pairs
with `dcid:providerCountry`.

!!! note
    `providerCountry` and `recipientCountry` are properties, not entities. If they aren't already
    part of the base Data Commons schema, declare them with `add_property` first (see the next
    section).

See [Why config.json and MCF](dc-schemas.md#observationabout-vs-custom-dimensions-why-bilateral-data-needs-a-different-mechanism)
for why `observationAbout` can't represent a row about two entities.

## How to declare StatVars and custom schema nodes

`CustomDataManager` has six MCF node builders. Use `add_variable_to_mcf` for the StatVars
themselves. Use the other five when your data needs a schema concept Data Commons doesn't already
define.

| Method | Emits | Use when |
|---|---|---|
| `add_variable_to_mcf` | `dcid:StatisticalVariable` | Declaring a StatVar (see above) |
| `add_entity_type` | `dcid:Class` | Your data describes something Data Commons doesn't have a `Class` for yet, such as a program type or a facility category |
| `add_event_type` | `dcid:Class` (`subClassOf` defaults to `dcid:Event`) | Your data is about events (a pledge announcement, a policy change) rather than a state |
| `add_property` | `dcid:Property` | You need a new predicate, such as a custom dimension from the previous section |
| `add_unit` | `dcid:UnitOfMeasure` | Your values are in a unit Data Commons doesn't already define |
| `add_measurement_method` | `dcid:MeasurementMethodEnum` | You want to record how an observation was produced (survey, estimate, administrative data) |

All six accept a bare or `dcid:`-prefixed `Node` token. Bare tokens are normalized to
`dcid:<token>` (no namespace segment, unlike source/provenance names). `add_measurement_method` is
the only one where `name` is optional.

Declaring the StatVar the single-entity input file from earlier references:

```python
manager.add_variable_to_mcf(
    Node="climateFinanceProvidedCommitments",
    name="Climate finance committed",
    description="Bilateral climate finance commitments provided by a country.",
    statType="dcid:measuredValue",
    populationType="Country",
    measuredProperty="amount",
)
```

This emits a `dcid:StatisticalVariable` node to `custom_nodes.mcf` (the default file for this
builder). `populationType` and `measuredProperty` go through the same bare-or-`dcid:` normalization
as `Node`.

Declaring the two properties the multi-entity StatVar from the previous section depends on:

```python
manager.add_property(
    Node="providerCountry",
    name="provider country",
    description="The country providing climate finance in a bilateral flow.",
    domainIncludes="StatisticalVariable",
    rangeIncludes="Country",
)
manager.add_property(
    Node="recipientCountry",
    name="recipient country",
    description="The country receiving climate finance in a bilateral flow.",
    domainIncludes="StatisticalVariable",
    rangeIncludes="Country",
)
```

This mints `dcid:providerCountry` and `dcid:recipientCountry`. These are the same tokens the
StatVar's `observationProperties` and the input file's `custom:` columnMappings keys referenced.

`add_entity_type` and `add_event_type` take an `includedIn` kwarg that's a bare **provenance**
name, not a dcid, unlike every other ref parameter on these builders:

```python
manager.add_entity_type(
    Node="ClimateFinanceProgram",
    name="Climate finance program",
    description="A named climate finance program or initiative tracked by ONE.",
    includedIn="ONEClimateFinance",
)
```

The provenance must already be registered via `add_provenance`, or this raises `ValueError`. The
builder expands one bare name into `includedIn` dcids for **both** the Provenance node and its
linked Source node.

## How to add StatVar groups and bulk-import variables from a CSV

Add a top-level StatVarGroup for all of an organization's custom variables:

```python
manager.add_variable_group_to_mcf(
    Node="dcid:one/g/ONEData",
    name="ONE Data",
    specializationOf="dcid:dc/g/Root",
)
```

`Node` must contain `g/`. `specializationOf` is `"dcid:dc/g/Root"` for a top-level group, or
another group's dcid for a sub-group. Unlike the schema-node builders above,
`add_variable_group_to_mcf` doesn't normalize a bare `Node`. Pass it already `dcid:`-prefixed.

To declare many StatVars at once instead of calling `add_variable_to_mcf` per variable, put them
in a CSV with one row per StatVar and columns matching `StatVarMCFNode` field names:

```csv
Node,name,statType,memberOf
dcid:climateFinanceProvidedGrants,Climate finance committed as grants,dcid:measuredValue,Economic/ClimateFinance/BilateralCommitments
dcid:climateFinanceProvidedLoans,Climate finance committed as loans,dcid:measuredValue,Economic/ClimateFinance/BilateralCommitments
```

```python
manager.add_variables_to_mcf_from_csv(
    "climate_finance_variables.csv",
    parse_groups=True,
    group_namespace="one",
)
```

`parse_groups=True` treats `memberOf` as a slash-separated group path
(`"Economic/ClimateFinance/BilateralCommitments"`) instead of a dcid, and expands it into a chain
of `StatVarGroupMCFNode`s under `group_namespace` (here, `dcid:one/g/economic`, then
`.../climatefinance`, then `.../bilateralcommitments`). Each StatVar's `memberOf` is rewritten to
the deepest group's dcid. Rename CSV columns to node field names with
`column_to_property_mapping` if your headers don't already match.

!!! note
    The groups `parse_groups` generates land in the same `mcf_file_name` as the StatVars
    (`custom_nodes.mcf` by default), not in `add_variable_group_to_mcf`'s default of
    `custom_groups.mcf`. If you export both files, this doesn't matter. If you only export one,
    it does.

The `dcp-tools csv2mcf` CLI command wraps the same conversion for a CSV that isn't going through a
`CustomDataManager` at all. See [CLI tools](cli-tools.md) for the command reference.

## How to rename and remove variables

```python
manager.rename_variable("dcid:climateFinanceProvidedCommitments", "dcid:climateFinanceCommitmentsProvided")
```

Pass the full node id on both sides, matching what's stored (the value after minting, not the bare
name you might have originally passed to `add_variable_to_mcf`). Raises `ValueError` if the old
name isn't found or the new name is already taken. Scope the search to one file with
`mcf_file_name=`. Omit it and all loaded MCF files are searched.

```python
manager.remove_indicator("dcid:climateFinanceCommitmentsProvided")
```

!!! warning "Heads up"
    There's no `remove_variable` method. The real name is `remove_indicator`.

## How to merge config files

Use this when different teams maintain separate `config.json` files for the same custom Data
Commons instance and you need one combined bundle.

```python
from dcp_tools import CustomDataManager

merged = CustomDataManager.from_config_files_in_directory("path/to/configs")
```

This recursively finds every `config.json` under the directory and merges them into one manager,
replacing whatever config the manager already had. To merge into an existing manager instead of
starting fresh, call `merge_configs_from_directory` directly:

```python
manager.merge_configs_from_directory("path/to/configs", replace_loaded_config=False)
```

To merge a single config (an object, a dict, or a path to a JSON file) rather than a whole
directory:

```python
manager.merge_config("path/to/other/config.json")
```

All three take `policy`, one of `"error"` (default, raises on any conflicting value),
`"override"` (the new config wins), or `"ignore"` (the existing value is kept). Input files are
merged by `filename`/`pattern`. Everything else (`importName`, `customIdNamespace`,
`svHierarchyPropsBlocklist`, and so on) is merged field by field.

!!! warning "Heads up"
    `export_config` defaults an unset `importName` to the export directory's name. If two configs
    were each exported without an explicit `importName`, merging them raises a conflict on
    `importName` (`"climate"` vs. `"health"`) even though neither config set it on purpose. Call
    `set_importName` explicitly on configs you intend to merge later.

## How to add vertical specs to guide the StatVar hierarchy

Vertical specs tell the importer which top-level groups to file matching StatVars under when
`groupStatVarsByProperty` is set. Skip this unless you're using that setting.

```python
manager.set_groupStatVarsByProperty(True)
manager.add_vertical_spec(
    verticals=["ClimateFinanceVertical"],
    population_type="Country",
    measured_properties=["amount"],
)
```

Each call appends one spec matching StatVars about `population_type` with the given
`measured_properties` to `verticals`. The first call also sets the config's `verticalSpecsFile` to
`"vertical_specs.json"`, unless you already set one with `set_verticalSpecsFile` or passed
`file_name=` here. `export_all` (or `export_vertical_specs` directly) writes the accumulated specs
as `{"specs": [...]}` JSON. Exporting with no specs added raises `ValueError`.

## How to validate and export the bundle

Validate without writing anything:

```python
manager.validate_config()
```

Raises a pydantic `ValidationError` or `ValueError` if the config is invalid, including if an
input file references a provenance that was never registered.

Export everything in one call:

```python
manager.export_all(
    "output_directory",
    mcf_file_names=["provenance.mcf", "custom_nodes.mcf", "custom_groups.mcf"],
)
```

`export_all` writes `config.json` always, data CSVs if any DataFrames are registered,
`vertical_specs.json` if any specs were added, and each file in `mcf_file_names`. `mcf_file_names`
defaults to `None`, which exports **no MCF file at all**. Omitting it is the most common way to
end up with a `config.json` that references StatVars and provenances nobody wrote to disk.

Before writing anything, `export_all` checks that every provenance an input file references (and
that provenance's linked source) lives in one of the MCF files you're exporting. If not, it raises
rather than shipping an incomplete bundle:

```text
ValueError: export_all() would write a config.json referencing source/provenance node(s)
defined in MCF file(s) not being exported: ['provenance.mcf']. Add them to mcf_file_names
(e.g. mcf_file_names=['provenance.mcf']) so the bundle is complete.
```

Pass `validate_data=True` to also raise if any declared input file has no registered DataFrame
(pattern entries are exempt, since they carry no local data by design):

```python
manager.export_all("output_directory", mcf_file_names=["provenance.mcf"], validate_data=True)
```

To export pieces individually instead of all at once:

- `export_config(dir_path)` writes only `config.json` (and defaults `importName` to the directory
  name if you never set one).
- `export_data(dir_path)` writes the registered DataFrames as CSVs.
- `export_mcf_file(dir_path, mcf_file_name=...)` writes one MCF file.
- `export_vertical_specs(dir_path)` writes the vertical specs file.
- `config_to_dict()` returns the validated config as a dict without writing anything, and without
  defaulting `importName`, since there's no export directory to name it after.

## See also

- [Why config.json and MCF](dc-schemas.md): why column mappings and dcids are shaped the way they
  are.
- [Loading data](loading-data.md): upload the exported bundle to Google Cloud Storage and trigger
  the ingestion job.
- [CLI tools](cli-tools.md): the `dcp-tools csv2mcf` command for CSV-to-MCF conversion outside a
  `CustomDataManager`.
