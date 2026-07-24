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
    assert node.typeOf == "dcid:Class"
    assert "typeOf: dcid:Class" in node.to_mcf()


def test_entity_type_accepts_included_in_list():
    node = EntityTypeNode(
        dcid="dcid:MyClass",
        name="My Class",
        includedIn=["dcid:provenance/p", "dcid:source/s"],
    )
    assert "includedIn: dcid:provenance/p, dcid:source/s" in node.to_mcf()


def test_entity_type_rejects_malformed_node():
    """Node field enforces dcid: prefix; builder normalizes before construction."""
    with pytest.raises(ValidationError):
        EntityTypeNode(dcid="MyClass", name="My Class")


def test_entity_type_included_in_normalizes_bare_token():
    """includedIn is DcidOrListDcid; a bare token is minted (regression for #126)."""
    node = EntityTypeNode(dcid="dcid:MyClass", name="My Class", includedIn="p")
    assert node.includedIn == "dcid:p"


# --- EventTypeNode ---


def test_event_type_default_typeof_and_subclassof():
    node = EventTypeNode(dcid="dcid:MyEvent", name="My Event")
    assert node.typeOf == "dcid:Class"
    assert node.subClassOf == "dcid:Event"


def test_event_type_subclassof_override():
    node = EventTypeNode(
        dcid="dcid:MyEvent", name="My Event", subClassOf="dcid:DisasterEvent"
    )
    assert node.subClassOf == "dcid:DisasterEvent"
    assert "subClassOf: dcid:DisasterEvent" in node.to_mcf()


def test_event_type_subclassof_normalizes_bare_token():
    """subClassOf is DcidOrListDcid; a bare token is minted (regression for #126)."""
    node = EventTypeNode(
        dcid="dcid:MyEvent", name="My Event", subClassOf="DisasterEvent"
    )
    assert node.subClassOf == "dcid:DisasterEvent"


# --- PropertyNode ---


def test_property_default_typeof():
    node = PropertyNode(dcid="dcid:myProp", name="My Prop")
    assert node.typeOf == "dcid:Property"


def test_property_optional_refs_serialize():
    node = PropertyNode(
        dcid="dcid:myProp",
        name="My Prop",
        domainIncludes="dcid:Person",
        rangeIncludes="dcid:Number",
        subPropertyOf="dcid:baseProp",
    )
    assert "domainIncludes: dcid:Person" in node.to_mcf()
    assert "rangeIncludes: dcid:Number" in node.to_mcf()
    assert "subPropertyOf: dcid:baseProp" in node.to_mcf()


def test_property_model_normalizes_bare_ref():
    """DcidOrListDcid now runs ensure_dcid via a BeforeValidator (regression for #126), so
    domainIncludes/rangeIncludes/subPropertyOf are normalized at the model layer too, not
    just by the builder (add_property). A bare token is minted to dcid:<token>."""
    node = PropertyNode(dcid="dcid:myProp", domainIncludes="Person")
    assert node.domainIncludes == "dcid:Person"


def test_property_model_rejects_whitespace_bearing_ref():
    with pytest.raises(ValidationError):
        PropertyNode(dcid="dcid:myProp", domainIncludes="has space")


def test_property_model_normalizes_bare_ref_list():
    node = PropertyNode(
        dcid="dcid:myProp",
        domainIncludes=["Person", "Household"],
        rangeIncludes=["Number"],
        subPropertyOf=["baseProp"],
    )
    assert node.domainIncludes == ["dcid:Person", "dcid:Household"]
    assert node.rangeIncludes == ["dcid:Number"]
    assert node.subPropertyOf == ["dcid:baseProp"]


# --- UnitOfMeasureNode ---


def test_unit_default_typeof():
    node = UnitOfMeasureNode(dcid="dcid:MyUnit", name="My Unit")
    assert node.typeOf == "dcid:UnitOfMeasure"


def test_unit_typeof_override_validates():
    node = UnitOfMeasureNode(
        dcid="dcid:USD", name="US Dollar", typeOf="dcid:CurrencyUnitOfMeasure"
    )
    assert node.typeOf == "dcid:CurrencyUnitOfMeasure"
    assert "typeOf: dcid:CurrencyUnitOfMeasure" in node.to_mcf()


def test_unit_inherits_short_display_name():
    node = UnitOfMeasureNode(dcid="dcid:USD", name="US Dollar", shortDisplayName="$")
    assert 'shortDisplayName: "$"' in node.to_mcf()


# --- MeasurementMethodNode ---


def test_measurement_method_default_typeof():
    node = MeasurementMethodNode(dcid="dcid:MyMethod")
    assert node.typeOf == "dcid:MeasurementMethodEnum"


def test_measurement_method_typeof_override_validates():
    node = MeasurementMethodNode(dcid="dcid:MyCensus", typeOf="dcid:CensusSurveyEnum")
    assert node.typeOf == "dcid:CensusSurveyEnum"
    assert "typeOf: dcid:CensusSurveyEnum" in node.to_mcf()


def test_measurement_method_allows_missing_name():
    node = MeasurementMethodNode(dcid="dcid:MyMethod")
    assert "name:" not in node.to_mcf()
