# Getting started with `bblocks-datacommons-tools`

This page walks you through the basic steps to install and start using 
`bblocks-datacommonst-tools` to prepare and load the data for your custom instance.

## About custom Data Commons instances

Anyone can build and manage their own Data Commons instance—combining their own datasets with the base
data available from datacommons.org, and taking advantage of built-in features like natural language queries, 
interactive visualisations, and data exploration tools. For many organisations, a custom instance is a practical 
way to publish data with exploration and visualisation tools without building infrastructure from scratch.

However, preparing your data for a Data Commons knowledge graph, uploading the necessary files to Google 
Cloud Platform (GCP), and deploying the service can be a repetitive and error-prone process.
For smaller projects with limited data and infrequent updates, managing the workflow manually may be
sufficient. But for larger datasets or pipelines with regular refreshes, the process quickly 
becomes tedious and difficult to maintain.

`bblocks-datacommons-tools` streamlines this workflow by allowing you to programmatically prepare and load data using
a Python-based pipeline.

Before you get started, you should have a basic understanding of how custom Data Commons instances work and 
what the data loading process involves. You can find the
[official documentation here](docs.datacommons.org/custom_dc/custom_data.html).

At a top level, you should be familiar with:

- **The `config.json` file**: the 
[JSON configuration](https://docs.datacommons.org/custom_dc/custom_data.html#step-2-write-the-json-config-file) 
file that specifies how to map and resolve data to the
Data Commons schema knowledge graph.
- **The data files**: CSV files containing the data formatted for the
[explicit schema](https://docs.datacommons.org/custom_dc/custom_data.html#explicit).
- **Meta Content Framework 
([MCF](https://docs.datacommons.org/custom_dc/custom_data.html#step-1-define-statistical-variables-in-mcf)) files**: files that provide additional flexibility form modeling data for the knowledge
graph.
- **Uploading data and deploying**: Files need to be loaded to GCP, and the service needs to be 
[deployed](https://docs.datacommons.org/custom_dc/deploy_cloud.html).


## Installation

The package can be installed in various ways. 

Directly as
```bash
pip install bblocks-datacommons-tools
```

Or from the main `bblocks` package with an extra:

```bash
pip install "bblocks[datacommons-tools]"
```

## Preparing data

`bblocks-datacommons-tools` offers convenient functionality to prepare configuration JSON, MCF, and custom data files
without having to manually edit these files. To access this functionality, create an instance of the 
`CustomDataManager` class.

```python
from bblocks.datacommons_tools import CustomDataManager

manager = CustomDataManager()
```

The `CustomDataManager` lets you create or edit the `config.json` file without editing it manually. 

You can register variables, sources or provenances, and data files. 

```python title="Add provenance and source"
manager.add_provenance(
    provenance_name="ONE Climate Finance",
    provenance_url="https://datacommons.one.org/data/climate-finance-files",
    source_name="ONE Data",
    source_url="https://data.one.org",
)
```

You can pass pandas DataFrames to the manager and the manager will handle exporting the data as
CSVs in the correct format.

```python title="Add explicit schema data"
import pandas as pd
from bblocks.datacommons_tools.custom_data.models.data_files import ColumnMappings

df = pd.DataFrame(...)

manager.add_explicit_schema_file(
    file_name="climate_finance/one_cf_provider_commitments.csv",
    provenance="ONE Climate Finance",
    data=df,
    columnMappings=ColumnMappings(
        entity="country",
        date="year",
        variable="variable",
        value="value",
    ),
)
```


Once you are finished adding and editing data and configuration, you can 
validate and export all the files for your custom Data Commons instance.

```python
manager.export_all("path/to/output/folder")
```

**Read more detailed documentation about preparing data with the `CustomDataManager` 
[here ↗](./preparing-data.md)**

## Loading data

You can programmatically push the data and config to a Google Cloud
Storage Bucket, trigger the data load job, and redeploy your Data Commons
instance.

First, specify all the configuration settings needed to add files to the storage bucket. For convenience these
can be specified in a `.env` file (read more about the configuration settings [here](./loading-data.md)).


```python
from bblocks.datacommons_tools.gcp_utilities import get_kg_settings

settings = get_kg_settings(source="env", env_file="customDC.env")
```


Now we can load data and configuration files to the storage bucket, run the data load job on GCP,
and redeploy the custom Data Commons instance.

```python
from bblocks.datacommons_tools.gcp_utilities import (
    upload_to_cloud_storage,
    run_data_load,
    redeploy_service,
)

upload_to_cloud_storage(settings=settings, directory="path/to/folder/with/data_and_config")
run_data_load(settings=settings)
redeploy_service(settings=settings)

```
