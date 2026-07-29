"""Holds fixtures and configuration for the test suite."""

import pytest
from panel.config import panel_extension
from panel.io.reload import _local_modules
from panel.io.reload import _modules
from panel.io.reload import _watched_files
from panel.io.state import state
from panel.theme import Design

optional_markers = {
    "ui": {
        "help": "Runs UI related tests",
        "marker-descr": "UI test marker",
        "skip-reason": "Test only runs with the --ui option.",
    },
}


def pytest_addoption(parser):
    """Add extra command line options."""
    for marker, info in optional_markers.items():
        parser.addoption(f"--{marker}", action="store_true", default=False, help=info["help"])
    parser.addoption("--repeat", action="store", help="Number of times to repeat each test")


def pytest_configure(config):
    """Add extra markers."""
    for marker, info in optional_markers.items():
        config.addinivalue_line("markers", "{}: {}".format(marker, info["marker-descr"]))

    config.addinivalue_line("markers", "internet: mark test as requiring an internet connection")


@pytest.fixture
def petstore_spec():
    """A small petstore-style OpenAPI 3.0 specification."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Petstore", "version": "1.0.0"},
        "paths": {
            "/pets/{petId}": {
                "get": {
                    "summary": "Get a pet",
                    "operationId": "getPet",
                    "parameters": [
                        {
                            "name": "petId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer", "minimum": 1, "maximum": 100},
                        },
                        {
                            "name": "verbose",
                            "in": "query",
                            "schema": {"type": "boolean", "default": False},
                        },
                    ],
                    "responses": {"200": {"description": "ok"}},
                },
                "post": {
                    "operationId": "createPet",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Pet"}}},
                    },
                    "responses": {"200": {"description": "ok"}},
                },
            }
        },
        "components": {
            "schemas": {
                "Pet": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {
                        "name": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": ["available", "pending", "sold"],
                        },
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "age": {"type": "integer"},
                    },
                }
            }
        },
    }


@pytest.fixture
def record_spec():
    """A spec with a readable record and both PATCH and PUT updates."""
    task = {
        "type": "object",
        "required": ["title"],
        "properties": {
            "id": {"type": "integer", "readOnly": True},
            "title": {"type": "string"},
            "done": {"type": "boolean"},
            "notes": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        },
    }
    operation = {
        "parameters": [
            {
                "name": "taskId",
                "in": "path",
                "required": True,
                "schema": {"type": "integer"},
            }
        ],
        "responses": {
            "200": {
                "description": "ok",
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Task"}}},
            }
        },
    }
    body = {
        "requestBody": {
            "required": True,
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Task"}}},
        }
    }
    return {
        # 3.1, since `anyOf` with a null branch is how pydantic and FastAPI
        # express an optional field and is invalid in 3.0.
        "openapi": "3.1.0",
        "info": {"title": "Tasks", "version": "1.0.0"},
        "paths": {
            "/tasks/{taskId}": {
                "get": {"summary": "Get a task", **operation},
                "patch": {"summary": "Patch a task", **operation, **body},
                "put": {"summary": "Replace a task", **operation, **body},
            },
            "/notes/{noteId}": {
                "get": {"summary": "Get a note", **operation},
            },
        },
        "components": {"schemas": {"Task": task}},
    }


@pytest.fixture(autouse=True)
def module_cleanup():
    """Cleanup Panel extensions after each test."""
    from bokeh.core.has_props import _default_resolver
    from panel.reactive import ReactiveMetaBase

    to_reset = list(panel_extension._imports.values())
    _default_resolver._known_models = {
        name: model for name, model in _default_resolver._known_models.items() if not any(model.__module__.startswith(tr) for tr in to_reset)
    }
    ReactiveMetaBase._loaded_extensions = set()


@pytest.fixture(autouse=True)
def server_cleanup():
    """Clean up server state after each test."""
    try:
        yield
    finally:
        state.reset()
        _watched_files.clear()
        _modules.clear()
        _local_modules.clear()


@pytest.fixture(autouse=True)
def cache_cleanup():
    """Clean up cache."""
    state.clear_caches()
    Design._resolve_modifiers.cache_clear()
    Design._cache.clear()
