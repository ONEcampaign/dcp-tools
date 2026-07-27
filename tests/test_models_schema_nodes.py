import pytest
from pydantic import ValidationError

from dcp_tools.custom_data.models.schema_nodes import (
    EntityTypeNode,
    EventTypeNode,
    MeasurementMethodNode,
    PropertyNode,
    UnitOfMeasureNode,
)

# --- EntityTypeNode ---


def test_entity_type_default_typeof():
    node = EntityTypeNode(dcid="dcid:MyClass", name="My Class")
    assert node.type_of == "dcid:Class"
    assert "typeOf: dcid:Class" in node.to_mcf()


def test_entity_type_accepts_included_in_list():
    node = EntityTypeNode(
        dcid="dcid:MyClass",
        name="My Class",
        included_in=["dcid:provenance/p", "dcid:source/s"],
    )
    assert "includedIn: dcid:provenance/p, dcid:source/s" in node.to_mcf()


def test_entity_type_rejects_malformed_node():
    """Node field enforces dcid: prefix; builder normalizes before construction."""
    with pytest.raises(ValidationError):
        EntityTypeNode(dcid="MyClass", name="My Class")


def test_entity_type_included_in_normalizes_bare_token():
    """includedIn is DcidOrListDcid; a bare token is minted (regression for #126)."""
    node = EntityTypeNode(dcid="dcid:MyClass", name="My Class", included_in="p")
    assert node.included_in == "dcid:p"


# --- EventTypeNode ---


def test_event_type_default_typeof_and_subclassof():
    node = EventTypeNode(dcid="dcid:MyEvent", name="My Event")
    assert node.type_of == "dcid:Class"
    assert node.sub_class_of == "dcid:Event"


def test_event_type_subclassof_override():
    node = EventTypeNode(
        dcid="dcid:MyEvent", name="My Event", sub_class_of="dcid:DisasterEvent"
    )
    assert node.sub_class_of == "dcid:DisasterEvent"
    assert "subClassOf: dcid:DisasterEvent" in node.to_mcf()


def test_event_type_subclassof_normalizes_bare_token():
    """subClassOf is DcidOrListDcid; a bare token is minted (regression for #126)."""
    node = EventTypeNode(
        dcid="dcid:MyEvent", name="My Event", sub_class_of="DisasterEvent"
    )
    assert node.sub_class_of == "dcid:DisasterEvent"


# --- PropertyNode ---


def test_property_default_typeof():
    node = PropertyNode(dcid="dcid:myProp", name="My Prop")
    assert node.type_of == "dcid:Property"


def test_property_optional_refs_serialize():
    node = PropertyNode(
        dcid="dcid:myProp",
        name="My Prop",
        domain_includes="dcid:Person",
        range_includes="dcid:Number",
        sub_property_of="dcid:baseProp",
    )
    assert "domainIncludes: dcid:Person" in node.to_mcf()
    assert "rangeIncludes: dcid:Number" in node.to_mcf()
    assert "subPropertyOf: dcid:baseProp" in node.to_mcf()


def test_property_model_normalizes_bare_ref():
    """DcidOrListDcid now runs ensure_dcid via a BeforeValidator (regression for #126), so
    domainIncludes/rangeIncludes/subPropertyOf are normalized at the model layer too, not
    just by the builder (add_property). A bare token is minted to dcid:<token>."""
    node = PropertyNode(dcid="dcid:myProp", domain_includes="Person")
    assert node.domain_includes == "dcid:Person"


def test_property_model_rejects_whitespace_bearing_ref():
    with pytest.raises(ValidationError):
        PropertyNode(dcid="dcid:myProp", domain_includes="has space")


def test_property_model_normalizes_bare_ref_list():
    node = PropertyNode(
        dcid="dcid:myProp",
        domain_includes=["Person", "Household"],
        range_includes=["Number"],
        sub_property_of=["baseProp"],
    )
    assert node.domain_includes == ["dcid:Person", "dcid:Household"]
    assert node.range_includes == ["dcid:Number"]
    assert node.sub_property_of == ["dcid:baseProp"]


# --- UnitOfMeasureNode ---


def test_unit_default_typeof():
    node = UnitOfMeasureNode(dcid="dcid:MyUnit", name="My Unit")
    assert node.type_of == "dcid:UnitOfMeasure"


def test_unit_typeof_override_validates():
    node = UnitOfMeasureNode(
        dcid="dcid:USD", name="US Dollar", type_of="dcid:CurrencyUnitOfMeasure"
    )
    assert node.type_of == "dcid:CurrencyUnitOfMeasure"
    assert "typeOf: dcid:CurrencyUnitOfMeasure" in node.to_mcf()


def test_unit_inherits_short_display_name():
    node = UnitOfMeasureNode(dcid="dcid:USD", name="US Dollar", short_display_name="$")
    assert 'shortDisplayName: "$"' in node.to_mcf()


# --- MeasurementMethodNode ---


def test_measurement_method_default_typeof():
    node = MeasurementMethodNode(dcid="dcid:MyMethod")
    assert node.type_of == "dcid:MeasurementMethodEnum"


def test_measurement_method_typeof_override_validates():
    node = MeasurementMethodNode(dcid="dcid:MyCensus", type_of="dcid:CensusSurveyEnum")
    assert node.type_of == "dcid:CensusSurveyEnum"
    assert "typeOf: dcid:CensusSurveyEnum" in node.to_mcf()


def test_measurement_method_allows_missing_name():
    node = MeasurementMethodNode(dcid="dcid:MyMethod")
    assert "name:" not in node.to_mcf()
