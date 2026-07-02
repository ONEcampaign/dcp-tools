import pytest
from pydantic import ValidationError

from dcp_tools.custom_data.models.schema_nodes import (
    EntityTypeMCFNode,
    EventTypeMCFNode,
    MeasurementMethodMCFNode,
    PropertyMCFNode,
    UnitOfMeasureMCFNode,
)

# --- EntityTypeMCFNode ---


def test_entity_type_default_typeof():
    node = EntityTypeMCFNode(Node="dcid:MyClass", name="My Class")
    assert node.typeOf == "dcid:Class"
    assert "typeOf: dcid:Class" in node.mcf


def test_entity_type_accepts_included_in_list():
    node = EntityTypeMCFNode(
        Node="dcid:MyClass",
        name="My Class",
        includedIn=["dcid:provenance/p", "dcid:source/s"],
    )
    assert "includedIn: dcid:provenance/p, dcid:source/s" in node.mcf


def test_entity_type_rejects_malformed_node():
    """Node field enforces dcid: prefix; builder normalizes before construction."""
    with pytest.raises(ValidationError):
        EntityTypeMCFNode(Node="MyClass", name="My Class")


# --- EventTypeMCFNode ---


def test_event_type_default_typeof_and_subclassof():
    node = EventTypeMCFNode(Node="dcid:MyEvent", name="My Event")
    assert node.typeOf == "dcid:Class"
    assert node.subClassOf == "dcid:Event"


def test_event_type_subclassof_override():
    node = EventTypeMCFNode(
        Node="dcid:MyEvent", name="My Event", subClassOf="dcid:DisasterEvent"
    )
    assert node.subClassOf == "dcid:DisasterEvent"
    assert "subClassOf: dcid:DisasterEvent" in node.mcf


# --- PropertyMCFNode ---


def test_property_default_typeof():
    node = PropertyMCFNode(Node="dcid:myProp", name="My Prop")
    assert node.typeOf == "dcid:Property"


def test_property_optional_refs_serialize():
    node = PropertyMCFNode(
        Node="dcid:myProp",
        name="My Prop",
        domainIncludes="dcid:Person",
        rangeIncludes="dcid:Number",
        subPropertyOf="dcid:baseProp",
    )
    assert "domainIncludes: dcid:Person" in node.mcf
    assert "rangeIncludes: dcid:Number" in node.mcf
    assert "subPropertyOf: dcid:baseProp" in node.mcf


def test_property_model_accepts_bare_ref_unvalidated():
    """DcidOrListDcid uses PlainValidator; the dcid: pattern is NOT enforced on ref fields.

    This documents that the builder (add_property, via ensure_dcid) — not the model — is
    what guarantees the dcid: prefix on domainIncludes/rangeIncludes/subPropertyOf. Contrast
    with test_entity_type_rejects_malformed_node: Node is a bare Dcid field and DOES enforce.
    """
    node = PropertyMCFNode(Node="dcid:myProp", domainIncludes="Person")
    assert node.domainIncludes == "Person"


# --- UnitOfMeasureMCFNode ---


def test_unit_default_typeof():
    node = UnitOfMeasureMCFNode(Node="dcid:MyUnit", name="My Unit")
    assert node.typeOf == "dcid:UnitOfMeasure"


def test_unit_typeof_override_validates():
    node = UnitOfMeasureMCFNode(
        Node="dcid:USD", name="US Dollar", typeOf="dcid:CurrencyUnitOfMeasure"
    )
    assert node.typeOf == "dcid:CurrencyUnitOfMeasure"
    assert "typeOf: dcid:CurrencyUnitOfMeasure" in node.mcf


def test_unit_inherits_short_display_name():
    node = UnitOfMeasureMCFNode(Node="dcid:USD", name="US Dollar", shortDisplayName="$")
    assert 'shortDisplayName: "$"' in node.mcf


# --- MeasurementMethodMCFNode ---


def test_measurement_method_default_typeof():
    node = MeasurementMethodMCFNode(Node="dcid:MyMethod")
    assert node.typeOf == "dcid:MeasurementMethodEnum"


def test_measurement_method_typeof_override_validates():
    node = MeasurementMethodMCFNode(
        Node="dcid:MyCensus", typeOf="dcid:CensusSurveyEnum"
    )
    assert node.typeOf == "dcid:CensusSurveyEnum"
    assert "typeOf: dcid:CensusSurveyEnum" in node.mcf


def test_measurement_method_allows_missing_name():
    node = MeasurementMethodMCFNode(Node="dcid:MyMethod")
    assert "name:" not in node.mcf
