# dcp-tools

__Manage and load data to Data Commons Platform instances__

[![PyPI](https://img.shields.io/pypi/v/dcp-tools.svg)](https://pypi.org/project/dcp-tools/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/dcp-tools.svg)](https://pypi.org/project/dcp-tools/)
[![Docs](https://img.shields.io/badge/docs-dcp--tools-blue)](https://docs.one.org/tools/dcp-tools/)
[![Lint/format: Ruff](https://img.shields.io/badge/lint%2Fformat-ruff-46a758.svg)](https://github.com/astral-sh/ruff)

A [Data Commons Platform](https://docs.datacommons.org/custom_dc/custom_data.html) instance takes
your data as CSVs in a fixed variable-per-row shape, plus a `config.json` that maps each CSV's
columns onto the Data Commons schema. If you're defining your own statistical variables,
entities, or properties rather than reusing existing ones, you also need MCF (Meta Content
Framework) files describing them. `dcp-tools` builds and validates that bundle in Python (or from
the CLI) and uploads it to Cloud Storage to trigger the platform's ingestion job.

This package was published as `bblocks-datacommons-tools` until version 0.1.1, and imported as
`bblocks.datacommons_tools`. Installing the old distribution now pulls in `dcp-tools` and
redirects those imports with a `DeprecationWarning`, so existing code keeps working. Update
imports to `dcp_tools` when convenient.

## Install

```bash
pip install dcp-tools
```

While `1.0.0` is still in alpha, this is a pre-release, so pip won't find it
unless you ask for pre-releases explicitly: `pip install --pre dcp-tools`.

Or from GitHub:

```bash
pip install git+https://github.com/ONEcampaign/dcp-tools
```

## Quickstart

This builds a config and MCF for a source, a provenance, one input file, and one statistical
variable, then exports the bundle to disk.

```python
from pathlib import Path

import pandas as pd
from dcp_tools import CustomDataManager

manager = CustomDataManager()
manager.add_source(name="ONEData", url="https://data.one.org")
manager.add_provenance(
    name="ONEClimateFinance",
    url="https://datacommons.one.org/data/climate-finance-files",
    source="ONEData",
)

data = pd.DataFrame({
    "country": ["Kenya", "Kenya", "Vietnam"],
    "year": [2022, 2023, 2023],
    "variable": ["climateFinanceProvidedCommitments"] * 3,
    "value": [12.4, 15.1, 8.7],
})
manager.add_input_file(
    file_name="climate_finance/one_cf_provider_commitments.csv",
    provenance="ONEClimateFinance",
    data=data,
    columnMappings={
        "observationAbout": "country",
        "date": "year",
        "variable": "variable",
        "value": "value",
    },
    observationProperties={"unit": "USDollar"},
)

manager.add_variable_to_mcf(
    Node="climateFinanceProvidedCommitments",
    name="Climate finance commitments (bilateral)",
    description="Funding committed for climate adaptation and mitigation projects",
    statType="dcid:measuredValue",
)

out_dir = Path("export/climate_finance")
out_dir.mkdir(parents=True, exist_ok=True)
manager.export_all(out_dir, mcf_file_names=["provenance.mcf", "custom_nodes.mcf"])
```

`export_all` writes `config.json`, the CSV, and both named MCF files under `out_dir`. Since we
never called `set_importName`, `config.json` defaults `importName` to the export directory's
name, and column mappings and the provenance name are resolved to full dcids:

```json
{
    "importName": "climate_finance",
    "inputFiles": [
        {
            "filename": "climate_finance/one_cf_provider_commitments.csv",
            "provenance": "dcid:provenance/ONEClimateFinance",
            "columnMappings": {
                "dcid:variableMeasured": "variable",
                "dcid:observationDate": "year",
                "dcid:value": "value",
                "dcid:observationAbout": "country"
            },
            "observationProperties": {"unit": "USDollar"},
            "format": "variablePerRow"
        }
    ]
}
```

!!! warning "Heads up"
    `provenance.mcf` (source and provenance nodes) is never exported by default. If an input
    file references a provenance and its MCF file isn't in `mcf_file_names`, `export_all` raises
    before writing anything, so you can't ship a bundle with a dangling reference.

## Loading it

Once you have a bundle on disk, `dcp_tools.gcp_utilities` uploads it and triggers the load:

```python
from dcp_tools.gcp_utilities import get_kg_settings, upload_to_cloud_storage, run_data_load

settings = get_kg_settings(source="env", env_file="customDC.env")
upload_to_cloud_storage(settings=settings, directory="export/climate_finance")
run_data_load(settings=settings)
```

`run_data_load` triggers the DCP (Data Commons Platform) ingestion job, which ingests the new
data and serves it. There's no separate redeploy step to run. See the
[loading-data docs](https://docs.one.org/tools/dcp-tools/loading-data/) for the
full settings reference, and the `dcp-tools` CLI (`upload`, `dataload`, `pipeline`), which wraps
this same flow.

## Contributing

Contributions are welcome! See [CONTRIBUTING](https://github.com/ONEcampaign/dcp-tools/blob/main/CONTRIBUTING.MD)
for how to get started, report bugs, and submit changes.
