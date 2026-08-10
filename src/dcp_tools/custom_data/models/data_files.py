from typing import Annotated, Any, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    StringConstraints,
    field_validator,
    model_serializer,
    model_validator,
)
from pydantic.alias_generators import to_camel

from dcp_tools.custom_data.models.common import CustomDimensionName, mint_dcid


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
        date: Date of the observation.
        value: Value of the observation.
        unit: Unit of the observation.
        scaling_factor: Scaling factor for the data.
        measurement_method: Measurement method used for the data.
        observation_period: Observation period of the data.
        observation_about: Entity column for single-entity data.
        custom_dimensions: Entity columns for multi-entity data.
    """

    variable: str | None = Field(
        default=None,
        validation_alias=AliasChoices("variable", "dcid:variableMeasured"),
        serialization_alias="dcid:variableMeasured",
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
    scaling_factor: str | None = None
    measurement_method: str | None = Field(
        default=None,
        validation_alias=AliasChoices("measurementMethod", "dcid:measurementMethod"),
        serialization_alias="dcid:measurementMethod",
    )
    observation_period: str | None = Field(
        default=None,
        validation_alias=AliasChoices("observationPeriod", "dcid:observationPeriod"),
        serialization_alias="dcid:observationPeriod",
    )
    observation_about: str | None = Field(
        default=None,
        validation_alias=AliasChoices("observationAbout", "dcid:observationAbout"),
        serialization_alias="dcid:observationAbout",
    )
    custom_dimensions: dict[CustomDimensionName, str] = Field(
        default_factory=dict,
    )

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
        serialize_by_alias=True,
    )

    @model_serializer(mode="wrap")
    def _serialize(self, handler: SerializerFunctionWrapHandler) -> dict[str, str]:
        data = handler(self)
        for name, column in (data.pop("customDimensions", None) or {}).items():
            data[f"custom:{name}"] = column
        return data

    @model_validator(mode="before")
    @classmethod
    def _collect_custom_dimensions(cls, data: Any) -> Any:
        if isinstance(data, dict):
            dims = {
                k[len("custom:") :]: v
                for k, v in data.items()
                if isinstance(k, str) and k.startswith("custom:")
            }
            if dims:
                data = {
                    k: v
                    for k, v in data.items()
                    if not (isinstance(k, str) and k.startswith("custom:"))
                }
                data["customDimensions"] = dims
        return data


class ObservationProperties(BaseModel):
    """File-level constant observation properties for an input file.

    Applied as constants to every observation in the file (the only working route to a
    constant ``unit``/``scalingFactor``/``measurementMethod``/``observationPeriod``). Keys
    are emitted verbatim with no ``dcid:`` aliasing; the DCP importer reads the four standard
    keys directly and passes any custom keys through unchanged.

    Attributes:
        unit: Unit applied to every observation.
        scaling_factor: Scaling factor applied to every observation.
        measurement_method: Measurement method applied to every observation.
        observation_period: Observation period applied to every observation.
    """

    unit: str | None = None
    scaling_factor: str | None = None
    measurement_method: str | None = None
    observation_period: str | None = None

    model_config = ConfigDict(extra="allow")


class InputFile(BaseModel):
    """Representation of an entry in the config's ``inputFiles`` list.

    An entry declares either a CSV file of observations in variable-per-row form (one
    observation per row) or an MCF file of node definitions. Both need a ``provenance``;
    only CSV entries need column mappings and a format.

    Exactly one of ``filename`` or ``pattern`` must be set:
    - ``filename`` names one CSV file and must end in ``.csv``.
    - ``pattern`` is a glob matching one or more files, and is the only way to declare
      an MCF file. An exact file name works too, since a literal name is a valid glob.

    Attributes:
        filename: Exact CSV file name (mutually exclusive with ``pattern``; must have a
            ``.csv`` extension).
        pattern: Glob pattern matching one or more input files (mutually exclusive
            with ``filename``). Pattern entries are config-only: ``data=`` is not
            accepted with ``pattern=``. The only way to declare an MCF file; no
            extension check applies here.
        provenance: Provenance name for the data. Bare name is minted as
            ``dcid:provenance/<name>``; pass an already ``dcid:``-prefixed value to
            use it verbatim. Names must be valid dcid tokens (no whitespace).
        ignore_columns: List of columns to ignore.
        column_mappings: If headings in the CSV file do not use the default names,
            the equivalent names for each column. Absent for MCF entries.
        observation_properties: File-level constant observation properties applied to every
            observation (constants such as unit or measurementMethod). Optional; absent
            for MCF entries.
        data_format: Format of the data (variable per row, one observation per row).
            This attribute is represented as "format" in the JSON. Absent for MCF entries.
    """

    filename: str | None = None
    pattern: str | None = None
    provenance: str
    ignore_columns: list[str] | None = None
    column_mappings: ColumnMappings | None = None
    observation_properties: ObservationProperties | None = None
    data_format: Literal["variablePerRow"] | None = Field(default=None, alias="format")

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="forbid",
        populate_by_name=True,
    )

    @property
    def is_mcf(self) -> bool:
        """Whether this entry declares an MCF file rather than a CSV.

        Checks both ``filename`` and ``pattern`` for symmetry, but a validated instance
        can never have a ``.mcf`` ``filename``, so in practice this is only true for
        ``pattern`` entries.
        """
        return (self.filename or self.pattern or "").lower().endswith(".mcf")

    @field_validator("provenance", mode="after")
    @classmethod
    def _mint_provenance(cls, value: str) -> str:
        return mint_dcid(prefix="provenance", token=value)

    @model_validator(mode="after")
    def _validate_entry(self) -> "InputFile":
        if (self.filename is None) == (self.pattern is None):
            raise ValueError("Exactly one of 'filename' or 'pattern' must be set.")
        # `filename` is CSV-only because add_data, export_data, and
        # validate_all_input_files_have_data treat every filename entry as a
        # data-bearing CSV target, without checking `is_mcf`. A `.mcf` filename would
        # let them silently handle an MCF declaration as a CSV.
        if self.filename is not None and not self.filename.lower().endswith(".csv"):
            raise ValueError(f'filename "{self.filename}" must have a .csv extension.')
        if self.is_mcf:
            # An MCF file holds node definitions, not observations, so none of the
            # observation settings below apply.
            return self
        if self.column_mappings is None:
            self.column_mappings = ColumnMappings()
        if self.data_format is None:
            self.data_format = "variablePerRow"
        return self
