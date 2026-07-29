"""Use the introspection helpers directly and build the form yourself."""

import panel as pn
import panel_material_ui as pmui

from panel_openapi import collect_fields
from panel_openapi import get_operation
from panel_openapi import load_openapi
from panel_openapi import schema_to_widget

pn.extension()

SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Orders", "version": "1.0.0"},
    "paths": {
        "/orders/{orderId}": {
            "put": {
                "summary": "Replace an order",
                "parameters": [
                    {
                        "name": "orderId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                    },
                    {"name": "dry_run", "in": "query", "schema": {"type": "boolean"}},
                ],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["sku"],
                                "properties": {
                                    "sku": {"type": "string"},
                                    "quantity": {
                                        "type": "integer",
                                        "minimum": 1,
                                        "maximum": 20,
                                    },
                                    "express": {"type": "boolean"},
                                },
                            }
                        }
                    }
                },
                "responses": {"200": {"description": "ok"}},
            }
        }
    },
}

openapi = load_openapi(SPEC)
operation = get_operation(openapi, "/orders/{orderId}", "put")
fields = collect_fields(openapi, operation)

# Group the widgets by where they end up in the request.
sections: dict[str, list] = {}
widgets = {}
for field in fields:
    widget = schema_to_widget(field.name, field.schema, field.required)
    widgets[field.name] = widget
    sections.setdefault(field.location, []).append(widget)

preview = pmui.Column(sizing_mode="stretch_width")


def show_request(event=None):
    """Preview what would be sent, rather than sending it."""
    values = {name: w.value for name, w in widgets.items()}
    preview[:] = [pn.pane.JSON(values, depth=-1, sizing_mode="stretch_width")]


pmui.Row(
    pmui.Column(
        *[item for location, group in sections.items() for item in (pmui.Typography(location.title(), variant="subtitle2"), *group)],
        pmui.Button(label="Preview request", variant="contained", on_click=show_request),
        width=380,
    ),
    preview,
    sizing_mode="stretch_width",
).servable(title="Build your own form")
