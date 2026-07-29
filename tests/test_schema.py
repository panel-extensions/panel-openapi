"""Tests for panel_openapi.schema."""

import pytest

from panel_openapi.schema import (
    collect_fields,
    find_update_operations,
    get_operation,
    load_openapi,
    resolve_ref,
    response_schema,
)


def test_load_openapi_from_dict(petstore_spec):
    api = load_openapi(petstore_spec)
    assert api.info.title == "Petstore"
    assert "/pets/{petId}" in api.paths


def test_load_openapi_passthrough(petstore_spec):
    api = load_openapi(petstore_spec)
    assert load_openapi(api) is api


def test_get_operation(petstore_spec):
    api = load_openapi(petstore_spec)
    op = get_operation(api, "/pets/{petId}", "get")
    assert op.operationId == "getPet"


def test_get_operation_case_insensitive(petstore_spec):
    api = load_openapi(petstore_spec)
    assert get_operation(api, "/pets/{petId}", "GET").operationId == "getPet"


def test_get_operation_unknown_path(petstore_spec):
    api = load_openapi(petstore_spec)
    with pytest.raises(KeyError, match="not found"):
        get_operation(api, "/missing", "get")


def test_get_operation_unknown_method(petstore_spec):
    api = load_openapi(petstore_spec)
    with pytest.raises(KeyError, match="not defined"):
        get_operation(api, "/pets/{petId}", "delete")


def test_collect_fields_parameters(petstore_spec):
    api = load_openapi(petstore_spec)
    fields = collect_fields(api, get_operation(api, "/pets/{petId}", "get"))
    by_name = {f.name: f for f in fields}
    assert by_name["petId"].location == "path"
    assert by_name["petId"].required
    assert by_name["verbose"].location == "query"
    assert not by_name["verbose"].required


def test_collect_fields_body_expands_ref(petstore_spec):
    api = load_openapi(petstore_spec)
    fields = collect_fields(api, get_operation(api, "/pets/{petId}", "post"))
    by_name = {f.name: f for f in fields}
    assert set(by_name) == {"name", "status", "tags", "age"}
    assert all(f.location == "body" for f in fields)
    assert by_name["name"].required
    assert not by_name["age"].required
    # The $ref to the enum property should be resolved to concrete options.
    assert by_name["status"].schema.enum == ["available", "pending", "sold"]


def test_resolve_ref_non_reference_passthrough(petstore_spec):
    api = load_openapi(petstore_spec)
    schema = api.components.schemas["Pet"]
    assert resolve_ref(api, schema) is schema


def test_response_schema(record_spec):
    api = load_openapi(record_spec)
    schema = response_schema(api, get_operation(api, "/tasks/{taskId}", "get"))
    assert set(schema.properties) == {"id", "title", "done", "notes"}


def test_response_schema_missing(petstore_spec):
    api = load_openapi(petstore_spec)
    # The petstore fixture declares a 200 without any content.
    assert response_schema(api, get_operation(api, "/pets/{petId}", "get")) is None


def test_find_update_operations_prefers_patch(record_spec):
    api = load_openapi(record_spec)
    assert find_update_operations(api, "/tasks/{taskId}") == ["patch", "put"]


def test_find_update_operations_none(record_spec):
    api = load_openapi(record_spec)
    assert find_update_operations(api, "/notes/{noteId}") == []
    assert find_update_operations(api, "/unknown") == []


def test_collect_fields_flags_read_only(record_spec):
    api = load_openapi(record_spec)
    fields = collect_fields(api, get_operation(api, "/tasks/{taskId}", "patch"))
    read_only = {f.name: f.read_only for f in fields}
    assert read_only == {"taskId": False, "id": True, "title": False, "done": False, "notes": False}


def test_collect_fields_skip_read_only(record_spec):
    api = load_openapi(record_spec)
    fields = collect_fields(
        api, get_operation(api, "/tasks/{taskId}", "patch"), skip_read_only=True
    )
    assert "id" not in [f.name for f in fields]


PATH_LEVEL_PARAM_SPEC = {
    "openapi": "3.0.0",
    "info": {"title": "shared", "version": "1"},
    "paths": {
        "/things/{thingId}": {
            "parameters": [
                {
                    "name": "thingId",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "integer"},
                }
            ],
            "get": {
                "parameters": [
                    {"name": "verbose", "in": "query", "schema": {"type": "boolean"}}
                ],
                "responses": {"200": {"description": "ok"}},
            },
            "delete": {"responses": {"204": {"description": "gone"}}},
        }
    },
}


def test_path_level_parameters_are_inherited():
    openapi = load_openapi(PATH_LEVEL_PARAM_SPEC)
    operation = get_operation(openapi, "/things/{thingId}", "get")
    fields = collect_fields(openapi, operation)
    assert [(f.name, f.location) for f in fields] == [
        ("thingId", "path"),
        ("verbose", "query"),
    ]


def test_path_level_parameters_reach_operations_without_own():
    openapi = load_openapi(PATH_LEVEL_PARAM_SPEC)
    operation = get_operation(openapi, "/things/{thingId}", "delete")
    assert [f.name for f in collect_fields(openapi, operation)] == ["thingId"]


def test_operation_parameter_overrides_path_level():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "override", "version": "1"},
        "paths": {
            "/things/{thingId}": {
                "parameters": [
                    {
                        "name": "thingId",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                    }
                ],
                "get": {
                    "parameters": [
                        {
                            "name": "thingId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "The more specific one wins.",
                        }
                    ],
                    "responses": {"200": {"description": "ok"}},
                },
            }
        },
    }
    openapi = load_openapi(spec)
    fields = collect_fields(openapi, get_operation(openapi, "/things/{thingId}", "get"))
    assert len(fields) == 1
    assert fields[0].schema.type == "string"


def test_merge_does_not_mutate_document():
    openapi = load_openapi(PATH_LEVEL_PARAM_SPEC)
    get_operation(openapi, "/things/{thingId}", "get")
    original = openapi.paths["/things/{thingId}"].get
    # The merge returns a copy, so a second lookup cannot accumulate duplicates.
    assert [p.name for p in original.parameters] == ["verbose"]


def test_parameter_description_reaches_the_schema():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "described", "version": "1"},
        "paths": {
            "/x": {
                "get": {
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "schema": {"type": "string"},
                            "description": "What to search for.",
                        }
                    ],
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
    }
    openapi = load_openapi(spec)
    fields = collect_fields(openapi, get_operation(openapi, "/x", "get"))
    # OpenAPI documents a parameter on the parameter, not on its schema.
    assert fields[0].schema.description == "What to search for."
