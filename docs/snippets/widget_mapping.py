"""One property per widget kind, to show how schemas map to widgets."""

import panel as pn

from panel_openapi import OpenAPIForm

pn.extension()

SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "Widget mapping", "version": "1.0.0"},
    "paths": {
        "/post": {
            "post": {
                "summary": "Every widget kind",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    # string -> TextInput
                                    "name": {"type": "string"},
                                    # format: password -> PasswordInput
                                    "token": {"type": "string", "format": "password"},
                                    # format: date -> DatePicker
                                    "due": {"type": "string", "format": "date"},
                                    # format: date-time -> DatetimePicker
                                    "starts_at": {"type": "string", "format": "date-time"},
                                    # enum, <= 3 options -> RadioButtonGroup
                                    "size": {"type": "string", "enum": ["s", "m", "l"]},
                                    # enum, > 3 options -> Select
                                    "colour": {
                                        "type": "string",
                                        "enum": ["red", "green", "blue", "black"],
                                    },
                                    # integer, both bounds -> IntSlider
                                    "quantity": {
                                        "type": "integer",
                                        "minimum": 1,
                                        "maximum": 10,
                                    },
                                    # number, one bound -> FloatInput
                                    "weight": {"type": "number", "minimum": 0.0},
                                    # boolean -> Checkbox
                                    "gift": {"type": "boolean"},
                                    # array of enum -> MultiChoice
                                    "tags": {
                                        "type": "array",
                                        "items": {"type": "string", "enum": ["new", "sale"]},
                                    },
                                    # object, or anything unrecognised -> JSON TextAreaInput
                                    "metadata": {"type": "object"},
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

form.form.servable(title="Widget mapping")
