"""Generate a form from an inline OpenAPI spec.

The smallest possible example: hand ``OpenAPIForm`` a spec dictionary, a base
URL and the operation to target, and it renders one widget per parameter and
body property. Submitting issues the request and shows the response.

The spec below is annotated to show which schema constructs map to which
widget. Requests go to https://httpbin.org, which echoes them back.

Run with::

    panel serve examples/01_inline_spec.py --show
"""

import panel as pn
import panel_material_ui as pmui

from panel_openapi import OpenAPIForm

pn.extension()

SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "httpbin", "version": "1.0.0"},
    "paths": {
        "/anything": {
            "post": {
                "summary": "Register an attendee",
                "description": "Every widget below was derived from the JSON schema of the request body.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["name", "email"],
                                "properties": {
                                    # string -> TextInput
                                    "name": {
                                        "type": "string",
                                        "title": "Full name",
                                        "description": "Descriptions become widget tooltips.",
                                    },
                                    "email": {"type": "string", "title": "Email"},
                                    # string with format: password -> PasswordInput
                                    "access_code": {
                                        "type": "string",
                                        "format": "password",
                                        "title": "Access code",
                                    },
                                    # string with format: date -> DatePicker
                                    "arrival": {
                                        "type": "string",
                                        "format": "date",
                                        "title": "Arrival date",
                                    },
                                    # up to three enum values -> RadioButtonGroup
                                    "ticket": {
                                        "type": "string",
                                        "enum": ["standard", "student", "vip"],
                                        "default": "standard",
                                        "title": "Ticket type",
                                    },
                                    # more than three -> Select
                                    "track": {
                                        "type": "string",
                                        "enum": ["python", "javascript", "rust", "data", "other"],
                                        "title": "Preferred track",
                                    },
                                    # integer with both bounds -> IntSlider
                                    "years_experience": {
                                        "type": "integer",
                                        "minimum": 0,
                                        "maximum": 40,
                                        "title": "Years of experience",
                                    },
                                    # number with one bound -> FloatInput
                                    "budget": {
                                        "type": "number",
                                        "minimum": 0,
                                        "title": "Budget (USD)",
                                    },
                                    # boolean -> Checkbox
                                    "attends_dinner": {
                                        "type": "boolean",
                                        "default": True,
                                        "title": "Attending the dinner",
                                    },
                                    # array of enum values -> MultiChoice
                                    "dietary": {
                                        "type": "array",
                                        "items": {
                                            "type": "string",
                                            "enum": ["vegan", "halal", "gluten-free", "none"],
                                        },
                                        "title": "Dietary requirements",
                                    },
                                    # objects and free-form arrays -> JSON TextAreaInput
                                    "notes": {
                                        "type": "object",
                                        "title": "Extra metadata",
                                        "description": "Any JSON object.",
                                    },
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

form = OpenAPIForm(
    SPEC,
    base_url="https://httpbin.org",
    path="/anything",
    method="post",
)

pmui.Page(title=form.title, main=[form]).servable()
