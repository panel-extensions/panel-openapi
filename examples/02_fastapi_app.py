"""Drive a live FastAPI app with a generated form.

FastAPI derives an OpenAPI document from your pydantic models, so
``OpenAPIForm`` can build a working client for an endpoint with no extra
schema authoring. Here the API and the Panel form are served from the same
process, so submitting the form really does create records.

Run with::

    python examples/02_fastapi_app.py

then open http://localhost:8000/form. ``fastapi run examples/02_fastapi_app.py``
works too, on whatever port it picks: the base URL is read off the request.
"""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Literal

import panel as pn
import panel_material_ui as pmui
import uvicorn
from fastapi import FastAPI, Header, HTTPException, Query
from panel.io.fastapi import add_application
from pydantic import BaseModel, Field

from panel_openapi import OpenAPIForm

# --------------------------------------------------------------------------- #
# The API
# --------------------------------------------------------------------------- #


class Task(BaseModel):
    """A unit of work. Every field maps to a widget in the generated form."""

    title: str = Field(..., description="Short summary of the work.")
    priority: Literal["low", "medium", "high"] = Field("medium", description="How urgent this is.")
    estimate_hours: float = Field(4.0, ge=0.0, le=40.0, description="Expected effort.")
    due: dt.date | None = Field(None, description="Optional deadline.")
    blocked: bool = Field(False, description="Whether the task is currently blocked.")
    labels: list[str] = Field(default_factory=list, description="Free-form labels.")


api = FastAPI(title="Task tracker", version="1.0.0")

TASKS: list[dict] = []
API_KEY = "let-me-in"


@api.get("/tasks", summary="List tasks")
async def list_tasks(
    priority: Annotated[
        Literal["low", "medium", "high"] | None, Query(description="Filter by priority.")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum number of results.")] = 20,
) -> list[dict]:
    """Return the stored tasks, optionally filtered by priority."""
    matches = [t for t in TASKS if priority is None or t["priority"] == priority]
    return matches[:limit]


@api.post("/tasks", summary="Create a task")
async def create_task(
    task: Task,
    x_api_key: Annotated[str, Header(description="Send 'let-me-in' to authenticate.")] = "",
) -> dict:
    """Store a task. Demonstrates a header parameter alongside a JSON body."""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Bad or missing X-API-Key header.")
    record = {"id": len(TASKS) + 1, **task.model_dump(mode="json")}
    TASKS.append(record)
    return record


# --------------------------------------------------------------------------- #
# The generated forms
# --------------------------------------------------------------------------- #

def base_url() -> str:
    """The origin this page was served from, whatever port that turned out to be.

    Hardcoding a port breaks as soon as the app is started another way, e.g.
    ``fastapi run``, which defaults to 8000.
    """
    location = pn.state.location
    return f"{location.protocol}//{location.hostname}:{location.port}"


@add_application("/form", app=api, title="Task tracker client")
def form_app():
    """Build a tabbed client with one generated form per operation."""
    # OpenAPIForm also accepts a URL (see 03_remote_spec.py), but fetching
    # "/openapi.json" here would mean this app requesting a page from the very
    # server that is rendering it. api.openapi() builds the same document from
    # the pydantic models in-process, no request involved, and caches it.
    spec = api.openapi()

    url = base_url()
    create = OpenAPIForm(spec, base_url=url, path="/tasks", method="post")
    listing = OpenAPIForm(spec, base_url=url, path="/tasks", method="get")

    return pmui.Page(
        title="Task tracker client",
        main=[
            pmui.Tabs(
                ("Create", create),
                ("List", listing),
                dynamic=True,
                sizing_mode="stretch_width",
            )
        ],
    )


if __name__ == "__main__":
    uvicorn.run(api, port=8000)
