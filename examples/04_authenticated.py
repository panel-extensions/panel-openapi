"""Authenticate requests and let the user supply the token.

``OpenAPIForm`` sends its ``headers`` argument with every request, which covers
bearer tokens, API keys and any other static header an API requires. Because
``headers`` is read on each submit, mutating the dict is enough to swap
credentials at runtime.

This example targets the public GitHub API. It works unauthenticated at a low
rate limit; paste a personal access token to raise it.

Run with::

    panel serve examples/04_authenticated.py --show
"""

from __future__ import annotations

import panel as pn
import panel_material_ui as pmui

from panel_openapi import OpenAPIForm

pn.extension()

# A hand-written slice of the GitHub API. Writing the spec by hand rather than
# fetching GitHub's full description keeps the example to one operation.
SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "GitHub search", "version": "1.0.0"},
    "paths": {
        "/search/repositories": {
            "get": {
                "summary": "Search repositories",
                "description": "Unauthenticated requests are limited to 10/minute. Add a token to raise that.",
                "parameters": [
                    {
                        "name": "q",
                        "in": "query",
                        "required": True,
                        "description": "A GitHub search query, e.g. 'holoviz panel'.",
                        "schema": {"type": "string", "title": "Query", "default": "holoviz panel"},
                    },
                    {
                        "name": "sort",
                        "in": "query",
                        "schema": {
                            "type": "string",
                            "enum": ["stars", "forks", "updated"],
                            "title": "Sort by",
                        },
                    },
                    {
                        "name": "order",
                        "in": "query",
                        "schema": {"type": "string", "enum": ["desc", "asc"], "title": "Order"},
                    },
                    {
                        "name": "per_page",
                        "in": "query",
                        "schema": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 100,
                            "title": "Results per page",
                        },
                    },
                ],
                "responses": {"200": {"description": "Matching repositories."}},
            }
        }
    },
}

# The dict handed to OpenAPIForm is stored by reference on the form, so updating
# it in place changes the headers used by subsequent submits.
headers = {"Accept": "application/vnd.github+json"}

form = OpenAPIForm(
    SPEC,
    base_url="https://api.github.com",
    path="/search/repositories",
    method="get",
    headers=headers,
)

token_input = pmui.PasswordInput(
    label="GitHub token",
    description="Optional. Stays in this browser session and is only sent to api.github.com.",
    placeholder="ghp_...",
    sizing_mode="stretch_width",
)


def _apply_token(value: str) -> pmui.Alert | None:
    if value:
        headers["Authorization"] = f"Bearer {value}"
        return pmui.Alert(object="Requests are authenticated.", severity="success")
    headers.pop("Authorization", None)
    return pmui.Alert(object="Requests are anonymous (10/minute).", severity="info")


pmui.Page(
    title="GitHub repository search",
    main=[
        pmui.Column(
            token_input,
            pn.bind(_apply_token, token_input),
            pmui.Divider(),
            form,
            sizing_mode="stretch_width",
        )
    ],
).servable()
