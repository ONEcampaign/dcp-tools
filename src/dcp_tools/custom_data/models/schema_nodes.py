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
        type_of: Fixed type indicating this is a Class (``dcid:Class``).
        included_in: Optional provenance/source DCID(s) the entity type is defined in.
    """

    type_of: Literal["dcid:Class"] = "dcid:Class"
    included_in: DcidOrListDcid | None = None


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
        type_of: Fixed type indicating this is a Class (``dcid:Class``).
        sub_class_of: Parent class; defaults to ``dcid:Event`` (overridable).
        included_in: Optional provenance/source DCID(s) the event type is defined in.
    """

    type_of: Literal["dcid:Class"] = "dcid:Class"
    sub_class_of: DcidOrListDcid = "dcid:Event"
    included_in: DcidOrListDcid | None = None


class GenericNode(Node):
    """Represents an arbitrary Data Commons node with a caller-supplied ``typeOf``.

    Used for entity instances (e.g. an organisation acting as a CRS provider) or
    generic constraint-value classes (e.g. ``Commitment``, ``MalariaControl``) that
    don't fit one of the other typed builders. ``includedIn`` references the
    provenance(s) — and, via the builder, their linked source(s) — the node is
    defined in.

    Attributes:
        # Inherited from Node
        dcid: Identifier for the Node.
        name: The human-readable name for the Node.
        type_of: DCID(s) of the node's type(s).
        description: Optional human-readable description.

        # GenericNode-specific
        included_in: Optional provenance/source DCID(s) the node is defined in.
    """

    included_in: DcidOrListDcid | None = None


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
        type_of: Fixed type indicating this is a Property (``dcid:Property``).
        domain_includes: Optional DCID(s) of classes the property applies to.
        range_includes: Optional DCID(s) of classes that are the value type.
        sub_property_of: Optional DCID(s) of parent properties.
    """

    type_of: Literal["dcid:Property"] = "dcid:Property"
    domain_includes: DcidOrListDcid | None = None
    range_includes: DcidOrListDcid | None = None
    sub_property_of: DcidOrListDcid | None = None


class UnitOfMeasureNode(Node):
    """Represents a Data Commons UnitOfMeasure node.

    typeOf defaults to ``dcid:UnitOfMeasure`` and is overridable (e.g.
    ``dcid:CurrencyUnitOfMeasure``). ``name``/``shortDisplayName``/``description`` are
    inherited from Node.

    Attributes:
        # Inherited from Node
        dcid: Identifier for the Node (e.g. ``dcid:MyUnit``).
        name: The human-readable name for the Node.
        short_display_name: Optional short display name (e.g. ``"$"``).
        description: Optional human-readable description.

        # UnitOfMeasure-specific
        type_of: Type of unit; defaults to ``dcid:UnitOfMeasure`` (overridable).
    """

    type_of: DcidOrListDcid = "dcid:UnitOfMeasure"


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
        type_of: Measurement method enum type; defaults to ``dcid:MeasurementMethodEnum``
            (overridable).
    """

    type_of: DcidOrListDcid = "dcid:MeasurementMethodEnum"
