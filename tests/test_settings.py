import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from dcp_tools.gcp_utilities.settings import KGSettings, get_kg_settings

RAW_SCREAMING = {
    "LOCAL_PATH": "/tmp/data",
    "GCP_PROJECT_ID": "proj",
    "GCS_BUCKET_NAME": "bucket",
    "GCS_INPUT_FOLDER_PATH": "ingestion/input/",
    "GCS_OUTPUT_FOLDER_PATH": "/output/path/",
    "LOAD_JOB_NAME": "job",
    "INGESTION_WORKFLOW_NAME": "workflow",
    "LOAD_JOB_REGION": "us-central1",
    "LOAD_JOB_SERVICE_ACCOUNT": "test@example.com",
}

RAW_SNAKE = {
    "local_path": "/tmp/data",
    "gcp_project_id": "proj",
    "gcs_bucket_name": "bucket",
    "gcs_input_folder_path": "ingestion/input/",
    "gcs_output_folder_path": "/output/path/",
    "load_job_name": "job",
    "ingestion_workflow_name": "workflow",
    "load_job_region": "us-central1",
    "load_job_service_account": "test@example.com",
}


def test_model_dump_round_trips_to_field_names() -> None:
    """model_dump() must return snake_case field names callers expect, not aliases."""
    settings = KGSettings(**RAW_SCREAMING)

    dumped = settings.model_dump()

    assert dumped["local_path"] == Path("/tmp/data")
    assert dumped["gcp_project_id"] == "proj"
    assert dumped["gcs_input_folder_path"] == "ingestion/input"
    assert "LOCAL_PATH" not in dumped
    assert "GCP_PROJECT_ID" not in dumped

    # Round-trip: dumping and reloading by field name must reproduce the settings.
    reloaded = KGSettings(**dumped)
    assert reloaded == settings


def test_constructor_accepts_snake_case_field_names() -> None:
    """populate_by_name=True lets callers construct KGSettings with field names."""
    settings = KGSettings(**RAW_SNAKE)

    assert settings.local_path == Path("/tmp/data")
    assert settings.gcp_project_id == "proj"
    assert settings.gcs_input_folder_path == "ingestion/input"


def test_constructor_still_accepts_screaming_snake_aliases() -> None:
    """Backwards compatibility: the historic SCREAMING_SNAKE keys still work."""
    settings = KGSettings(**RAW_SCREAMING)

    assert settings.local_path == Path("/tmp/data")
    assert settings.load_job_service_account == "test@example.com"


def test_json_source_loads_screaming_snake_config(tmp_path: Path) -> None:
    """The documented JSON config convention (SCREAMING_SNAKE keys) keeps working."""
    config_file = tmp_path / "settings.json"
    config_file.write_text(json.dumps(RAW_SCREAMING))

    settings = get_kg_settings(source="json", file=config_file)

    assert settings.local_path == Path("/tmp/data")
    assert settings.gcs_input_folder_path == "ingestion/input"


def test_json_source_loads_snake_case_config(tmp_path: Path) -> None:
    """A JSON config using field names (snake_case) must also populate correctly."""
    config_file = tmp_path / "settings.json"
    config_file.write_text(json.dumps(RAW_SNAKE))

    settings = get_kg_settings(source="json", file=config_file)

    assert settings.local_path == Path("/tmp/data")
    assert settings.gcp_project_id == "proj"
    assert settings.gcs_input_folder_path == "ingestion/input"


def test_json_source_rejects_unknown_keys(tmp_path: Path) -> None:
    """A mismatched/typo'd key must fail loudly, not silently drop the field."""
    raw = dict(RAW_SCREAMING)
    del raw["GCS_INPUT_FOLDER_PATH"]
    raw["GCS_INPUT_FOLDER_PATHH"] = "typo/oops"
    config_file = tmp_path / "settings.json"
    config_file.write_text(json.dumps(raw))

    with pytest.raises(ValidationError):
        get_kg_settings(source="json", file=config_file)


def test_gcs_input_folder_path_defaults_to_ingestion_input() -> None:
    """A standard DCP Terraform deployment shouldn't need to set this explicitly."""
    raw = dict(RAW_SCREAMING)
    del raw["GCS_INPUT_FOLDER_PATH"]

    settings = KGSettings(**raw)

    assert settings.gcs_input_folder_path == "ingestion/input"


def test_env_source_still_accepts_screaming_snake(monkeypatch) -> None:
    """Backwards compatibility: env vars keep using the SCREAMING_SNAKE convention."""
    for key, value in RAW_SCREAMING.items():
        monkeypatch.setenv(key, value)

    settings = get_kg_settings(source="env")

    assert settings.local_path == Path("/tmp/data")
    assert settings.gcs_input_folder_path == "ingestion/input"
