"""Lay out the form and response yourself.

By default ``OpenAPIForm`` renders as a ``Row`` of inputs beside the response.
Its ``form`` and ``response`` containers are public, so you can place them
wherever you like instead: here the inputs go in the sidebar and the response
fills the main area.

Both containers are mutated in place when the operation changes, so a layout
built once around them keeps working as ``path`` and ``method`` change. This
example drives one form from a sidebar operation picker to show that.

Run with::

    panel serve examples/06_custom_layout.py --show
"""

from __future__ import annotations

import panel as pn
import panel_material_ui as pmui

from panel_openapi import OpenAPIForm

pn.extension()

SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "httpbin", "version": "1.0.0"},
    "paths": {
        "/get": {
            "get": {
                "summary": "Inspect a GET request",
                "parameters": [
                    {
                        "name": "search",
                        "in": "query",
                        "schema": {"type": "string", "title": "Search term"},
                    },
                    {
                        "name": "page",
                        "in": "query",
                        "schema": {"type": "integer", "minimum": 1, "maximum": 20, "title": "Page"},
                    },
                ],
                "responses": {"200": {"description": "The echoed request."}},
            }
        },
        "/post": {
            "post": {
                "summary": "Inspect a POST request",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["message"],
                                "properties": {
                                    "message": {"type": "string", "title": "Message"},
                                    "urgent": {"type": "boolean", "title": "Urgent"},
                                },
                            }
                        }
                    },
                },
                "responses": {"200": {"description": "The echoed request."}},
            }
        },
        "/status/{code}": {
            "get": {
                "summary": "Return a given status code",
                "description": "Try 404 or 500 to see how error responses are rendered.",
                "parameters": [
                    {
                        "name": "code",
                        "in": "path",
                        "required": True,
                        "schema": {
                            "type": "integer",
                            "minimum": 200,
                            "maximum": 599,
                            "title": "Status code",
                        },
                    }
                ],
                "responses": {"200": {"description": "The requested status."}},
            }
        },
    },
}

OPERATIONS = {
    "GET /get": ("/get", "get"),
    "POST /post": ("/post", "post"),
    "GET /status/{code}": ("/status/{code}", "get"),
}

form = OpenAPIForm(SPEC, base_url="https://httpbin.org", path="/get", method="get")

selector = pmui.RadioButtonGroup(
    label="Operation",
    options=list(OPERATIONS),
    orientation="vertical",
    sizing_mode="stretch_width",
)

def _select_operation(label: str) -> None:
    path, method = OPERATIONS[label]
    form.param.update(path=path, method=method)


pn.bind(_select_operation, selector, watch=True)

pmui.Page(
    title="httpbin explorer",
    # form.form and form.response are placed independently rather than using
    # the default side-by-side rendering of the form itself.
    sidebar=[selector, pmui.Divider(), form.form],
    main=[
        pmui.Column(
            # Typography accepts a reference, so the heading tracks the operation.
            pmui.Typography(form.param.title, variant="h6"),
            form.response,
            margin=10,
            sizing_mode="stretch_width",
        )
    ],
    sidebar_width=360,
).servable()
