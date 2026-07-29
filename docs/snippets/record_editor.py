"""Look up a record, edit it, and send the changes back."""

import panel as pn
import panel_material_ui as pmui

from panel_openapi import OpenAPIRecordEditor

pn.extension()

SPEC = {
    "openapi": "3.1.0",
    "info": {"title": "Articles", "version": "1.0.0"},
    "paths": {
        "/articles/{article_id}": {
            "parameters": [
                {
                    "name": "article_id",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                }
            ],
            "get": {
                "summary": "Get an article",
                "responses": {
                    "200": {
                        "description": "The article.",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Article"}}},
                    }
                },
            },
            "patch": {
                "summary": "Update an article",
                "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/Article"}}}},
                "responses": {"200": {"description": "The updated article."}},
            },
        }
    },
    "components": {
        "schemas": {
            "Article": {
                "type": "object",
                "properties": {
                    # readOnly fields are shown disabled and never sent.
                    "id": {"type": "integer", "readOnly": True},
                    "created": {"type": "string", "format": "date", "readOnly": True},
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "published": {"type": "boolean"},
                    "views": {"type": "integer", "minimum": 0},
                },
            }
        }
    },
}

editor = OpenAPIRecordEditor(
    SPEC,
    base_url="https://api.example.com",
    path="/articles/{article_id}",
    # PATCH is picked automatically; pass update_method to override.
    confirm=True,
)
editor.lookup.widgets["article_id"].value = 1

# Normally you would click Load; this stands in for a live server.
editor.populate(
    {
        "id": 1,
        "created": "2026-01-15",
        "title": "Generating forms from OpenAPI",
        "body": "A schema is a user interface waiting to happen.",
        "published": False,
        "views": 12,
    }
)

pmui.Column(editor, sizing_mode="stretch_width").servable(title="Record editor")
