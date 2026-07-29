"""Tests for panel_openapi.editor."""

import json

import httpx
import panel_material_ui as pmui
import pytest

from panel_openapi.editor import OpenAPIRecordEditor

RECORD = {"id": 1, "title": "Original", "done": False, "notes": "keep me"}


@pytest.fixture
def api(monkeypatch):
    """Route requests to an in-memory record, recording what was sent."""
    state = {"record": dict(RECORD), "requests": []}

    def handler(request):
        state["requests"].append(request)
        if request.method == "GET":
            return httpx.Response(200, json=state["record"])
        sent = json.loads(request.content) if request.content else {}
        state["record"].update(sent)
        return httpx.Response(200, json=state["record"])

    original = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)
    return state


def make_editor(record_spec, **kwargs):
    return OpenAPIRecordEditor(
        record_spec, base_url="https://api.example.com", path="/tasks/{taskId}", **kwargs
    )


def test_auto_detects_patch(record_spec):
    editor = make_editor(record_spec)
    assert editor.update_method == "patch"
    assert list(editor.lookup.widgets) == ["taskId"]


def test_explicit_update_method(record_spec):
    editor = make_editor(record_spec, update_method="put")
    assert editor.update_method == "put"


def test_no_update_operation(record_spec):
    editor = OpenAPIRecordEditor(
        record_spec, base_url="https://api.example.com", path="/notes/{noteId}"
    )
    assert editor.update_method is None
    assert editor.editor is None


def test_read_only_field_disabled(record_spec):
    editor = make_editor(record_spec)
    assert editor.editor.widgets["id"].disabled is True
    assert editor.editor.widgets["title"].disabled is False


def test_save_disabled_until_loaded(record_spec):
    editor = make_editor(record_spec)
    assert editor.editor._submit_button.disabled is True
    editor.populate(RECORD)
    assert editor.editor._submit_button.disabled is False


def test_populate_sets_record_and_widgets(record_spec):
    editor = make_editor(record_spec)
    editor.populate(RECORD)
    assert editor.loaded
    assert editor.editor.widgets["title"].value == "Original"
    # Read-only values are shown even though they are never sent.
    assert editor.editor.widgets["id"].value == 1
    assert "id" not in editor.editor.values


def test_diff_empty_then_tracks_edits(record_spec):
    editor = make_editor(record_spec)
    editor.populate(RECORD)
    assert editor.diff() == {}
    editor.editor.widgets["title"].value = "Changed"
    assert editor.diff() == {"title": ("Original", "Changed")}


async def test_load_populates_from_response(record_spec, api):
    editor = make_editor(record_spec, show_lookup=False)
    record = await editor.load(taskId=1)
    assert record == RECORD
    assert editor.editor.widgets["title"].value == "Original"


async def test_load_rejects_unknown_lookup_field(record_spec, api):
    editor = make_editor(record_spec)
    with pytest.raises(ValueError, match="Unknown lookup fields"):
        await editor.load(nope=1)


async def test_patch_sends_only_changed_fields(record_spec, api):
    editor = make_editor(record_spec, show_lookup=False)
    await editor.load(taskId=1)
    editor.editor.widgets["title"].value = "Changed"

    saved = await editor.save()

    sent = json.loads(api["requests"][-1].content)
    assert sent == {"title": "Changed"}
    # The server's version becomes the new baseline.
    assert saved["title"] == "Changed"
    assert saved["notes"] == "keep me"
    assert editor.record["title"] == "Changed"
    assert editor.diff() == {}


async def test_put_sends_full_body(record_spec, api):
    editor = make_editor(record_spec, update_method="put", show_lookup=False)
    await editor.load(taskId=1)
    editor.editor.widgets["title"].value = "Changed"

    await editor.save()

    sent = json.loads(api["requests"][-1].content)
    # A full replace sends every editable field, changed or not.
    assert sent == {"title": "Changed", "done": False, "notes": "keep me"}
    # ...but never the read-only one.
    assert "id" not in sent


async def test_save_without_changes_is_noop(record_spec, api):
    editor = make_editor(record_spec, show_lookup=False)
    await editor.load(taskId=1)
    before = len(api["requests"])

    assert await editor.save() is None
    assert len(api["requests"]) == before


async def test_save_reuses_lookup_path_parameter(record_spec, api):
    editor = make_editor(record_spec, show_lookup=False)
    await editor.load(taskId=7)
    editor.editor.widgets["title"].value = "Changed"

    await editor.save()

    assert api["requests"][-1].url.path == "/tasks/7"


async def test_load_failure_reports(record_spec, monkeypatch):
    def handler(request):
        return httpx.Response(404, json={"detail": "nope"})

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *a, **kw: original(*a, **{**kw, "transport": httpx.MockTransport(handler)}),
    )

    editor = make_editor(record_spec, show_lookup=False)
    assert await editor.load(taskId=1) is None
    assert not editor.loaded
    assert editor._status[0].severity == "error"


