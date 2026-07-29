"""Send credentials, and swap them at runtime."""

import panel as pn
import panel_material_ui as pmui

from panel_openapi import OpenAPIForm

pn.extension()

SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "GitHub search", "version": "1.0.0"},
    "paths": {
        "/search/repositories": {
            "get": {
                "summary": "Search repositories",
                "parameters": [
                    {
                        "name": "q",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "string", "default": "panel holoviz"},
                        "description": "Search query.",
                    },
                    {
                        "name": "per_page",
                        "in": "query",
                        "schema": {"type": "integer", "minimum": 1, "maximum": 100},
                    },
                ],
                "responses": {"200": {"description": "Matching repositories."}},
            }
        }
    },
}

# The headers dict is read on every submit, so mutating it swaps credentials
# without rebuilding the form.
headers = {"Accept": "application/vnd.github+json"}

form = OpenAPIForm(
    SPEC,
    base_url="https://api.github.com",
    path="/search/repositories",
    method="get",
    headers=headers,
)

token = pmui.PasswordInput(
    label="GitHub token",
    description="Optional. Raises the rate limit. Only ever sent to api.github.com.",
    sizing_mode="stretch_width",
)


def apply_token(event):
    if event.new:
        headers["Authorization"] = f"Bearer {event.new}"
    else:
        headers.pop("Authorization", None)


token.param.watch(apply_token, "value")

pmui.Column(token, form, sizing_mode="stretch_width").servable(title="Authentication")
