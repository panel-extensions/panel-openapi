"""Look up a record from an OpenAPI operation and edit it.

:class:`OpenAPIRecordEditor` pairs a read operation with an update operation on
the same path: it fetches a record, populates a form from the response, and
sends the edits back.
"""

from __future__ import annotations

import json
from typing import Any

import panel as pn
import panel_material_ui as pmui
import param
from openapi_pydantic import OpenAPI

from .form import OpenAPIForm
from .schema import find_update_operations, get_operation, load_openapi

# Methods whose body is a partial update, so only changed fields are sent.
_PARTIAL_METHODS = ("patch",)

# Longest value rendered in full in the confirmation dialog.
_MAX_DIFF_VALUE = 60


def _short(value: Any) -> str:
    """Render a value for the diff, truncating anything long."""
    text = "(unset)" if value is None else json.dumps(value, default=str)
    if len(text) > _MAX_DIFF_VALUE:
        return text[: _MAX_DIFF_VALUE - 1] + "…"
    return text


class OpenAPIRecordEditor(pn.viewable.Viewer):
    """Fetch a record from an operation and edit it via another.

    The editor composes two :class:`~panel_openapi.form.OpenAPIForm` instances:
    a lookup form for the read operation, and an edit form for the update
    operation. Loading a record populates the edit form, and saving sends the
    edits back to the same resource.

    The update operation is discovered on the same path, preferring ``PATCH``
    over ``PUT`` over ``POST``, unless ``update_method`` names one. Because
    ``POST`` on a path means "update this" in some APIs and "create a
    subresource" in others, the resolved operation is always displayed.

    A ``PATCH`` save sends only the fields that differ from the loaded record,
    matching the convention that omitted keys are left alone. ``PUT`` and
    ``POST`` send the full body.

    Parameters
    ----------
    openapi : str or dict or OpenAPI
        The OpenAPI document, as a URL, raw dict or parsed model.
    base_url : str
        The base URL requests are issued against.
    path : str
        The templated path of the record, e.g. ``/pets/{petId}``.
    method : str
        The method used to read the record.
    update_method : str, optional
        The method used to save. Auto-detected when omitted.
    headers : dict, optional
        Static headers sent with every request.
    show_lookup : bool
        Whether to render the lookup form. Set ``False`` when driving the editor
        with :meth:`load` or :meth:`populate`.
    **params
        Remaining parameters, notably ``confirm`` to have the Save button open a
        dialog listing the pending changes before sending them.

    Examples
    --------
    Point it at a path and let it find the update operation:

    >>> editor = OpenAPIRecordEditor(  # doctest: +SKIP
    ...     spec, base_url="https://petstore3.swagger.io/api/v3", path="/pet/{petId}"
    ... )

    Or drive it without the lookup UI:

    >>> editor = OpenAPIRecordEditor(spec, base_url=..., path=..., show_lookup=False)  # doctest: +SKIP
    >>> await editor.load(petId=7)  # doctest: +SKIP
    """

    base_url = param.String(default="", doc="Base URL requests are issued against.")

    path = param.String(default="", doc="Templated path of the record.")

    method = param.Selector(
        default="get",
        objects=["get", "post", "put", "patch", "delete"],
        doc="Method used to read the record.",
    )

    update_method = param.Selector(
        default=None,
        objects=[None, "patch", "put", "post"],
        doc="Method used to save the record. Auto-detected when None.",
    )

    record = param.Dict(
        default=None,
        allow_None=True,
        doc="The record last loaded or saved, and the baseline a PATCH diffs against.",
    )

    confirm = param.Boolean(
        default=False,
        doc="Whether the Save button opens a dialog showing the pending changes first.",
    )

    def __init__(
        self,
        openapi: str | dict[str, Any] | OpenAPI,
        base_url: str,
        path: str,
        method: str = "get",
        update_method: str | None = None,
        headers: dict[str, str] | None = None,
        show_lookup: bool = True,
        **params: Any,
    ) -> None:
        super().__init__(
            base_url=base_url, path=path, method=method, update_method=update_method, **params
        )
        self._openapi = load_openapi(openapi)
        self._headers = dict(headers or {})
        self._show_lookup = show_lookup

        # Fails fast if the read operation does not exist.
        get_operation(self._openapi, self.path, self.method)

        if self.update_method is None:
            candidates = find_update_operations(self._openapi, self.path)
            # The read method itself is not an update, even when it is a POST.
            candidates = [m for m in candidates if m != self.method]
            with param.parameterized.discard_events(self):
                self.update_method = candidates[0] if candidates else None

        self.lookup = OpenAPIForm(
            self._openapi,
            base_url=self.base_url,
            path=self.path,
            method=self.method,
            headers=self._headers,
        )
        self.lookup._submit_button.label = "Load"
        self.lookup._submit_button.on_click(self._load_clicked)

        # Edit-form path inputs hidden because the lookup form asks for them.
        self._hidden: set[str] = set()

        self.editor: OpenAPIForm | None = None
        if self.update_method is not None:
            self.editor = OpenAPIForm(
                self._openapi,
                base_url=self.base_url,
                path=self.path,
                method=self.update_method,
                headers=self._headers,
            )
            self.editor._submit_button.label = "Save"
            self.editor._submit_button.on_click(self._save_clicked)
            self.editor._submit_button.disabled = True
            self._watched: set[int] = set()
            self._watch_edits()
            if show_lookup:
                self._hide_shared_path_widgets()

        self._status = pmui.Column(sizing_mode="stretch_width")

        self._diff_pane = pmui.Column(sizing_mode="stretch_width")
        self._dialog = pmui.Dialog(
            pmui.Typography("Confirm changes", variant="h6"),
            self._diff_pane,
            pmui.Row(
                pmui.Button(
                    label="Confirm save",
                    variant="contained",
                    color="success",
                    on_click=self._confirmed,
                ),
                pmui.Button(label="Cancel", variant="text", on_click=self._cancelled),
            ),
            width_option="sm",
        )

    @property
    def loaded(self) -> bool:
        """Whether a record has been loaded."""
        return self.record is not None

    def _watch_edits(self) -> None:
        """Enable Save as soon as the user touches the edit form.

        Waiting for a load would strand anyone who wants to send an update
        without reading the record first, which a ``PATCH`` supports perfectly
        well. Watchers are attached once per widget, since the form rebuilds its
        widgets when the operation changes.
        """
        assert self.editor is not None
        for field, widget in self.editor._widgets:
            if field.read_only or id(widget) in self._watched:
                continue
            self._watched.add(id(widget))
            widget.param.watch(self._edited, "value")

    def _edited(self, event: Any = None) -> None:
        """Enable Save now that there is something to send."""
        assert self.editor is not None
        self.editor._submit_button.disabled = False

    def _hide_shared_path_widgets(self) -> None:
        """Hide edit-form path inputs that the lookup form already asks for.

        Both operations sit on the same path, so both generate a widget for e.g.
        ``petId``. Asking twice invites the two to disagree; :meth:`save` copies
        the value across instead.
        """
        assert self.editor is not None
        shared = {
            field.name for field, _ in self.lookup._widgets if field.location == "path"
        }
        for field, widget in self.editor._widgets:
            if field.location == "path" and field.name in shared:
                widget.visible = False
                self._hidden.add(field.name)

    def _lookup_params(self, hidden_only: bool = False) -> dict[str, Any]:
        """Path parameter values from the lookup form.

        Parameters
        ----------
        hidden_only : bool
            Restrict to inputs the edit form is not showing itself. Used when
            saving, where copying a visible field would let an untouched lookup
            default overwrite a value the user typed into the edit form.
        """
        return {
            field.name: widget.value
            for field, widget in self.lookup._widgets
            if field.location == "path"
            and (not hidden_only or field.name in self._hidden)
            and widget.value not in (None, "")
        }

    async def load(self, **lookup: Any) -> dict[str, Any] | None:
        """Fetch a record and populate the edit form.

        Parameters
        ----------
        **lookup
            Values for the read operation's inputs, e.g. ``petId=7``. Widgets
            keep their current value when not given, which is what the Load
            button relies on.

        Returns
        -------
        dict or None
            The fetched record, or ``None`` if the request failed or did not
            return a JSON object.
        """
        if lookup:
            unknown = set(lookup) - set(self.lookup.widgets)
            if unknown:
                raise ValueError(
                    f"Unknown lookup fields: {', '.join(sorted(unknown))}. "
                    f"Available: {', '.join(self.lookup.widgets)}."
                )
            self.lookup.populate(lookup)

        response = await self.lookup.submit()
        if response is None:
            return None
        if not response.is_success:
            # Naming the URL turns "404" into something actionable, since the
            # usual cause is a path parameter left at its default.
            self._set_status(
                f"Could not load record: {response.status_code} from {response.url}.",
                "error",
            )
            return None

        try:
            record = response.json()
        except ValueError:
            self._set_status("Response was not JSON, so there is nothing to edit.", "error")
            return None
        if not isinstance(record, dict):
            self._set_status(
                "Response was not a JSON object, so it cannot populate a form.", "error"
            )
            return None

        self.populate(record)
        return record

    def populate(self, record: dict[str, Any]) -> None:
        """Populate the edit form from a record without fetching it.

        Parameters
        ----------
        record : dict
            The record to edit. Becomes the baseline a ``PATCH`` diffs against.
        """
        self.record = record
        if self.editor is None:
            self._set_status("Loaded, but no update operation is available.", "info")
            return

        # A response from an earlier save does not describe the record just loaded.
        self.editor.response[:] = []
        # The edit form targets whatever the lookup just fetched, so it adopts
        # those path parameters even where it shows them itself.
        skipped = self.editor.populate({**self._lookup_params(), **record})
        # The form may have rebuilt its widgets since the last time we looked.
        self._watch_edits()
        self.editor._submit_button.disabled = False
        if skipped:
            self._set_status(
                f"Loaded. Not editable here: {', '.join(sorted(skipped))}.", "info"
            )
        else:
            self._set_status("Loaded. Edit the fields and save.", "success")

    def diff(self) -> dict[str, tuple[Any, Any]]:
        """The edits pending against the loaded record.

        Returns
        -------
        dict
            Field name to ``(old, new)``, covering every editable location, not
            just the body. Some APIs take updates as query parameters, e.g. the
            Swagger Petstore's ``POST /pet/{petId}``.
        """
        if self.editor is None:
            return {}
        record = self.record or {}
        changes: dict[str, tuple[Any, Any]] = {}
        for location in ("query", "header", "body"):
            for name, value in self.editor.get_values(location).items():
                old = record.get(name)
                if name not in record or old != value:
                    changes[name] = (old, value)
        return changes

    def _changed_body(self) -> dict[str, Any]:
        """Body fields whose value differs from the loaded record."""
        assert self.editor is not None
        record = self.record or {}
        return {
            name: value
            for name, value in self.editor.get_values("body").items()
            if name not in record or record[name] != value
        }

    async def save(self) -> dict[str, Any] | None:
        """Send the edits and adopt the response as the new record.

        Bypasses the confirmation dialog, which is only wired to the Save
        button, so calling this always saves.

        Returns
        -------
        dict or None
            The saved record as the server returned it, or ``None`` if the save
            failed or returned no JSON object.
        """
        if self.editor is None:
            raise RuntimeError("No update operation is available for this path.")

        # Fill in only the path inputs the edit form does not show, since a
        # visible one holds whatever the user last put there.
        self.editor.populate(self._lookup_params(hidden_only=True))

        extra = None
        if self.update_method in _PARTIAL_METHODS:
            extra = self._changed_body()
            if not extra:
                self._set_status("Nothing changed.", "info")
                return None

        response = await self.editor.submit(extra=extra)
        if response is None:
            return None
        if not response.is_success:
            self._set_status(f"Save failed: {response.status_code}.", "error")
            return None

        self._set_status("Saved.", "success")
        try:
            saved = response.json()
        except ValueError:
            return None
        if isinstance(saved, dict):
            # Adopt the server's version so the PATCH baseline stays accurate
            # and any server-side changes become visible.
            self.record = saved
            self.editor.populate(saved)
            return saved
        return None

    async def _load_clicked(self, event: Any = None) -> None:
        await self.load()

    async def _save_clicked(self, event: Any = None) -> None:
        if not self.confirm:
            await self.save()
            return

        changes = self.diff()
        if not changes:
            self._set_status("Nothing changed.", "info")
            return
        self._diff_pane[:] = self._render_diff(changes)
        self._dialog.open = True

    async def _confirmed(self, event: Any = None) -> None:
        self._dialog.open = False
        await self.save()

    def _cancelled(self, event: Any = None) -> None:
        self._dialog.open = False

    def _render_diff(self, changes: dict[str, tuple[Any, Any]]) -> list[Any]:
        """Render pending changes as one 'old -> new' line per field."""
        rows: list[Any] = []
        for name, (old, new) in sorted(changes.items()):
            label = "Set" if old is None and name not in (self.record or {}) else "Update"
            rows.append(
                pmui.Typography(
                    f"**{label} {name}**: `{_short(old)}` → `{_short(new)}`", variant="body2"
                )
            )
        method = (self.update_method or "").upper()
        return [
            pmui.Typography(
                f"{len(rows)} field(s) will be sent via {method} {self.path}.",
                variant="subtitle2",
            ),
            *rows,
        ]

    def _set_status(self, message: str, severity: str) -> None:
        self._status[:] = [pmui.Alert(object=message, severity=severity)]

    def __panel__(self) -> Any:
        items: list[Any] = []
        if self._show_lookup:
            items += [
                pmui.Typography("Find a record", variant="subtitle2"),
                self.lookup.form,
            ]
        items.append(self._status)
        if self.editor is None:
            items.append(
                pmui.Alert(
                    object=f"No update operation found on {self.path}.", severity="warning"
                )
            )
        else:
            items += [
                pmui.Divider(),
                pmui.Typography(
                    f"Edit ({self.update_method.upper()} {self.path})", variant="subtitle2"
                ),
                self.editor.form,
                self.editor.response,
                self._dialog,
            ]
        return pmui.Column(*items, sizing_mode="stretch_width")
