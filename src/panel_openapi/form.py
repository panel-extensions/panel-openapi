"""A Panel form that drives a single OpenAPI operation.

:class:`OpenAPIForm` introspects one path + method of an OpenAPI document,
renders a panel-material-ui widget per parameter and JSON body property, and on
submit issues the HTTP request and displays the response.
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Any

import panel as pn
import panel_material_ui as pmui
import param
from openapi_pydantic import OpenAPI
from openapi_pydantic import Operation

from .schema import Field
from .schema import collect_fields
from .schema import get_operation
from .schema import load_openapi
from .widgets import schema_to_widget

_EMPTY = (None, "", [], {})


def _coerce(widget: pmui.widgets.Widget, value: Any) -> Any:
    """Convert a JSON value into something ``widget.value`` accepts.

    Handles the cases where a JSON record and a widget disagree: JSON text areas
    hold serialized text, and the datetime picker rejects ISO strings (unlike
    the date picker, which parses them itself).
    """
    if isinstance(widget, pmui.TextAreaInput):
        return value if isinstance(value, str) else json.dumps(value, indent=2)
    if isinstance(widget, pmui.DatetimePicker) and isinstance(value, str):
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if isinstance(widget, pmui.Checkbox):
        return bool(value)
    return value


class OpenAPIForm(pn.viewable.Viewer):
    """Auto-generated form for a single OpenAPI operation.

    Setting :attr:`path` or :attr:`method` rebuilds the widgets for the newly
    referenced operation in place, and setting :attr:`base_url` redirects
    subsequent requests, so one form can be pointed at any operation in the
    document it was constructed with. To change both at once use
    ``form.param.update(path=..., method=...)``, which rebuilds only once and
    avoids a transient pair the document does not define.

    Parameters
    ----------
    openapi : str or dict or OpenAPI
        The OpenAPI document, as a URL, raw dict or parsed model.
    base_url : str
        The base URL requests are issued against, e.g. ``https://api.example.com``.
    path : str
        The templated operation path, e.g. ``/pets/{petId}``.
    method : str
        The HTTP method for the operation.
    headers : dict, optional
        Static headers (e.g. authentication) sent with every request. The
        mapping is read on each submit, so mutating it swaps credentials at
        runtime.

    Attributes
    ----------
    form : panel_material_ui.Column
        The widgets and submit button. Rebuilt in place when the operation
        changes, so the container may be laid out once and kept.
    response : panel_material_ui.Column
        The status and body of the most recent response, empty until submit.
    """

    base_url = param.String(default="", doc="Base URL requests are issued against.")

    path = param.String(default="", doc="Templated path of the operation.")

    method = param.Selector(
        default="get",
        objects=["get", "post", "put", "patch", "delete"],
        doc="HTTP method of the operation.",
    )

    title = param.String(
        default="",
        doc="Human-readable title, derived from the operation unless set explicitly.",
    )

    skip_read_only = param.Boolean(
        default=False,
        constant=True,
        doc=(
            "Whether to omit body properties marked readOnly entirely. When "
            "False they are shown as disabled widgets. Either way they are "
            "never sent, since the server does not accept them."
        ),
    )

    def __init__(
        self,
        openapi: str | dict[str, Any] | OpenAPI,
        base_url: str,
        path: str,
        method: str = "get",
        headers: dict[str, str] | None = None,
        **params: Any,
    ) -> None:
        self._explicit_title = bool(params.get("title"))
        super().__init__(base_url=base_url, path=path, method=method, **params)
        self._openapi = load_openapi(openapi)
        self._headers = dict(headers or {})
        self.response = pmui.Column(sizing_mode="stretch_width")
        self.form = pmui.Column(sizing_mode="stretch_width")
        self._submit_button = pmui.Button(label="Submit", variant="contained", on_click=self._submit)
        # Errors on the initial build are programming errors, so they propagate.
        self._rebuild()

    @property
    def operation(self) -> Operation:
        """The operation the form currently targets."""
        return self._operation

    @property
    def fields(self) -> list[Field]:
        """Descriptors for the inputs of the current operation."""
        return list(self._fields)

    @property
    def widgets(self) -> dict[str, pmui.widgets.Widget]:
        """The current widgets, keyed by field name."""
        return {field.name: widget for field, widget in self._widgets}

    def get_values(self, location: str | None = None) -> dict[str, Any]:
        """Return the values that would be sent, keyed by field name.

        JSON text areas are returned parsed. Fields left empty and fields marked
        ``readOnly`` are omitted, mirroring the request.

        Parameters
        ----------
        location : str, optional
            Restrict the result to one of ``path``, ``query``, ``header`` or
            ``body``. All locations are included when omitted.

        Returns
        -------
        dict
            Field name to value.
        """
        values: dict[str, Any] = {}
        for field, widget in self._widgets:
            if field.read_only or (location is not None and field.location != location):
                continue
            value = widget.value
            if value in _EMPTY:
                continue
            if isinstance(widget, pmui.TextAreaInput):
                try:
                    value = json.loads(value)
                except (TypeError, ValueError):
                    continue
            values[field.name] = value
        return values

    @property
    def values(self) -> dict[str, Any]:
        """The values that would be sent, keyed by field name."""
        return self.get_values()

    def populate(self, record: dict[str, Any]) -> list[str]:
        """Set widget values from a record, ignoring what does not fit.

        Population is deliberately tolerant: a record fetched from a live API
        routinely carries keys the request body does not accept, and values a
        widget cannot represent. Rather than raising, both are skipped and
        reported, so a partially populated form is still usable.

        Parameters
        ----------
        record : dict
            Field name to value, e.g. the parsed body of a ``GET`` response.

        Returns
        -------
        list of str
            Names of keys that could not be applied, either because no widget
            matched or because the value was rejected.
        """
        widgets = self.widgets
        skipped: list[str] = []
        for name, value in record.items():
            widget = widgets.get(name)
            if widget is None:
                skipped.append(name)
                continue
            try:
                widget.value = _coerce(widget, value)
            except (ValueError, TypeError):
                skipped.append(name)
        return skipped

    def _derived_title(self) -> str:
        op = self._operation
        return op.summary or op.operationId or f"{self.method.upper()} {self.path}"

    def _rebuild(self) -> None:
        """Rebuild the widgets for the current path and method."""
        self._operation = get_operation(self._openapi, self.path, self.method)
        self._fields = collect_fields(self._openapi, self._operation, skip_read_only=self.skip_read_only)
        self._widgets = []
        for field in self._fields:
            widget = schema_to_widget(field.name, field.schema, field.required)
            if field.read_only:
                # Shown for context only; _collect_values never sends these.
                widget.disabled = True
            self._widgets.append((field, widget))
        if not self._explicit_title:
            self.title = self._derived_title()
        self.response[:] = []
        self.form[:] = self._form_items()

    @param.depends("path", "method", watch=True)
    def _update_operation(self) -> None:
        """Rebuild when the targeted operation changes, reporting bad targets."""
        try:
            self._rebuild()
        except KeyError as exc:
            self._widgets = []
            self.form[:] = [pmui.Alert(object=str(exc.args[0]), severity="error")]

    def _form_items(self) -> list[Any]:
        items: list[Any] = []
        if self._operation.description:
            items.append(pmui.Typography(self._operation.description, variant="body2"))
        for _field, widget in self._widgets:
            widget.sizing_mode = "stretch_width"
            items.append(widget)
        items.append(self._submit_button)
        return items

    def _collect_values(self) -> tuple[dict[str, Any], list[str]]:
        """Read widget values grouped by request location.

        Returns
        -------
        tuple
            A mapping with ``path``, ``query``, ``header`` and ``body`` keys and
            a list of names of required fields that were left empty.
        """
        grouped: dict[str, dict[str, Any]] = {
            "path": {},
            "query": {},
            "header": {},
            "body": {},
        }
        missing: list[str] = []
        for field, widget in self._widgets:
            if field.read_only:
                # Server-assigned, so not accepted in a request body.
                continue
            value = widget.value
            if value in _EMPTY:
                if field.required:
                    missing.append(field.name)
                continue
            if isinstance(widget, pmui.TextAreaInput):
                try:
                    value = json.loads(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Field {field.name!r} must contain valid JSON: {exc}") from exc
            grouped[field.location][field.name] = value
        return grouped, missing

    def _build_request(self, grouped: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Assemble httpx request arguments from grouped widget values."""
        path = self.path
        for name, value in grouped["path"].items():
            path = path.replace(f"{{{name}}}", str(value))
        url = self.base_url.rstrip("/") + path
        kwargs: dict[str, Any] = {
            "method": self.method.upper(),
            "url": url,
            "params": grouped["query"],
            "headers": {**self._headers, **grouped["header"]},
        }
        if grouped["body"]:
            # A lone ``body`` field carries the whole payload, otherwise the
            # individual properties form the JSON object.
            if list(grouped["body"]) == ["body"]:
                kwargs["json"] = grouped["body"]["body"]
            else:
                kwargs["json"] = grouped["body"]
        return kwargs

    async def submit(self, extra: dict[str, Any] | None = None) -> Any:
        """Issue the request for the current values and render the response.

        Parameters
        ----------
        extra : dict, optional
            Additional body properties merged into the payload, overriding the
            widget values. Used to send a subset or superset of the form, e.g. a
            PATCH diff.

        Returns
        -------
        httpx.Response or None
            The response, or ``None`` if validation failed or the request could
            not be made. In both cases the reason is shown in :attr:`response`.
        """
        import httpx

        self.response[:] = []
        try:
            grouped, missing = self._collect_values()
        except ValueError as exc:
            self.response[:] = [pmui.Alert(object=str(exc), severity="error")]
            return None
        if missing:
            names = ", ".join(missing)
            self.response[:] = [pmui.Alert(object=f"Missing required fields: {names}", severity="warning")]
            return None

        if extra is not None:
            grouped["body"] = dict(extra)

        request_kwargs = self._build_request(grouped)
        self._submit_button.loading = True
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(**request_kwargs)
        except httpx.HTTPError as exc:
            self.response[:] = [pmui.Alert(object=f"Request failed: {exc}", severity="error")]
            return None
        finally:
            self._submit_button.loading = False

        self.response[:] = self._render_response(response)
        return response

    async def _submit(self, event: Any = None) -> None:
        await self.submit()

    def _render_response(self, response: Any) -> list[Any]:
        severity = "success" if response.is_success else "error"
        status = pmui.Alert(object=f"{response.status_code} {response.reason_phrase}", severity=severity)
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                body: Any = pn.pane.JSON(response.json(), depth=-1, sizing_mode="stretch_width")
            except ValueError:
                body = pmui.TextAreaInput(value=response.text, disabled=True, sizing_mode="stretch_width")
        else:
            body = pmui.TextAreaInput(value=response.text, disabled=True, sizing_mode="stretch_width")
        return [status, body]

    def __panel__(self) -> Any:
        """Return the UI."""
        return pmui.Row(
            self.form,
            self.response,
            sizing_mode="stretch_width",
        )
