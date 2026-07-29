"""Tests for panel_openapi.widgets."""

import panel_material_ui as pmui
import pytest
from openapi_pydantic import Schema

from panel_openapi.widgets import schema_to_widget


@pytest.mark.parametrize(
    "spec, expected",
    [
        ({"type": "string", "enum": ["a", "b"]}, pmui.RadioButtonGroup),
        ({"type": "string", "enum": ["a", "b", "c", "d"]}, pmui.Select),
        ({"type": "string"}, pmui.TextInput),
        ({"type": "string", "format": "password"}, pmui.PasswordInput),
        ({"type": "string", "format": "date"}, pmui.DatePicker),
        ({"type": "string", "format": "date-time"}, pmui.DatetimePicker),
        ({"type": "integer"}, pmui.IntInput),
        ({"type": "integer", "minimum": 1, "maximum": 10}, pmui.IntSlider),
        ({"type": "number"}, pmui.FloatInput),
        ({"type": "number", "minimum": 0, "maximum": 1}, pmui.FloatSlider),
        ({"type": "boolean"}, pmui.Checkbox),
        ({"type": "array", "items": {"type": "string", "enum": ["x", "y"]}}, pmui.MultiChoice),
        ({"type": "array", "items": {"type": "string"}}, pmui.TextAreaInput),
        ({"type": "object"}, pmui.TextAreaInput),
        ({}, pmui.TextAreaInput),
        ({"type": ["string", "null"]}, pmui.TextInput),
        # anyOf with a single non-null branch is how pydantic renders `T | None`,
        # which covers most fields of a PATCH request model.
        ({"anyOf": [{"type": "string"}, {"type": "null"}]}, pmui.TextInput),
        ({"anyOf": [{"type": "boolean"}, {"type": "null"}]}, pmui.Checkbox),
        ({"oneOf": [{"type": "integer"}, {"type": "null"}]}, pmui.IntInput),
        (
            {"anyOf": [{"type": "string", "enum": ["a", "b"]}, {"type": "null"}]},
            pmui.RadioButtonGroup,
        ),
        # A genuine union of two concrete types stays a JSON text area.
        ({"anyOf": [{"type": "string"}, {"type": "integer"}]}, pmui.TextAreaInput),
    ],
)
def test_widget_type(spec, expected):
    widget = schema_to_widget("field", Schema.model_validate(spec))
    assert isinstance(widget, expected)


def test_nullable_union_keeps_outer_metadata():
    widget = schema_to_widget(
        "field",
        Schema.model_validate(
            {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "title": "Notes",
                "description": "Free text.",
                "default": "hi",
            }
        ),
    )
    assert isinstance(widget, pmui.TextInput)
    assert widget.label == "Notes"
    assert widget.description == "Free text."
    assert widget.value == "hi"


def test_default_applied():
    widget = schema_to_widget("field", Schema.model_validate({"type": "string", "default": "hi"}))
    assert widget.value == "hi"


def test_bounds_applied():
    widget = schema_to_widget(
        "field", Schema.model_validate({"type": "integer", "minimum": 2, "maximum": 8})
    )
    assert widget.start == 2
    assert widget.end == 8


def test_title_used_as_label():
    widget = schema_to_widget("field", Schema.model_validate({"type": "string", "title": "Nice"}))
    assert widget.label == "Nice"


def test_required_tag():
    required = schema_to_widget("field", Schema.model_validate({"type": "string"}), required=True)
    optional = schema_to_widget("field", Schema.model_validate({"type": "string"}))
    assert "required" in required.tags
    assert "optional" in optional.tags
