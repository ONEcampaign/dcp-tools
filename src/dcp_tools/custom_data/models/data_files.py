from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


class MCFFileName(BaseModel):
    file_name: Annotated[
        str, StringConstraints(strip_whitespace=True, pattern=r".*\.mcf$")
    ]


class ColumnMappings(BaseModel):
    """Representation of the ColumnMappings section of the InputFiles section of the config file

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

    variable: str | None = None
    entity: str | None = None
    date: str | None = None
    value: str | None = None
    unit: str | None = None
    scalingFactor: str | None = None
    measurementMethod: str | None = None
    observationPeriod: str | None = None

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