async def test_non_object_response_reports(record_spec, monkeypatch):
    def handler(request):
        return httpx.Response(200, json=[1, 2, 3])

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *a, **kw: original(*a, **{**kw, "transport": httpx.MockTransport(handler)}),
    )

    editor = make_editor(record_spec, show_lookup=False)
    assert await editor.load(taskId=1) is None
    assert "JSON object" in editor._status[0].object


async def test_save_without_update_operation_raises(record_spec):
    editor = OpenAPIRecordEditor(
        record_spec, base_url="https://api.example.com", path="/notes/{noteId}"
    )
    with pytest.raises(RuntimeError, match="No update operation"):
        await editor.save()


async def test_confirm_opens_dialog_instead_of_saving(record_spec, api):
    editor = make_editor(record_spec, show_lookup=False, confirm=True)
    await editor.load(taskId=1)
    editor.editor.widgets["title"].value = "Changed"
    before = len(api["requests"])

    await editor._save_clicked()

    assert editor._dialog.open is True
    assert len(api["requests"]) == before
    rendered = " ".join(str(o.object) for o in editor._diff_pane)
    assert "title" in rendered and "Changed" in rendered


async def test_confirming_dialog_saves(record_spec, api):
    editor = make_editor(record_spec, show_lookup=False, confirm=True)
    await editor.load(taskId=1)
    editor.editor.widgets["title"].value = "Changed"
    await editor._save_clicked()

    await editor._confirmed()

    assert editor._dialog.open is False
    assert editor.record["title"] == "Changed"


async def test_cancelling_dialog_does_not_save(record_spec, api):
    editor = make_editor(record_spec, show_lookup=False, confirm=True)
    await editor.load(taskId=1)
    editor.editor.widgets["title"].value = "Changed"
    await editor._save_clicked()
    before = len(api["requests"])

    editor._cancelled()

    assert editor._dialog.open is False
    assert len(api["requests"]) == before
    assert editor.record["title"] == "Original"


async def test_confirm_with_no_changes_does_not_open(record_spec, api):
    editor = make_editor(record_spec, show_lookup=False, confirm=True)
    await editor.load(taskId=1)

    await editor._save_clicked()

    assert editor._dialog.open is False
    assert editor._status[0].object == "Nothing changed."


def test_renders(record_spec):
    editor = make_editor(record_spec)
    assert isinstance(editor.__panel__(), pmui.Column)


def test_shared_path_widget_hidden_when_lookup_shown(record_spec):
    editor = make_editor(record_spec)
    # Both operations declare taskId; only the lookup should ask for it.
    assert editor.lookup.widgets["taskId"].visible is True
    assert editor.editor.widgets["taskId"].visible is False


def test_shared_path_widget_visible_without_lookup(record_spec):
    editor = make_editor(record_spec, show_lookup=False)
    assert editor.editor.widgets["taskId"].visible is True


async def test_load_clears_previous_save_response(record_spec, api):
    editor = make_editor(record_spec, show_lookup=False)
    await editor.load(taskId=1)
    editor.editor.widgets["title"].value = "Changed"
    await editor.save()
    assert len(editor.editor.response) > 0

    await editor.load(taskId=1)

    assert len(editor.editor.response) == 0


def test_editing_enables_save_without_loading(record_spec):
    editor = make_editor(record_spec)
    assert editor.editor._submit_button.disabled is True

    editor.editor.widgets["title"].value = "Typed directly"

    assert editor.editor._submit_button.disabled is False


def test_read_only_widget_does_not_enable_save(record_spec):
    editor = make_editor(record_spec)
    # id is readOnly, so touching it cannot produce anything worth sending.
    editor.editor.widgets["id"].value = 9
    assert editor.editor._submit_button.disabled is True


async def test_save_without_loading_sends_edited_fields(record_spec, api):
    editor = make_editor(record_spec, show_lookup=False)
    editor.editor.widgets["taskId"].value = 1
    editor.editor.widgets["title"].value = "No lookup"

    await editor.save()

    request = api["requests"][-1]
    # The typed path parameter must survive; the lookup form is not showing.
    assert request.url.path == "/tasks/1"
    sent = json.loads(request.content)
    # Without a loaded record every filled field counts as a change.
    assert sent["title"] == "No lookup"


def test_edit_watchers_survive_operation_change(record_spec):
    editor = make_editor(record_spec)
    editor.editor.method = "put"
    editor.editor._submit_button.disabled = True

    editor.populate({"title": "Original"})
    editor.editor.widgets["title"].value = "Changed"

    assert editor.editor._submit_button.disabled is False


async def test_hidden_path_param_copied_from_lookup(record_spec, api):
    editor = make_editor(record_spec)
    await editor.load(taskId=3)
    editor.editor.widgets["title"].value = "Changed"

    await editor.save()

    assert api["requests"][-1].url.path == "/tasks/3"


async def test_load_error_names_the_url(record_spec, monkeypatch):
    def handler(request):
        return httpx.Response(404, json={"detail": "nope"})

    original = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda *a, **k: original(*a, **{**k, "transport": httpx.MockTransport(handler)}),
    )
    editor = make_editor(record_spec, show_lookup=False)

    assert await editor.load(taskId=9) is None

    message = editor._status[0].object
    assert "404" in message
    assert "/tasks/9" in message
