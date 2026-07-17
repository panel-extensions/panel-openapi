"""A Panel form that drives a single OpenAPI operation.

:class:`OpenAPIForm` introspects one path + method of an OpenAPI document,
renders a panel-material-ui widget per parameter and JSON body property, and on
submit issues the HTTP request and displays the response.
"""

from __future__ import annotations

import json
from typing import Any

import panel as pn
import panel_material_ui as pmui
import param
from openapi_pydantic import OpenAPI

from .schema import Field, collect_fields, get_operation, load_openapi
from .widgets import schema_to_widget

_EMPTY = (None, "", [], {})


class OpenAPIForm(pn.viewable.Viewer):
    """Auto-generated form for a single OpenAPI operation.

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
        Static headers (e.g. authentication) sent with every request.
    """

    base_url = param.String(default="", doc="Base URL requests are issued against.")

    path = param.String(default="", doc="Templated path of the operation.")

    method = param.Selector(
        default="get",
        objects=["get", "post", "put", "patch", "delete"],
        doc="HTTP method of the operation.",
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
        super().__init__(base_url=base_url, path=path, method=method, **params)
        self._openapi = load_openapi(openapi)
        self._operation = get_operation(self._openapi, self.path, self.method)
        self._headers = dict(headers or {})
        self._fields = collect_fields(self._openapi, self._operation)
        self._widgets: list[tuple[Field, pmui.widgets.Widget]] = [
            (field, schema_to_widget(field.name, field.schema, field.required))
            for field in self._fields
        ]
        self._response = pmui.Column(sizing_mode="stretch_width")
        self._submit_button = pmui.Button(
            label="Submit", variant="contained", on_click=self._submit
        )
        self._form = self._build_form()

    @property
    def title(self) -> str:
        """A human-readable title for the operation."""
        op = self._operation
        return op.summary or op.operationId or f"{self.method.upper()} {self.path}"

    def _build_form(self) -> pmui.Column:
        items: list[Any] = []
        if self._operation.description:
            items.append(pmui.Typography(self._operation.description, variant="body2"))
        for _field, widget in self._widgets:
            widget.sizing_mode = "stretch_width"
            items.append(widget)
        items.append(self._submit_button)
        return pmui.Column(*items, sizing_mode="stretch_width")

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

    async def _submit(self, event: Any = None) -> None:
        import httpx

        self._response[:] = []
        try:
            grouped, missing = self._collect_values()
        except ValueError as exc:
            self._response[:] = [pmui.Alert(object=str(exc), severity="error")]
            return
        if missing:
            names = ", ".join(missing)
            self._response[:] = [
                pmui.Alert(object=f"Missing required fields: {names}", severity="warning")
            ]
            return

        request_kwargs = self._build_request(grouped)
        self._submit_button.loading = True
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(**request_kwargs)
        except httpx.HTTPError as exc:
            self._response[:] = [pmui.Alert(object=f"Request failed: {exc}", severity="error")]
            return
        finally:
            self._submit_button.loading = False

        self._response[:] = self._render_response(response)

    def _render_response(self, response: Any) -> list[Any]:
        severity = "success" if response.is_success else "error"
        status = pmui.Alert(
            object=f"{response.status_code} {response.reason_phrase}", severity=severity
        )
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
        if pn.state.served:
            return pmui.Page(
                title=self.title,
                sidebar=[self._form],
                main=[pmui.Column(self._response, margin=10, sizing_mode="stretch_width")],
            )
        return pmui.Row(
            pmui.Column(self._form, max_width=400),
            self._response,
            sizing_mode="stretch_width",
        )
