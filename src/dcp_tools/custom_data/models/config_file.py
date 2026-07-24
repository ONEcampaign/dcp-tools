import os
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.alias_generators import to_camel

from dcp_tools.custom_data.models.data_files import InputFile


class Config(BaseModel):
    """Representation of the config file

    Attributes:
        import_name: Name of the import. Used by the platform prep job to name the
            JSON-LD output directory. Optional; defaults to the export directory name
            on export when unset.
        include_input_subdirs: Include input subdirectories.
        group_stat_vars_by_property: Group stat vars by property.
        default_custom_root_stat_var_group_name: Display name for the custom root StatVarGroup.
            Default: `"Custom Variables"`
        custom_id_namespace: Namespace token for generated ids for SVs and manual groups.
            Default: `"custom"`.
        custom_svg_prefix: String prefix for generated custom StatVarGroup ids. If not set,
            and `customIdNamespace` is provided, it defaults to `<customIdNamespace>/g/`.
        input_files: List of input file entries. Each entry specifies exactly one of
            ``filename`` (exact CSV name) or ``pattern`` (glob), plus ``provenance``
            and column mapping information.
        sv_hierarchy_props_blocklist: Array of additional property dcids to exclude from hierarchy generation.
            These are added to the internal blocklist used by Data Commons.
        data_download_url: Optional list of URLs the importer fetches input data from.
            Serialized as a JSON list; passthrough config value (no fetching/validation here).
        vertical_specs_file: Optional filename of the vertical-specs JSON file the importer reads
            when grouping stat vars. Plain filename string; the file itself is not managed here.
    """

    import_name: str | None = None
    include_input_subdirs: bool | None = None
    group_stat_vars_by_property: bool | None = None
    default_custom_root_stat_var_group_name: str | None = None
    custom_id_namespace: str | None = None
    custom_svg_prefix: str | None = None
    sv_hierarchy_props_blocklist: list[str] | None = None
    data_download_url: list[str] | None = None
    vertical_specs_file: str | None = None
    input_files: list[InputFile]

    # model configuration - populate by name (for the "format" field alias)
    # and forbid extra fields
    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
        serialize_by_alias=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    @model_validator(mode="before")
    @classmethod
    def _reject_legacy_variable_per_column(cls, data: Any) -> Any:
        """Reject legacy 'variablePerColumn' inputFiles with a clear migration error.

        Handles both the legacy dict format and the current list format for ``inputFiles``
        so that the friendly migration message fires before any type-coercion error.
        """
        if isinstance(data, dict):
            input_files = data.get("inputFiles") or {}
            if isinstance(input_files, dict):
                # Legacy dict format — use the dict key in the error message so callers
                # can identify the offending file.
                for key, entry in input_files.items():
                    if isinstance(entry, dict) and "variablePerColumn" in {
                        entry.get("format"),
                        entry.get("data_format"),
                    }:
                        raise ValueError(
                            f"Config contains input file '{key}' in the legacy "
                            "'variablePerColumn' format, which is no longer supported. "
                            "Convert the file to the variable-per-row format (one "
                            "observation per row) with a 'columnMappings' block. See "
                            "https://docs.datacommons.org/custom_dc/custom_data.html"
                        )
            elif isinstance(input_files, list):
                # Current list format — key off filename or pattern for the message.
                for entry in input_files:
                    if isinstance(entry, dict) and "variablePerColumn" in {
                        entry.get("format"),
                        entry.get("data_format"),
                    }:
                        key = (
                            entry.get("filename") or entry.get("pattern") or "<unknown>"
                        )
                        raise ValueError(
                            f"Config contains input file '{key}' in the legacy "
                            "'variablePerColumn' format, which is no longer supported. "
                            "Convert the file to the variable-per-row format (one "
                            "observation per row) with a 'columnMappings' block. See "
                            "https://docs.datacommons.org/custom_dc/custom_data.html"
                        )
        return data

    def validate_config(self) -> None:
        """Validate the config"""
        Config.model_validate(self.model_dump())

    @classmethod
    def from_json(cls, file_path: str | os.PathLike[str]) -> "Config":
        """Read the config from a JSON file

        Args:
            file_path: Path to the JSON file.

        Returns:
            Config: The config object.
        """

        with open(file_path) as f:
            data = f.read()
        return cls.model_validate_json(data)
