from os import PathLike
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from dcp_tools.custom_data.models.data_files import ExplicitSchemaFile
from dcp_tools.custom_data.models.sources import Source


class Config(BaseModel):
    """Representation of the config file

    Attributes:
        importName: Name of the import. Used by the platform prep job to name the
            JSON-LD output directory. Optional; defaults to the export directory name
            on export when unset.
        includeInputSubdirs: Include input subdirectories.
        groupStatVarsByProperty: Group stat vars by property.
        defaultCustomRootStatVarGroupName: Display name for the custom root StatVarGroup.
            Default: `"Custom Variables"`
        customIdNamespace: Namespace token for generated ids for SVs and manual groups.
            Default: `"custom"`.
        customSvgPrefix: String prefix for generated custom StatVarGroup ids. If not set,
            and `customIdNamespace` is provided, it defaults to `<customIdNamespace>/g/`.
        inputFiles: Dictionary of input files.
        svHierarchyPropsBlocklist: Array of additional property dcids to exclude from hierarchy generation.
            These are added to the internal blocklist used by Data Commons.
        sources: Dictionary of sources.
    """

    importName: str | None = None
    includeInputSubdirs: bool | None = None
    groupStatVarsByProperty: bool | None = None
    defaultCustomRootStatVarGroupName: str | None = None
    customIdNamespace: str | None = None
    customSvgPrefix: str | None = None
    svHierarchyPropsBlocklist: list[str] | None = None
    inputFiles: dict[str, ExplicitSchemaFile]
    sources: dict[str, Source]

    # model configuration - populate by name (for the "format" field alias)
    # and forbid extra fields
    model_config = ConfigDict(
        populate_by_name=True,
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    @model_validator(mode="before")
    @classmethod
    def _reject_implicit_schema_files(cls, data: Any) -> Any:
        """Reject legacy implicit-schema (variablePerColumn) inputFiles with a clear error."""
        if isinstance(data, dict):
            for key, entry in (data.get("inputFiles") or {}).items():
                if isinstance(entry, dict) and "variablePerColumn" in {
                    entry.get("format"),
                    entry.get("data_format"),
                }:
                    raise ValueError(
                        f"Config contains implicit-schema file '{key}': "
                        "format 'variablePerColumn' is no longer supported. "
                        "Migrate to explicit schema before loading. See "
                        "https://docs.datacommons.org/custom_dc/custom_data.html "
                        "for the explicit-schema format."
                    )
        return data

    @model_validator(mode="after")
    def validate_input_file_keys_are_csv(self) -> "Config":
        """Validate that all input file keys are .csv files"""

        for key in self.inputFiles:
            if not key.lower().endswith(".csv"):
                raise ValueError(f'Input file key "{key}" must be a .csv file name')
        return self

    @model_validator(mode="after")
    def validate_provenance_in_sources(self) -> "Config":
        """Validate that all input file provenances are in the sources section"""

        known_provenances = set()
        for source in self.sources.values():
            known_provenances.update(source.provenances.keys())

        # Validate that each InputFile provenance is among them
        for file_key, input_file in self.inputFiles.items():
            if input_file.provenance not in known_provenances:
                raise ValueError(
                    f'Input file "{file_key}" references unknown provenance "{input_file.provenance}".'
                )

        return self

    def validate_config(self) -> None:
        """Validate the config"""
        Config.model_validate(self.model_dump())

    @classmethod
    def from_json(cls, file_path: str | PathLike[str]) -> "Config":
        """Read the config from a JSON file

        Args:
            file_path: Path to the JSON file.

        Returns:
            Config: The config object.
        """

        with open(file_path) as f:
            data = f.read()
        return cls.model_validate_json(data)
