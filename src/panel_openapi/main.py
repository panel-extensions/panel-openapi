"""Demo entry point for panel-openapi.

Running ``panel serve src/panel_openapi/main.py`` builds an :class:`OpenAPIForm`
for a small inline OpenAPI spec targeting `httpbin.org <https://httpbin.org>`_,
so the generated form can be submitted against a live endpoint.
"""

from .form import OpenAPIForm

DEMO_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "httpbin demo", "version": "1.0.0"},
    "paths": {
        "/anything": {
            "post": {
                "summary": "Echo a payload",
                "description": "Send a JSON payload to httpbin and see it echoed back.",
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
                                        "title": "Role",
                                    },
                                    "age": {
                                        "type": "integer",
                                        "minimum": 0,
                                        "maximum": 120,
                                        "title": "Age",
                                    },
                                    "subscribed": {"type": "boolean", "title": "Subscribed"},
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


def create_app() -> OpenAPIForm:
    """Create the demo OpenAPI form.

    Returns
    -------
    OpenAPIForm
        A form for the ``POST /anything`` httpbin endpoint.
    """
    return OpenAPIForm(
        DEMO_SPEC,
        base_url="https://httpbin.org",
        path="/anything",
        method="post",
    )


if __name__.startswith("bokeh") or __name__ == "__main__":
    create_app().servable()
