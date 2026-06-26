# Data Commons Schemas

Data Commons uses the **explicit schema** to map your data to the knowledge graph. Each CSV file
must include a column mapping that tells the importer which columns represent entities, time
periods, and statistical variable values.

# Explicit schema

With the explicit schema your data must follow the variable-per-row format, where each row
represents a single observation. Each CSV file is registered with a `columnMappings` block that
describes the role of each column.

### Example explicit schema workflow

Here is a simple example of a workflow using the explicit schema.

Let's say we have some data on GDP for different countries that we want to import into Data Commons.
The data comes from the IMF World Economic Outlook, and we have already cleaned and formatted it:

```python
import pandas as pd

df = pd.DataFrame({
    "country": ["USA", "Canada", "Mexico"],
    "year": [2020, 2020, 2020],
    "variable": ["Amount_EconomicActivity_GrossDomesticProduction_Nominal"] * 3,
    "value": [21000000, 1700000, 1200000],
    "unit": ["USDollar"] * 3,
})
```

This DataFrame uses the explicit (variable-per-row) format. The `columnMappings` block will tell
the importer which columns map to entities, dates, variable DCIDs, and observation values.

First, create a `CustomDataManager` instance:

```python
from dcp_tools import CustomDataManager

manager = CustomDataManager()
```

Add the source and provenance:

```python
manager.add_source(
    name="IMF",
    url="https://www.imf.org/en/Home",
)
manager.add_provenance(
    name="WEO",
    url="https://www.imf.org/en/Publications/WEO",
    source="IMF",
)
```

Register the data file with its column mappings:

```python
from dcp_tools.custom_data.models.data_files import ColumnMappings

manager.add_explicit_schema_file(
    file_name="economy/gdp.csv",
    provenance="WEO",
    data=df,
    columnMappings=ColumnMappings(
        entityColumn="country",
        observationDateColumn="year",
        variableColumn="variable",
        observationValueColumn="value",
        observationProperties={"unit": "USDollar"},
    ),
)
```

Export all files:

```python
manager.export_all("output_directory")
```

The `config.json` and the data CSV will be created in `output_directory`.

For more detail on the explicit schema format, see the
[Data Commons custom data documentation](https://docs.datacommons.org/custom_dc/custom_data.html).
