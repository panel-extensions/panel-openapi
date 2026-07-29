"""Tests for panel_openapi.form."""

import httpx
import panel_material_ui as pmui
import pytest

from panel_openapi.form import OpenAPIForm


@pytest.fixture
def mock_transport(monkeypatch):
    """Patch httpx.AsyncClient to route requests through a recording handler."""
    captured = {}

    def handler(request):
        captured["request"] = request
        return httpx.Response(200, json={"echo": request.url.path})

    original = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)
    return captured


def test_form_builds_widgets(petstore_spec):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "get")
    names = list(form.widgets)
    assert names == ["petId", "verbose"]
    assert form.title == "Get a pet"


def test_build_request_substitutes_path(petstore_spec):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "get")
    form.widgets["petId"].value = 7
    grouped, missing = form._collect_values()
    request = form._build_request(grouped)
    assert missing == []
    assert request["url"] == "https://api.example.com/pets/7"
    assert request["method"] == "GET"


def test_headers_merged(petstore_spec):
    form = OpenAPIForm(
        petstore_spec,
        "https://api.example.com",
        "/pets/{petId}",
        "get",
        headers={"Authorization": "Bearer token"},
    )
    grouped, _ = form._collect_values()
    request = form._build_request(grouped)
    assert request["headers"]["Authorization"] == "Bearer token"


def test_body_json_assembled(petstore_spec):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "post")
    widgets = form.widgets
    widgets["name"].value = "Rex"
    widgets["tags"].value = '["a", "b"]'
    grouped, missing = form._collect_values()
    request = form._build_request(grouped)
    assert missing == []
    assert request["json"]["name"] == "Rex"
    assert request["json"]["tags"] == ["a", "b"]


def test_invalid_json_body_raises(petstore_spec):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "post")
    widgets = form.widgets
    widgets["name"].value = "Rex"
    widgets["tags"].value = "not json"
    with pytest.raises(ValueError, match="valid JSON"):
        form._collect_values()


async def test_submit_success(petstore_spec, mock_transport):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "get")
    form.widgets["petId"].value = 5
    await form._submit()
    assert mock_transport["request"].url.path == "/pets/5"
    assert isinstance(form.response[0], pmui.Alert)
    assert form.response[0].severity == "success"


async def test_submit_missing_required(petstore_spec):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "post")
    await form._submit()
    assert isinstance(form.response[0], pmui.Alert)
    assert form.response[0].severity == "warning"
    assert "name" in form.response[0].object


def test_method_change_rebuilds_widgets(petstore_spec):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "get")
    container = form.form
    assert list(form.widgets) == ["petId", "verbose"]

    form.method = "post"

    assert list(form.widgets) == ["name", "status", "tags", "age"]
    assert form.title == "createPet"
    # The container is mutated in place so existing layouts keep working.
    assert form.form is container


def test_title_derived_from_operation(petstore_spec):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "get")
    assert form.title == "Get a pet"
    form.method = "post"
    assert form.title == "createPet"


def test_explicit_title_survives_operation_change(petstore_spec):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "get", title="Fixed")
    form.method = "post"
    assert form.title == "Fixed"


def test_rebuild_clears_previous_response(petstore_spec, mock_transport):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "get")
    form.widgets["petId"].value = 5
    form.response[:] = [pmui.Alert(object="stale", severity="info")]

    form.method = "post"

    assert len(form.response) == 0


def test_unknown_path_reports_error(petstore_spec):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "get")

    form.path = "/nope"

    assert isinstance(form.form[0], pmui.Alert)
    assert form.form[0].severity == "error"
    assert form.widgets == {}


def test_batched_update_rebuilds_once(petstore_spec):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "get")
    calls = []
    form.param.watch(lambda event: calls.append(event), ["path", "method"])

    form.param.update(path="/pets/{petId}", method="post")

    assert len(calls) == 1
    assert list(form.widgets) == ["name", "status", "tags", "age"]


def test_recovers_after_unknown_path(petstore_spec):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "get")
    form.path = "/nope"

    form.path = "/pets/{petId}"

    assert list(form.widgets) == ["petId", "verbose"]


def test_base_url_change_redirects_request(petstore_spec, mock_transport):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "get")
    form.widgets["petId"].value = 5
    form.base_url = "https://other.example.com"
    grouped, _ = form._collect_values()
    assert form._build_request(grouped)["url"] == "https://other.example.com/pets/5"


def test_values_excludes_empty_and_parses_json(petstore_spec):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "post")
    form.widgets["name"].value = "Rex"
    form.widgets["tags"].value = '["a"]'
    values = form.values
    assert values["name"] == "Rex"
    # The text area holds serialized JSON but values returns it parsed.
    assert values["tags"] == ["a"]


def test_values_omits_empty_text(petstore_spec):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "post")
    # name is an untouched TextInput and tags an untouched text area.
    assert "name" not in form.values
    assert "tags" not in form.values


def test_get_values_by_location(petstore_spec):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "get")
    form.widgets["petId"].value = 3
    assert form.get_values("path") == {"petId": 3}
    assert form.get_values("body") == {}


def test_populate_sets_values(petstore_spec):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "post")
    skipped = form.populate({"name": "Rex", "status": "sold", "tags": ["a", "b"]})
    assert skipped == []
    assert form.widgets["name"].value == "Rex"
    # JSON fields are serialized back into their text area.
    assert form.values["tags"] == ["a", "b"]


def test_populate_reports_unknown_keys(petstore_spec):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "post")
    assert form.populate({"name": "Rex", "nope": 1, "other": 2}) == ["nope", "other"]


def test_populate_coerces_datetime():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "t", "version": "1"},
        "paths": {
            "/x": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"at": {"type": "string", "format": "date-time"}},
                                }
                            }
                        }
                    },
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
    }
    form = OpenAPIForm(spec, "https://api.example.com", "/x", "post")
    # The datetime picker rejects ISO strings, so populate must parse them.
    assert form.populate({"at": "2026-07-29T10:30:00Z"}) == []
    assert form.widgets["at"].value.year == 2026
