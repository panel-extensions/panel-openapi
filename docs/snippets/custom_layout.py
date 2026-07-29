"""Lay out the form and its response wherever you want them."""

import panel as pn
import panel_material_ui as pmui

from panel_openapi import OpenAPIForm

pn.extension()

SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "echo", "version": "1.0.0"},
    "paths": {
        "/post": {
            "post": {
                "summary": "Send a message",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["message"],
                                "properties": {
                                    "message": {"type": "string"},
                                    "urgency": {
                                        "type": "string",
                                        "enum": ["low", "normal", "high"],
                                        "default": "normal",
                                    },
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

form = OpenAPIForm(SPEC, base_url="https://postman-echo.com", path="/post", method="post")

# form and response are plain Columns, so they can go anywhere in a layout.
pmui.Page(
    title="Custom layout",
    sidebar=[pmui.Typography(form.param.title, variant="h6"), form.form],
    main=[pmui.Typography("Response", variant="h6"), form.response],
    sidebar_width=340,
).servable()
