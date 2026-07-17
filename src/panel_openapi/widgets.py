"""Map OpenAPI/JSON schemas to panel-material-ui widgets.

The single public entry point is :func:`schema_to_widget`, which inspects a
resolved :class:`~openapi_pydantic.Schema` and returns the most appropriate
panel-material-ui widget for editing that value.
"""

from __future__ import annotations

from typing import Any

import panel_material_ui as pmui
from openapi_pydantic import Schema

# Number of enum options at or below which a RadioButtonGroup is preferred
# over a Select.
_RADIO_THRESHOLD = 3


def _schema_type(schema: Schema) -> str | None:
    """Return the primary non-null type of a schema.

    OpenAPI 3.1 allows ``type`` to be a list (e.g. ``["string", "null"]``);
    this collapses it to the first meaningful type.
    """
    type_ = schema.type
    if type_ is None:
        return None
    if isinstance(type_, list):
        for entry in type_:
            value = getattr(entry, "value", entry)
            if value != "null":
                return value
        return None
    return getattr(type_, "value", type_)


def _label(name: str, schema: Schema) -> str:
    """Human-readable label for a field."""
    return schema.title or name


def _common_kwargs(name: str, schema: Schema) -> dict[str, Any]:
    """Widget keyword arguments shared across all widget types."""
    kwargs: dict[str, Any] = {"label": _label(name, schema)}
    if schema.description:
        kwargs["description"] = schema.description
    return kwargs


def _enum_widget(name: str, schema: Schema) -> pmui.widgets.Widget:
    options = list(schema.enum or [])
    kwargs = _common_kwargs(name, schema)
    if schema.default is not None:
        kwargs["value"] = schema.default
    if 0 < len(options) <= _RADIO_THRESHOLD:
        return pmui.RadioButtonGroup(options=options, **kwargs)
    return pmui.Select(options=options, **kwargs)


def _string_widget(name: str, schema: Schema) -> pmui.widgets.Widget:
    kwargs = _common_kwargs(name, schema)
    if schema.default is not None:
        kwargs["value"] = schema.default
    fmt = schema.schema_format
    if fmt == "password":
        return pmui.PasswordInput(**kwargs)
    if fmt in ("date",):
        kwargs.pop("value", None)
        return pmui.DatePicker(**kwargs)
    if fmt in ("date-time", "datetime"):
        kwargs.pop("value", None)
        return pmui.DatetimePicker(**kwargs)
    return pmui.TextInput(**kwargs)


def _number_widget(name: str, schema: Schema, integer: bool) -> pmui.widgets.Widget:
    kwargs = _common_kwargs(name, schema)
    cast = int if integer else float
    if schema.default is not None:
        kwargs["value"] = cast(schema.default)
    low, high = schema.minimum, schema.maximum
    if low is not None and high is not None:
        kwargs.setdefault("value", cast(low))
        slider = pmui.IntSlider if integer else pmui.FloatSlider
        return slider(start=cast(low), end=cast(high), **kwargs)
    if low is not None:
        kwargs["start"] = cast(low)
    if high is not None:
        kwargs["end"] = cast(high)
    spinner = pmui.IntInput if integer else pmui.FloatInput
    return spinner(**kwargs)


def _boolean_widget(name: str, schema: Schema) -> pmui.widgets.Widget:
    kwargs = _common_kwargs(name, schema)
    kwargs["value"] = bool(schema.default)
    return pmui.Checkbox(**kwargs)


def _array_widget(name: str, schema: Schema) -> pmui.widgets.Widget:
    kwargs = _common_kwargs(name, schema)
    items = schema.items if isinstance(schema.items, Schema) else None
    if items is not None and items.enum:
        return pmui.MultiChoice(options=list(items.enum), **kwargs)
    # Free-form arrays (arbitrary strings or complex items) are edited as JSON
    # since MultiChoice cannot accept values outside its options.
    return _json_widget(name, schema)


def _json_widget(name: str, schema: Schema) -> pmui.widgets.Widget:
    kwargs = _common_kwargs(name, schema)
    placeholder = "Enter JSON"
    return pmui.TextAreaInput(placeholder=placeholder, **kwargs)


def schema_to_widget(name: str, schema: Schema, required: bool = False) -> pmui.widgets.Widget:
    """Return a panel-material-ui widget for editing a schema value.

    Parameters
    ----------
    name : str
        The field name, used as the widget label when no ``title`` is set.
    schema : Schema
        The resolved JSON schema describing the value.
    required : bool
        Whether the field is required. Recorded on the widget's ``tags`` so the
        form layer can validate and render it accordingly.

    Returns
    -------
    panel_material_ui.widgets.Widget
        The widget best matching the schema. Values of type ``object`` or of an
        unknown type fall back to a JSON text area.
    """
    if schema.enum:
        widget = _enum_widget(name, schema)
    else:
        type_ = _schema_type(schema)
        if type_ == "string":
            widget = _string_widget(name, schema)
        elif type_ == "integer":
            widget = _number_widget(name, schema, integer=True)
        elif type_ == "number":
            widget = _number_widget(name, schema, integer=False)
        elif type_ == "boolean":
            widget = _boolean_widget(name, schema)
        elif type_ == "array":
            widget = _array_widget(name, schema)
        else:
            widget = _json_widget(name, schema)

    widget.tags = [*widget.tags, "required" if required else "optional"]
    return widget
