import pytest
from pydantic import ValidationError

from dcp_tools.custom_data.models.vertical_specs import VerticalSpec


def test_vertical_spec_defaults():
    spec = VerticalSpec(verticals=["PersonCountVertical"])
    assert spec.population_type == "Thing"
    assert spec.measured_properties == []
    assert spec.verticals == ["PersonCountVertical"]


def test_vertical_spec_round_trips():
    spec = VerticalSpec(
        population_type="Person",
        measured_properties=["count"],
        verticals=["PersonCountVertical"],
    )
    dumped = spec.model_dump(mode="json")
    assert dumped == {
        "populationType": "Person",
        "measuredProperties": ["count"],
        "verticals": ["PersonCountVertical"],
    }
    assert VerticalSpec.model_validate(dumped) == spec


def test_vertical_spec_rejects_unknown_field():
    with pytest.raises(ValidationError):
        VerticalSpec.model_validate({"verticals": ["v"], "unexpected": "x"})
