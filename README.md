# dcp-tools

__Manage and load data to custom Data Commons instances__

[![PyPI](https://img.shields.io/pypi/v/dcp-tools.svg)](https://pypi.org/project/dcp-tools/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/dcp-tools.svg)](https://pypi.org/project/dcp-tools/)
[![Docs](https://img.shields.io/badge/docs-bblocks-blue)](https://docs.one.org/tools/bblocks/datacommons-tools/)
[![Lint/format: Ruff](https://img.shields.io/badge/lint%2Fformat-ruff-46a758.svg)](https://github.com/astral-sh/ruff)

Custom [Data Commons](https://docs.datacommons.org/custom_dc/custom_data.html) requires that you provide your data in a specific schema, format, and file structure.

At a high level, you need to provide the following:

- All observations data must be in CSV format, using a predefined schema.
- You must also provide a JSON configuration file, named `config.json`, that specifies how to map and resolve the CSV contents to the Data Commons schema knowledge graph.
- Depending on how you define your statistical variables (metrics), you may need to provide MCF (Meta Content Framework) files.
- You may also need to define new custom entities.

Managing this workflow by hand is tedious and easy to get wrong.

The `dcp_tools` package streamlines that process. It provides a Python API and command line utilities for building config files, generating MCF from CSV metadata and running the data load pipeline on Google Cloud. 

Use this package when you want to:

- Manage `config.json` files programmatically.
- Define statistical variables, entities or groups using MCF files.
- Programmatically upload CSVs, MCF files, and the `config.json` file to Cloud Storage, trigger the load job and redeploy your custom Data Commons service with code.

In short, `dcp-tools` removes much of the manual work involved in setting up and maintaining a custom Data Commons Knowledge Graph.

Read the [documentation](https://docs.one.org/tools/bblocks/datacommons-tools/)
for more details on how to use the package and the motivation for its creation.


## Installation

The package can be installed in various ways. 

Directly as
```bash
pip install dcp-tools
```

It can also be installed from GitHub:
```bash
pip install git+https://github.com/ONEcampaign/bblocks-datacommons-tools
```

## Sample Usage

Here's a simple example covering how to use the "implicit" Data Commons
schema to load a single dataset. Please see the full [documentation page](https://docs.one.org/tools/bblocks/datacommons-tools/) for a thorough 
introduction to the package, and to learn how to use it.


### 1. Create a CustomDataManager object. 

The CustomDataManager object will handle generating the `config.json` file, as well as (optionally) taking Pandas DataFrames and exporting them as CSVs (in the right format) for loading to the Knowlede Graph.

In this example, we assume a `config.json` does not yet exist.

```python title="Instantiate the CustomDataManager class"
from dcp_tools import CustomDataManager

# Create the object and call it "manager"
manager = CustomDataManager()

# Configure it to include subdirectories
manager.set_includeInputSubdirs(True)

```

### 2. Add the provenance information for our data
You can add or manage provenance information using `add_source` and `add_provenance`.

In this example, we will add a source and provenance for ONE Data's Climate Finance Files.

```python title="Add source and provenance"
manager.add_source(name="ONE Data", url="https://data.one.org")
manager.add_provenance(
    name="ONE Climate Finance",
    url="https://datacommons.one.org/data/climate-finance-files",
    source="ONE Data",
)
```

### 3. Add the data to the CustomDataManager object.
Next, you need to specify your data on the `config.json` file. 

Adding actual data data to the `CustomDataManager` is an optional step. 

For this example, we will assume a DataFrame is available via the
`data` variable.

To add to the `CustomDataManager`, using the Implicit Schema:

```python title="Register data"
manager.add_implicit_schema_file(
    file_name="climate_finance/one_cf_provider_commitments.csv",
    provenance="ONE Climate Finance",
    entityType="Country",
    data=data,
    ignoreColumns=["oecd_provider_code"],
    observationProperties={"unit": "USDollar"},
)
```

Adding the data in the step above is optional. You can also create the inputFile in the config and add the data tied to that inputFile at a later stage by running:

```python
manager.add_data(data=data, file_name='one_cf_provider_commitments.csv')
```

Or you can manually add the relevant CSV file (matching what you declared as `file_name`).

### 4. Add the indicators to config
Next, you need to specify information about the StatVars (variables) contained
in your data file(s).

When using the Implicit Schema, you can specify additional information.

For convenience, you could loop through a dictionary of indicators and information. For this example we'll add a single indicator.

```python title="Register an indicator"
manager.add_variable_to_config(
    statVar="climateFinanceProvidedCommitments",
    name="Climate Finance Commitments (bilateral)",
    group="ONE/Environment/Climate finance/Provider perspective/Commitments",
    description="Funding for climate adaptation and mitigation projects",
    searchDescriptions=[
        "Climate finance commitments provided",
        "Adaptation and mitigation finance provided",
    ],
    properties={"measurementMethod": "Commitment"},
    )
 ```

### 5. Export the `config.json` and (optionally) data CSVs

Next, once all the data is added and the config is set up, you can export the `config.json` and data. When you export, the `config.json` is validated automatically

```python title="Export config and data"
manager.export_all("path/to/output/folder", mcf_file_names=["provenance.mcf"])
```

`export_all` writes a complete bundle: if an input file references a provenance,
the MCF file defining it (`provenance.mcf` by default) must be listed in
`mcf_file_names`, or it raises before writing anything.

### 6. (Optionally) load to the Knowledge Graph
You can also programmatically push the data and config to a Google Cloud
Storage Bucket, trigger the data load job, and redeploy your Data Commons
instance.

To do this, you'll need to load information about your
project, Storage Bucket, etc. You can use `.env` or `.json` files,
or simply make the right information available as environment variables.
A detailed description of the needed information, can be found in the documentation.

#### Load the settings
First, load the settings using `get_kg_settings`. In this example, we will load them from a `.env` file available in our working directory.

```python  title="Load settings"
from dcp_tools.gcp_utilities import (
    upload_to_cloud_storage,
    run_data_load,
    redeploy_service,
    get_kg_settings,
)

settings = get_kg_settings(source="env", env_file="customDC.env")
```
Second, we'll upload the directory which contains the `config.json` file and
any CSV and/or MCF files.

```python title="Upload to GCS"
upload_to_cloud_storage(settings=settings, directory="path/to/output/folder")
```

Third, we'll run the data load job on Google Cloud Platform.
```python
run_data_load(settings=settings)
```

Last, we need to redeploy the Custom Data Commons instance.

```python
redeploy_service(settings=settings)
```

---

Visit the [documentation page](https://docs.one.org/tools/bblocks/datacommons-tools/) for the full package documentation and examples.

## Contributing
Contributions are welcome! Please see the
[CONTRIBUTING](https://github.com/ONEcampaign/bblocks-datacommons-tools/blob/main/CONTRIBUTING.md) 
page for details on how to get started, report bugs, fix issues, and submit enhancements.
