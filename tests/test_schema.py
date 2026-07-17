"""Tests for panel_openapi.schema."""

import pytest

from panel_openapi.schema import (
    collect_fields,
    get_operation,
    load_openapi,
    resolve_ref,
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
