# Loading data to the knowledge graph

This page walks through the process of loading data into a custom Data Commons knowledge graph. There are two
main steps involved:
- Pushing data files, MCF files and the `config.json` file to Google Cloud Storage.
- Triggering the Data Commons load job.

Before starting, specify all the settings to connect to GCP, push data to Google Cloud Storage, 
and trigger the Data Commons load job. 
This can be done using a `.env` file, a `.json` file, or by instantiating a `KGSettings` object directly.
The settings should include the following information:

- `LOCAL_PATH`: Path to the local directory that will be exported.
- `GCP_PROJECT_ID`: GCP project ID.
- `GCP_CREDENTIALS`: GCP credentials in JSON format.
- `GCS_BUCKET_NAME`: Google Cloud Storage bucket name.
- `GCS_INPUT_FOLDER_PATH`: Google Cloud Storage input folder path.
- `GCS_OUTPUT_FOLDER_PATH`: Google Cloud Storage output folder path.
- `LOAD_JOB_REGION`: Cloud Run load job region.
- `LOAD_JOB_NAME`: Cloud Run load job name.
- `LOAD_JOB_SERVICE_ACCOUNT`: Cloud Run service account email to impersonate, optional.

create a KGSettings object from a `.env` file, a `.json` file, or directly instantiating an object.

```python title="settings from .env file"
from dcp_tools.gcp_utilities import get_kg_settings

settings = get_kg_settings(source="env", env_file="customDC.env")

```

```python title="settings from .json file"
from dcp_tools.gcp_utilities import get_kg_settings

settings = get_kg_settings(source="json", env_file="customDC.json")

```

```python title="settings from KGSettings object"
from pathlib import Path
from dcp_tools.gcp_utilities import KGSettings

settings = KGSettings(
    LOCAL_PATH=Path("path/to/local/directory"),
    GCP_PROJECT_ID="your-gcp-project-id",
    GCP_CREDENTIALS="path/to/credentials.json",
    GCS_BUCKET_NAME="your-gcs-bucket-name",
    GCS_INPUT_FOLDER_PATH="input/folder/path",
    GCS_OUTPUT_FOLDER_PATH="output/folder/path",
    LOAD_JOB_REGION="your-load-job-region",
    LOAD_JOB_NAME="your-load-job-name",
    LOAD_JOB_SERVICE_ACCOUNT="your-service-account-email"
)
```

## Load data into the custom Data Commons instance

Once you have specified the settings, you can take the next steps to load data into your custom Data 
Commons knowledge graph.

First, you need to upload the directory containing the `config.json` file and any CSV or MCF files to 
Google Cloud Storage.

```python title="Upload to GCS"
from dcp_tools.gcp_utilities import (
    upload_to_cloud_storage,
    run_data_load
)

upload_to_cloud_storage(settings=settings, directory="path/to/output/folder")
```

Next, we'll run the data load job on Google Cloud Platform.
```python
# Load all data
run_data_load(settings=settings)

# Load specific imports
run_data_load(settings=settings, imports="import_a,import_b")
```

**Read more about deploying your custom instance to Google Cloud 
[here ↗](https://docs.datacommons.org/custom_dc/deploy_cloud.html)**