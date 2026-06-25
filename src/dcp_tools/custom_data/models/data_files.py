from typing import Annotated, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, StringConstraints


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

    Attributes:
        provenance: Provenance of the data.
        ignoreColumns: List of columns to ignore.
        columnMappings: If headings in the CSV file do not use the default names,
            the equivalent names for each column.
        data_format: Format of the data (variable per row).
            This attribute is represented as "format" in the JSON.
    """

    provenance: str
    ignoreColumns: list[str] | None = None
    columnMappings: ColumnMappings
    data_format: Literal["variablePerRow"] = Field(
        default="variablePerRow", alias="format"
    )

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
