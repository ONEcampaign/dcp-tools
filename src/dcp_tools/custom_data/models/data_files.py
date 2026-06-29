from typing import Annotated, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from dcp_tools.custom_data.models.common import mint_dcid


class MCFFileName(BaseModel):
    file_name: Annotated[
        str, StringConstraints(strip_whitespace=True, pattern=r".*\.mcf$")
    ]


class ColumnMappings(BaseModel):
    """Representation of the ColumnMappings section of the InputFiles section of the config file

    The DCP importer keys observations by ``dcid:``-prefixed predicate names, so each
    field serialises to its ``dcid:`` alias (via ``model_dump(by_alias=True)``) while the
    friendly short name remains the Python attribute. Both forms are accepted on input.
    ``scalingFactor`` has no recognised ``dcid:`` key and stays a plain short field.

    Attributes:
        variable: Variable name.
        entity: Entity name.
        date: Date of the observation.
        value: Value of the observation.
        unit: Unit of the observation.
        scalingFactor: Scaling factor for the data.
        measurementMethod: Measurement method used for the data.
        observationPeriod: Observation period of the data.
    """

    variable: str | None = Field(
        default=None,
        validation_alias=AliasChoices("variable", "dcid:variableMeasured"),
        serialization_alias="dcid:variableMeasured",
    )
    entity: str | None = Field(
        default=None,
        validation_alias=AliasChoices("entity", "dcid:observationAbout"),
        serialization_alias="dcid:observationAbout",
    )
    date: str | None = Field(
        default=None,
        validation_alias=AliasChoices("date", "dcid:observationDate"),
        serialization_alias="dcid:observationDate",
    )
    value: str | None = Field(
        default=None,
        validation_alias=AliasChoices("value", "dcid:value"),
        serialization_alias="dcid:value",
    )
    unit: str | None = Field(
        default=None,
        validation_alias=AliasChoices("unit", "dcid:unit"),
        serialization_alias="dcid:unit",
    )
    scalingFactor: str | None = None
    measurementMethod: str | None = Field(
        default=None,
        validation_alias=AliasChoices("measurementMethod", "dcid:measurementMethod"),
        serialization_alias="dcid:measurementMethod",
    )
    observationPeriod: str | None = Field(
        default=None,
        validation_alias=AliasChoices("observationPeriod", "dcid:observationPeriod"),
        serialization_alias="dcid:observationPeriod",
    )

    model_config = ConfigDict(extra="forbid")


class ExplicitSchemaFile(BaseModel):
    """Representation of an input file using the explicit (variable-per-row) schema.

    Exactly one of ``filename`` or ``pattern`` must be set. The ``.csv``-suffix
    check applies to ``filename`` only; ``pattern`` entries are exempt.

    Attributes:
        filename: Exact CSV file name (mutually exclusive with ``pattern``).
        pattern: Glob pattern matching one or more input files (mutually exclusive
            with ``filename``). Pattern entries are config-only: ``data=`` is not
            accepted with ``pattern=``.
        provenance: Provenance name for the data. Bare name is minted as
            ``dcid:provenance/<name>``; pass an already ``dcid:``-prefixed value to
            use it verbatim. Names must be valid dcid tokens (no whitespace).
        ignoreColumns: List of columns to ignore.
        columnMappings: If headings in the CSV file do not use the default names,
            the equivalent names for each column.
        data_format: Format of the data (variable per row).
            This attribute is represented as "format" in the JSON.
    """

    filename: str | None = None
    pattern: str | None = None
    provenance: str
    ignoreColumns: list[str] | None = None
    columnMappings: ColumnMappings
    data_format: Literal["variablePerRow"] = Field(
        default="variablePerRow", alias="format"
    )

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("provenance", mode="after")
    @classmethod
    def _mint_provenance(cls, value: str) -> str:
        return mint_dcid(prefix="provenance", name=value)

    @model_validator(mode="after")
    def _validate_filename_or_pattern(self) -> "ExplicitSchemaFile":
        if (self.filename is None) == (self.pattern is None):
            raise ValueError("Exactly one of 'filename' or 'pattern' must be set.")
        if self.filename is not None and not self.filename.lower().endswith(".csv"):
            raise ValueError(f'filename "{self.filename}" must have a .csv extension.')
        return self
