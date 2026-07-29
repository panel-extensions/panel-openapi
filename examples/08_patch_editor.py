"""Edit a record with PATCH, sending only what changed.

When the update operation is a ``PATCH``, the editor sends just the fields whose
value differs from the loaded record, matching the convention that omitted keys
are left alone. This example runs a FastAPI app that records every body it
receives, so you can see exactly what went over the wire.

It also shows ``readOnly`` handling: ``id`` and ``created`` come back from the
server and are displayed disabled, but are never sent. And ``confirm=True``
puts a dialog listing the pending changes in front of the save.

Run with::

    python examples/08_patch_editor.py

then open http://localhost:8001/editor. ``fastapi run examples/08_patch_editor.py``
works too, on whatever port it picks: the base URL is read off the request.
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Annotated

import panel as pn
import panel_material_ui as pmui
import uvicorn
from fastapi import Body, FastAPI, HTTPException
from panel.io.fastapi import add_application
from pydantic import BaseModel, Field

from panel_openapi import OpenAPIRecordEditor

# --------------------------------------------------------------------------- #
# The API
# --------------------------------------------------------------------------- #


class Article(BaseModel):
    """The stored record. Server-assigned fields are marked read-only."""

    id: int = Field(..., json_schema_extra={"readOnly": True})
    created: dt.date = Field(..., json_schema_extra={"readOnly": True})
    title: str
    body: str
    published: bool
    views: int = Field(0, ge=0)


class ArticlePatch(BaseModel):
    """A partial update. Every field is optional, so omitting one leaves it be.

    ``id`` and ``created`` are declared but marked ``readOnly``, which is how a
    schema says "you will see this, but you cannot set it". The editor shows them
    disabled and leaves them out of the request body.
    """

    id: int | None = Field(None, json_schema_extra={"readOnly": True})
    created: dt.date | None = Field(None, json_schema_extra={"readOnly": True})
    title: str | None = None
    body: str | None = None
    published: bool | None = None
    views: int | None = Field(None, ge=0)


api = FastAPI(title="Articles", version="1.0.0")

ARTICLES: dict[int, dict] = {
    1: {
        "id": 1,
        "created": "2026-01-15",
        "title": "Generating forms from OpenAPI",
        "body": "A schema is a user interface waiting to happen.",
        "published": False,
        "views": 0,
    }
}

# Every PATCH body the API receives, newest last, so the app can display them.
RECEIVED: list[dict] = []


@api.get("/articles/{article_id}", summary="Get an article", response_model=Article)
async def get_article(article_id: int) -> dict:
    """Return a stored article."""
    if article_id not in ARTICLES:
        raise HTTPException(status_code=404, detail=f"No article {article_id}.")
    return ARTICLES[article_id]


@api.patch("/articles/{article_id}", summary="Update an article", response_model=Article)
async def patch_article(
    article_id: int,
    patch: Annotated[ArticlePatch, Body()],
) -> dict:
    """Apply a partial update, touching only the fields that were sent."""
    if article_id not in ARTICLES:
        raise HTTPException(status_code=404, detail=f"No article {article_id}.")
    # exclude_unset is what makes this a real PATCH: absent keys are untouched.
    changes = patch.model_dump(exclude_unset=True, mode="json")
    # The editor never sends these, so seeing one means something is wrong.
    for read_only in ("id", "created"):
        if read_only in changes:
            raise HTTPException(status_code=400, detail=f"{read_only} is read-only.")
    RECEIVED.append(changes)
    ARTICLES[article_id].update(changes)
    return ARTICLES[article_id]


# --------------------------------------------------------------------------- #
# The editor
# --------------------------------------------------------------------------- #


def base_url() -> str:
    """The origin this page was served from, whatever port that turned out to be.

    Hardcoding a port breaks as soon as the app is started another way, e.g.
    ``fastapi run``, which defaults to 8000.
    """
    location = pn.state.location
    return f"{location.protocol}//{location.hostname}:{location.port}"


@add_application("/editor", app=api, title="Article editor")
def editor_app():
    """Build an editor for the article endpoints."""
    editor = OpenAPIRecordEditor(
        api.openapi(),
        base_url=base_url(),
        path="/articles/{article_id}",
        confirm=True,
    )
    # An untouched int input sits at 0, and there is no article 0, so start the
    # lookup on the one record this demo ships with.
    editor.lookup.widgets["article_id"].value = 1

    sent = pmui.Column(sizing_mode="stretch_width")

    def _show_sent(record: dict | None) -> pmui.Column:
        """Show the PATCH bodies the API has received."""
        if not RECEIVED:
            return pmui.Typography(
                "Nothing sent yet. Load article 1, change a field and save.",
                variant="body2",
            )
        return pmui.Column(
            *[
                pmui.Typography(f"`{json.dumps(body)}`", variant="body2")
                for body in reversed(RECEIVED)
            ]
        )

    sent[:] = [pn.bind(_show_sent, editor.param.record)]

    return pmui.Page(
        title="Article editor",
        main=[
            pmui.Column(
                pmui.Alert(
                    object=(
                        "`id` and `created` are readOnly: shown disabled, never sent. "
                        "Only edited fields go in the PATCH body."
                    ),
                    severity="info",
                ),
                editor,
                pmui.Divider(),
                pmui.Typography("PATCH bodies received", variant="subtitle2"),
                sent,
                margin=10,
                sizing_mode="stretch_width",
            )
        ],
    )


if __name__ == "__main__":
    uvicorn.run(api, port=8001)
