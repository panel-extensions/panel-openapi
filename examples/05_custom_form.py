"""Build your own form from the schema and widget helpers.

``OpenAPIForm`` is a convenience layer over three public functions:

- ``load_openapi`` parses a spec from a URL, dict or model,
- ``get_operation`` finds one path + method in it,
- ``collect_fields`` flattens that operation's parameters and JSON body into
  ``Field`` descriptors, and
- ``schema_to_widget`` turns a single field's schema into a widget.

Reach for them when you want the schema-driven widgets but a layout, validation
flow or submit behaviour of your own. Here fields are grouped by where they
belong in the request, required inputs are marked, and instead of firing a
request the form previews the payload it would send.

If you only need a different layout around the standard widgets, note that
``OpenAPIForm`` exposes its ``form`` and ``response`` containers and its
``fields``/``widgets``, which is often enough without dropping down here.

Run with::

    panel serve examples/05_custom_form.py --show
"""

from __future__ import annotations

import json

import panel as pn
import panel_material_ui as pmui

from panel_openapi import collect_fields, get_operation, load_openapi, schema_to_widget

pn.extension()

SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Deployments", "version": "1.0.0"},
    "paths": {
        "/projects/{project}/deployments": {
            "post": {
                "summary": "Create a deployment",
                "parameters": [
                    {
                        "name": "project",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "title": "Project"},
                    },
                    {
                        "name": "dry_run",
                        "in": "query",
                        "schema": {"type": "boolean", "title": "Dry run"},
                    },
                    {
                        "name": "X-Request-Id",
                        "in": "header",
                        "schema": {"type": "string", "title": "Request ID"},
                    },
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["ref", "environment"],
                                "properties": {
                                    "ref": {
                                        "type": "string",
                                        "title": "Git ref",
                                        "default": "main",
                                    },
                                    "environment": {
                                        "type": "string",
                                        "enum": ["dev", "staging", "prod"],
                                        "title": "Environment",
                                    },
                                    "replicas": {
                                        "type": "integer",
                                        "minimum": 1,
                                        "maximum": 10,
                                        "title": "Replicas",
                                    },
                                },
                            }
                        }
                    },
                },
                "responses": {"201": {"description": "Created."}},
            }
        }
    },
}

PATH = "/projects/{project}/deployments"

openapi = load_openapi(SPEC)
operation = get_operation(openapi, PATH, "post")
fields = collect_fields(openapi, operation)

# One widget per field, keeping the Field descriptor alongside it so we know
# where each value belongs in the request.
inputs = [
    (field, schema_to_widget(field.name, field.schema, field.required)) for field in fields
]

SECTIONS = {
    "path": "Path parameters",
    "query": "Query parameters",
    "header": "Headers",
    "body": "Request body",
}


def _row(field, widget) -> pmui.Row:
    """A widget with a required/optional marker beside it."""
    widget.sizing_mode = "stretch_width"
    marker = pmui.Chip(
        object="required" if field.required else "optional",
        color="error" if field.required else "default",
        size="small",
        margin=(20, 5),
    )
    return pmui.Row(widget, marker, sizing_mode="stretch_width")


sections = []
for location, header in SECTIONS.items():
    grouped = [(f, w) for f, w in inputs if f.location == location]
    if not grouped:
        continue
    sections.append(
        pmui.Card(
            *[_row(f, w) for f, w in grouped],
            title=header,
            collapsible=False,
            sizing_mode="stretch_width",
        )
    )

preview = pmui.Column(sizing_mode="stretch_width")


def _preview(event=None) -> None:
    """Validate the inputs and show the request that would be sent."""
    missing = [f.name for f, w in inputs if f.required and w.value in (None, "", [], {})]
    if missing:
        preview[:] = [
            pmui.Alert(
                object=f"Missing required fields: {', '.join(missing)}", severity="warning"
            )
        ]
        return

    path = PATH
    request = {"query": {}, "headers": {}, "body": {}}
    for field, widget in inputs:
        value = widget.value
        if value in (None, "", [], {}):
            continue
        if field.location == "path":
            path = path.replace(f"{{{field.name}}}", str(value))
        elif field.location == "query":
            request["query"][field.name] = value
        elif field.location == "header":
            request["headers"][field.name] = value
        else:
            request["body"][field.name] = value

    preview[:] = [
        pmui.Alert(object=f"POST {path}", severity="info"),
        pn.pane.JSON(json.dumps(request), depth=-1, sizing_mode="stretch_width"),
    ]


pmui.Page(
    title=operation.summary,
    main=[
        pmui.Column(
            *sections,
            pmui.Button(label="Preview request", variant="contained", on_click=_preview),
            preview,
            sizing_mode="stretch_width",
        )
    ],
).servable()
