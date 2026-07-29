"""Quickstart: a form for one operation of an inline spec."""

import panel as pn

from panel_openapi import OpenAPIForm

pn.extension()

SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "echo demo", "version": "1.0.0"},
    "paths": {
        "/post": {
            "post": {
                "summary": "Create a user",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["name"],
                                "properties": {
                                    "name": {"type": "string", "title": "Name"},
                                    "role": {
                                        "type": "string",
                                        "enum": ["admin", "user", "guest"],
                                        "default": "user",
                                    },
                                    "age": {"type": "integer", "minimum": 0, "maximum": 120},
                                    "subscribed": {"type": "boolean", "default": True},
                                },
                            }
                        }
                    },
                },
                "responses": {"200": {"description": "The echoed request."}},
            }
        }
    },
}

form = OpenAPIForm(SPEC, base_url="https://postman-echo.com", path="/post", method="post")

form.servable(title="Quickstart")
