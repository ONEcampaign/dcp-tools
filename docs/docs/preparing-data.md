# Preparing data for Data Commons

`dcp-tools` offers convenient functionality to prepare configuration JSON, 
MCF, and custom data files without having to manually edit these files. The `CustomDataManager`
lets you create or edit an existing `config.json` file, work with MCF files, export data stored as pandas
DataFrames in correct CSV formats, and validate all the files ensuring they are correctly structured for
Data Commons.

## Creating a `CustomDataManager`

To start preparing your data, create a `CustomDataManager` instance.

```python
from dcp_tools import CustomDataManager

manager = CustomDataManager()
```

This will create a custom data manager without a blank `config.json` and no MCF files, which you can use if you are
building the files from scratch. If you already have a `config.json` or any MCF files you can specify them at
instantiation.

```python
manager = CustomDataManager(config_file="path/to/config.json", mcf_file="path/to/mcf_file.mcf")
```

You might store several config files in subdirectories. You can create a `CustomDataManager` instance specifying 
the directory containing the `config.json` files which will be merged into a single `config.json` file.

```python
manager = CustomDataManager.from_config_files_in_directory("path/to/directory")
```

## Managing provenances and sources

The `CustomDataManager` allows you to define the sources and provenances for your data. Sources and
provenances are written as MCF `Source` and `Provenance` nodes — by default into a file called
`provenance.mcf`. Each input file references a provenance by name; internally that reference is stored
as `dcid:provenance/<name>`.

Add a source first, then add one or more provenances that point to it:

```python
manager.add_source(name="SourceName", url="https://example.com/source")
manager.add_provenance(
    name="ProvenanceName",
    url="https://example.com/provenance",
    source="SourceName",
)
```

Each `name` becomes part of a dcid (`dcid:source/<name>`, `dcid:provenance/<name>`), so it must be a
valid dcid token — no whitespace (use `"ONEData"`, not `"ONE Data"`). A name containing whitespace
raises a `ValueError`.

`add_provenance` requires the named source to already exist (added via `add_source`). If a source or
provenance with the same name already exists, a `ValueError` is raised unless you pass `override=True`.

Both methods accept optional metadata kwargs (`description`, `license`, `isPartOf` on both; additionally
`licenseType`, `lastDataRefreshDate`, `nextDataRefreshDate`, `nextSourceReleaseDate`,
`sourceReleaseFrequency`, `earliestObservationDate`, `latestObservationDate`, and `curator` on
`add_provenance`). Use the `additional_properties` dict for any property not covered by those kwargs.

Source and Provenance nodes live in `provenance.mcf` by default. To write that file to disk you must list
it explicitly when exporting:

```python
manager.export_all("path/to/output/folder", mcf_file_names=["provenance.mcf"])
```

This is the same mechanism used for any other MCF file — `provenance.mcf` is not exported automatically.


## Managing variables

The `CustomDataManager` lets you add variables to MCF files for the explicit schema. Read more
about the explicit schema [here](dc-schemas.md).

You can rename variables using the `rename_variable` method, optionally specifying the MCF file.


```python
manager.rename_variable("ghed_che", "ghed_current_health_expenditure",
                        mcf_file="path/to/mcf_file.mcf")
```

You can also remove variables from the `config.json` or MCF files using the `remove_variable` method.

```python
manager.remove_variable("ghed_che", mcf_file="path/to/mcf_file.mcf")
```

## Managing the data files

The `CustomDataManager` allows you to manage the data files you want to import into Data Commons. 
**Note:** This doesn't mean formatting or transforming the data, but rather managing the files that will be used
to import the data into Data Commons and registering them according to the schema you are using. 

The `CustomDataManager` provides support for working with pandas DataFrames, allowing you to register
data stored in a DataFrame to the manager which will export the data to a CSV file in the correct format
for Data Commons.

To register a data file, use the `add_explicit_schema_file` method:

```python
import pandas as pd
from dcp_tools.custom_data.models.data_files import ColumnMappings

df = pd.DataFrame({
    "country": ["USA", "Canada", "Mexico"],
    "year": [2020, 2020, 2020],
    "variable": ["Amount_EconomicActivity_GrossDomesticProduction_Nominal"] * 3,
    "value": [21000000, 1700000, 1200000],
})

manager.add_explicit_schema_file(
    file_name="gdp.csv",
    provenance="IMF",
    data=df,
    columnMappings=ColumnMappings(
        entity="country",
        date="year",
        variable="variable",
        value="value",
    ),
)
```

Adding data when registering a data file is optional. You can also add the data later using the `add_data` method:

```python
manager.add_data(data=df, file_name="gdp.csv")
```

## Removing variables and data files

You can remove variables and data files using the `remove_indicator` and `rename_variable` methods.


## Adding and merging config files

[//]: # (<---TODO: adding and merging config files here --->)





## Additional settings

There are some additional settings you can configure in the `CustomDataManager`:

```python
manager.set_includeInputSubdirs(True)  # Include input subdirectories in the config.json
```

This method will add the `includeInputSubdirs` field to the `config.json` file, which allows you
to place data files in subdirectories inside the main output directory. This is useful for organizing your data files
and keeping them structured. By default, this is not set and the Data Commons importer will expect all data files
to be in the main output directory. If this is set to `True`, You can specify the subdirectory when adding a data file:

```python
manager.add_explicit_schema_file(
    file_name="economics/gdp.csv",
    provenance="IMF",
    columnMappings=ColumnMappings(
        entity="country",
        date="year",
        variable="variable",
        value="value",
    ),
)
```

You can also set the `groupStatVarsByProperty` field in the `config.json` file, 
which allows you to group statistical variables by their properties. 

```python
manager.set_groupStatVarsByProperty(True)
```

You can control the generated StatVar and StatVarGroup identifiers in the `config.json` file.


```python
manager.set_customIdNamespace("ONE")
manager.set_customSvgPrefix("ONE/g/")  # Optional – overrides the default of "geo/g/"
manager.set_defaultCustomRootStatVarGroupName("ONE Data")
```

Finally, you can update the hierarchy blocklist used when generating StatVar groups
from the config. Any duplicates you provide are ignored automatically:

```python
manager.set_svHierarchyPropsBlocklist([
    "WhoCode",
    "aggregationDimensions",
])
```



## Validating and exporting files

To ensure that your `config.json` is correctly structured, you can validate it using the `validate_config` method:

```python
manager.validate_config()
```

The config is automatically validated when you export it. You can export the `config.json` file to disk
or get the config as a dictionary.

```python title="Export config to disk"
manager.export_config("path/to/output/config.json")
```

```python title="Get config as dictionary"
config_dict = manager.config_to_dict()
```

Additionally, you can export the data or MCF files to disk.

```python title="Export data files"
manager.export_data("path/to/output/folder")
```

```python title="Export MCF files"
manager.export_mfc_file("path/to/output/folder")
```

To export all files at once, you can use the `export_all` method:

```python
manager.export_all("path/to/output/folder")
```
**Note**: By default this will export the `config.json` and all data files. MCF files are not exported by default.
To export MCF files as well, you should specify the `mcf_file_names` parameter:

```python
manager.export_all("path/to/output/folder", mcf_file_names=["mcf_file1.mcf", "mcf_file2.mcf"])
```

If an input file references a provenance, the MCF file defining it (`provenance.mcf` by default)
must be among `mcf_file_names`; otherwise `export_all` raises before writing anything, so the
exported bundle can never reference a provenance node that is missing from disk.
