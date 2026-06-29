from pydantic import BaseModel, ConfigDict, Field


class VerticalSpec(BaseModel):
    """A single entry in the vertical-specs file guiding StatVar hierarchy generation.

    Each spec maps stat vars about a ``populationType`` with the given
    ``measuredProperties`` to one or more ``verticals`` (top-level groups) in the
    hierarchy the importer generates when ``groupStatVarsByProperty`` is set. Specs are
    serialized as the objects in the ``{"specs": [...]}`` JSON file the importer reads;
    the field names match the keys the importer expects (``data.py:VerticalSpec``).

    Attributes:
        populationType: Population type the spec applies to. Defaults to ``"Thing"``,
            matching the importer's own default.
        measuredProperties: Measured properties the spec applies to.
        verticals: Vertical (top-level group) names to file matching stat vars under.
    """

    populationType: str = "Thing"
    measuredProperties: list[str] = Field(default_factory=list)
    verticals: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")
