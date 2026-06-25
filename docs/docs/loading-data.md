# Loading data to the knowledge graph

This page walks through the process of loading data into a custom Data Commons knowledge graph. There are three
main steps involved:
- Pushing data files, MCF files and the `config.json` file to Google Cloud Storage.
- Triggering the Data Commons load job.
- Redeploying the custom Data Commons service.

Before starting, specify all the settings to connect to GCP, push data to Google Cloud Storage, 
and trigger the Data Commons load job. 
This can be done using a `.env` file, a `.json` file, or by instantiating a `KGSettings` object directly.
The settings should include the following information:

- `local_path`: Path to the local directory that will be exported.
- `gcp_project_id`: GCP project ID.
- `gcp_credentials`: GCP credentials in JSON format.
- `gcs_bucket_name`: Google Cloud Storage bucket name.
- `gcs_input_folder_path`: Google Cloud Storage input folder path.
- `gcs_output_folder_path`: Google Cloud Storage output folder path.
- `cloud_sql_db_name`: Cloud SQL database name.
- `cloud_sql_region`: Cloud SQL region.
- `cloud_job_region`: Cloud job region.
- `cloud_service_region`: Cloud service region.
- `cloud_run_job_name`: Cloud Run job name.
- `cloud_run_service_name`: Cloud Run service name.

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
from dcp_tools.gcp_utilities import KGSettings

settings = KGSettings(
    local_path="path/to/local/directory",
    gcp_project_id="your-gcp-project-id",
    gcp_credentials="path/to/credentials.json",
    gcs_bucket_name="your-gcs-bucket-name",
    gcs_input_folder_path="input/folder/path",
    gcs_output_folder_path="output/folder/path",
    cloud_sql_db_name="your-cloud-sql-db-name",
    cloud_sql_region="your-cloud-sql-region",
    cloud_job_region="your-cloud-job-region",
    cloud_service_region="your-cloud-service-region",
    cloud_run_job_name="your-cloud-run-job-name",
    cloud_run_service_name="your-cloud-run-service-name"
)
```

## Load data and deploy the custom Data Commons instance

Once you have specified the settings, you can take the next steps to load data into your custom Data 
Commons knowledge graph.

First, you need to upload the directory containing the `config.json` file and any CSV or MCF files to 
Google Cloud Storage.

```python title="Upload to GCS"
from dcp_tools.gcp_utilities import (
    upload_to_cloud_storage,
    run_data_load,
    redeploy_service,
)

upload_to_cloud_storage(settings=settings, directory="path/to/output/folder")
```

Next, we'll run the data load job on Google Cloud Platform.
```python
run_data_load(settings=settings)
```

Last, we need to redeploy the Custom Data Commons instance.

```python
redeploy_service(settings=settings)
```

**Read more about deploying your custom instance to Google Cloud 
[here ↗](https://docs.datacommons.org/custom_dc/deploy_cloud.html)**