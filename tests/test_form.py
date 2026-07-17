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
    names = [field.name for field, _ in form._widgets]
    assert names == ["petId", "verbose"]
    assert form.title == "Get a pet"


def test_build_request_substitutes_path(petstore_spec):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "get")
    form._widgets[0][1].value = 7  # petId
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
    widgets = {field.name: widget for field, widget in form._widgets}
    widgets["name"].value = "Rex"
    widgets["tags"].value = '["a", "b"]'
    grouped, missing = form._collect_values()
    request = form._build_request(grouped)
    assert missing == []
    assert request["json"]["name"] == "Rex"
    assert request["json"]["tags"] == ["a", "b"]


def test_invalid_json_body_raises(petstore_spec):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "post")
    widgets = {field.name: widget for field, widget in form._widgets}
    widgets["name"].value = "Rex"
    widgets["tags"].value = "not json"
    with pytest.raises(ValueError, match="valid JSON"):
        form._collect_values()


async def test_submit_success(petstore_spec, mock_transport):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "get")
    form._widgets[0][1].value = 5
    await form._submit()
    assert mock_transport["request"].url.path == "/pets/5"
    assert isinstance(form._response[0], pmui.Alert)
    assert form._response[0].severity == "success"


async def test_submit_missing_required(petstore_spec):
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "post")
    await form._submit()
    assert isinstance(form._response[0], pmui.Alert)
    assert form._response[0].severity == "warning"
    assert "name" in form._response[0].object
