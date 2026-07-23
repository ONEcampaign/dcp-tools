from typing import Literal

from dcp_tools.custom_data.models.common import DcidOrListDcid
from dcp_tools.custom_data.models.mcf import Node


class EntityTypeNode(Node):
    """Represents a Data Commons entity-type (Class) node.

    typeOf is fixed to ``dcid:Class``. ``includedIn`` references the provenance(s) — and,
    via the builder, their linked source(s) — the type is defined in.

    Attributes:
        # Inherited from Node
        dcid: Identifier for the Node (e.g. ``dcid:MyClass``).
        name: The human-readable name for the Node.
        description: Optional human-readable description.

        # EntityType-specific
        typeOf: Fixed type indicating this is a Class (``dcid:Class``).
        includedIn: Optional provenance/source DCID(s) the entity type is defined in.
    """

    typeOf: Literal["dcid:Class"] = "dcid:Class"
    includedIn: DcidOrListDcid | None = None


class EventTypeNode(Node):
    """Represents a Data Commons event-type node.

    typeOf is fixed to ``dcid:Class``; ``subClassOf`` defaults to ``dcid:Event`` and is
    overridable. ``includedIn`` mirrors EntityType.

    Attributes:
        # Inherited from Node
        dcid: Identifier for the Node (e.g. ``dcid:MyEventType``).
        name: The human-readable name for the Node.
        description: Optional human-readable description.

        # EventType-specific
        typeOf: Fixed type indicating this is a Class (``dcid:Class``).
        subClassOf: Parent class; defaults to ``dcid:Event`` (overridable).
        includedIn: Optional provenance/source DCID(s) the event type is defined in.
    """

    typeOf: Literal["dcid:Class"] = "dcid:Class"
    subClassOf: DcidOrListDcid = "dcid:Event"
    includedIn: DcidOrListDcid | None = None


class PropertyNode(Node):
    """Represents a Data Commons Property node.

    typeOf is fixed to ``dcid:Property``. Optional schema refs describe the property's
    domain, range, and parent property.

    Attributes:
        # Inherited from Node
        dcid: Identifier for the Node (e.g. ``dcid:myProperty``).
        name: The human-readable name for the Node.
        description: Optional human-readable description.

        # Property-specific
        typeOf: Fixed type indicating this is a Property (``dcid:Property``).
        domainIncludes: Optional DCID(s) of classes the property applies to.
        rangeIncludes: Optional DCID(s) of classes that are the value type.
        subPropertyOf: Optional DCID(s) of parent properties.
    """

    typeOf: Literal["dcid:Property"] = "dcid:Property"
    domainIncludes: DcidOrListDcid | None = None
    rangeIncludes: DcidOrListDcid | None = None
    subPropertyOf: DcidOrListDcid | None = None


class UnitOfMeasureNode(Node):
    """Represents a Data Commons UnitOfMeasure node.

    typeOf defaults to ``dcid:UnitOfMeasure`` and is overridable (e.g.
    ``dcid:CurrencyUnitOfMeasure``). ``name``/``shortDisplayName``/``description`` are
    inherited from Node.

    Attributes:
        # Inherited from Node
        dcid: Identifier for the Node (e.g. ``dcid:MyUnit``).
        name: The human-readable name for the Node.
        shortDisplayName: Optional short display name (e.g. ``"$"``).
        description: Optional human-readable description.

        # UnitOfMeasure-specific
        typeOf: Type of unit; defaults to ``dcid:UnitOfMeasure`` (overridable).
    """

    typeOf: DcidOrListDcid = "dcid:UnitOfMeasure"


class MeasurementMethodNode(Node):
    """Represents a Data Commons MeasurementMethod node.

    typeOf defaults to ``dcid:MeasurementMethodEnum`` and is overridable (e.g.
    ``dcid:CensusSurveyEnum``). ``name`` is optional (inherited).

    Attributes:
        # Inherited from Node
        dcid: Identifier for the Node (e.g. ``dcid:MyMethod``).
        name: Optional human-readable name for the Node.
        description: Optional human-readable description.

        # MeasurementMethod-specific
        typeOf: Measurement method enum type; defaults to ``dcid:MeasurementMethodEnum``
            (overridable).
    """

    typeOf: DcidOrListDcid = "dcid:MeasurementMethodEnum"
