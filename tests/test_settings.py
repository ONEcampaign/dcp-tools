import json
import warnings
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from dcp_tools.gcp_utilities.pipeline import upload_to_cloud_storage
from dcp_tools.gcp_utilities.settings import KGSettings, get_kg_settings

RAW_SCREAMING: dict[str, Any] = {
    "LOCAL_PATH": "/tmp/data",
    "GCP_PROJECT_ID": "proj",
    "GCP_REGION": "us-central1",
    "GCS_BUCKET_NAME": "bucket",
    "GCS_INPUT_FOLDER_PATH": "ingestion/input/",
    "GCS_OUTPUT_FOLDER_PATH": "/output/path/",
    "INGESTION_WORKFLOW_NAME": "workflow",
    "INGESTION_SERVICE_ACCOUNT": "test@example.com",
}

OPTIONAL_KEYS = {
    "LOCAL_PATH",
    "GCP_CREDENTIALS",
    "GCS_INPUT_FOLDER_PATH",
    "GCS_OUTPUT_FOLDER_PATH",
    "INGESTION_SERVICE_ACCOUNT",
}

RAW_REQUIRED = {k: v for k, v in RAW_SCREAMING.items() if k not in OPTIONAL_KEYS}

RAW_SNAKE: dict[str, Any] = {
    "local_path": "/tmp/data",
    "gcp_project_id": "proj",
    "gcp_region": "us-central1",
    "gcs_bucket_name": "bucket",
    "gcs_input_folder_path": "ingestion/input/",
    "gcs_output_folder_path": "/output/path/",
    "ingestion_workflow_name": "workflow",
    "ingestion_service_account": "test@example.com",
}


@pytest.fixture(autouse=True)
def isolated_settings_sources(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep the developer's environment and any ./.env out of KGSettings."""
    monkeypatch.chdir(tmp_path)
    for field in KGSettings.model_fields.values():
        assert isinstance(field.validation_alias, str)
        monkeypatch.delenv(field.validation_alias, raising=False)


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
    assert settings.ingestion_service_account == "test@example.com"


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


@pytest.mark.parametrize("key", ["INGESTION_PREP_JOB_NAME", "ingestion_prep_job_name"])
def test_prep_job_name_is_deprecated(key: str) -> None:
    """The ingestion workflow creates its own preprocessing job on DCP 1.1.6."""
    with pytest.warns(FutureWarning) as record:
        settings = KGSettings(**RAW_SCREAMING, **{key: "prep-job"})

    assert settings.ingestion_prep_job_name == "prep-job"
    assert [w.filename for w in record] == [__file__]


def test_prep_job_name_env_var_is_deprecated(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in RAW_SCREAMING.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("INGESTION_PREP_JOB_NAME", "prep-job")

    with pytest.warns(FutureWarning) as record:
        settings = get_kg_settings(source="env")

    assert settings.ingestion_prep_job_name == "prep-job"
    assert [w.filename for w in record] == [__file__]


def test_settings_without_prep_job_name_do_not_warn() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        settings = KGSettings(**RAW_SCREAMING)

    assert settings.ingestion_prep_job_name is None


@pytest.fixture
def isolated_env(monkeypatch, tmp_path: Path) -> Path:
    """Clear KG variables from the environment and run away from any real .env."""
    for key in RAW_SCREAMING.keys() | OPTIONAL_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_env_file_ignores_unrelated_variables(isolated_env: Path) -> None:
    """A .env shared with other tools must load, ignoring lines KGSettings doesn't own."""
    env_file = isolated_env / ".env"
    lines = [f"{k}={v}" for k, v in RAW_REQUIRED.items()]
    env_file.write_text("\n".join([*lines, "DUCKDB_PATH=warehouse.duckdb"]))

    settings = get_kg_settings(env_file=env_file)

    assert settings.gcp_project_id == "proj"
    assert not hasattr(settings, "duckdb_path")


def test_optional_paths_default_to_none(isolated_env: Path) -> None:
    """LOCAL_PATH and GCS_OUTPUT_FOLDER_PATH aren't needed to validate."""
    settings = KGSettings(**RAW_REQUIRED)

    assert settings.local_path is None
    assert settings.gcs_output_folder_path is None


def test_full_gcs_output_path_names_missing_setting(isolated_env: Path) -> None:
    settings = KGSettings(**RAW_REQUIRED)

    with pytest.raises(ValueError, match="GCS_OUTPUT_FOLDER_PATH"):
        _ = settings.full_gcs_output_path


def test_upload_without_directory_or_local_path_names_missing_setting(
    isolated_env: Path,
) -> None:
    settings = KGSettings(**RAW_REQUIRED)

    with (
        patch("dcp_tools.gcp_utilities.pipeline.get_gcs_client") as client,
        pytest.raises(ValueError, match="LOCAL_PATH"),
    ):
        upload_to_cloud_storage(settings)
    client.assert_not_called()


def test_upload_with_directory_needs_no_local_path(isolated_env: Path) -> None:
    settings = KGSettings(**RAW_REQUIRED)

    with (
        patch("dcp_tools.gcp_utilities.pipeline.get_gcs_client"),
        patch("dcp_tools.gcp_utilities.pipeline.upload_directory_to_gcs") as upload,
    ):
        upload_to_cloud_storage(settings, directory=isolated_env)

    assert upload.call_args.kwargs["directory"] == isolated_env
