"""Load a spec from a URL and browse every operation in it.

``load_openapi`` accepts a URL, so pointing it at a published
``openapi.json`` is enough to get a working client. This example fetches the
Swagger Petstore spec and lets you switch between any of its operations.

``OpenAPIForm.path`` and ``.method`` are reactive: assigning to them rebuilds
the widgets for the newly targeted operation in place. So a single form
instance serves the whole document, and the spec is fetched only once at
startup.

Run with::

    panel serve examples/03_remote_spec.py --show
"""

from __future__ import annotations

import panel as pn
import panel_material_ui as pmui

from panel_openapi import OpenAPIForm, load_openapi

pn.extension()

SPEC_URL = "https://petstore3.swagger.io/api/v3/openapi.json"
BASE_URL = "https://petstore3.swagger.io/api/v3"

METHODS = ("get", "put", "post", "delete", "patch")

# Fetched over HTTP and validated into an OpenAPI model.
SPEC = load_openapi(SPEC_URL)

# Every (path, method) pair the document defines, in declaration order.
OPERATIONS = {
    f"{method.upper()} {path}": (path, method)
    for path, item in (SPEC.paths or {}).items()
    for method in METHODS
    if getattr(item, method, None) is not None
}

first_path, first_method = next(iter(OPERATIONS.values()))

form = OpenAPIForm(SPEC, base_url=BASE_URL, path=first_path, method=first_method)

selector = pmui.Select(
    label="Operation",
    options=list(OPERATIONS),
    sizing_mode="stretch_width",
)


def _select_operation(label: str) -> None:
    path, method = OPERATIONS[label]
    # param.update() applies both at once, so the form rebuilds a single time
    # and never sees a path/method pair the document does not define.
    form.param.update(path=path, method=method)


pn.bind(_select_operation, selector, watch=True)

page = pmui.Page(
    title=f"{SPEC.info.title}: {form.title}",
    main=[pmui.Column(selector, pmui.Divider(), form, sizing_mode="stretch_width")],
)

# The form's title parameter tracks whichever operation is selected. Page.title
# is a plain string parameter rather than a reactive one, so keep it in sync.
form.param.watch(lambda event: page.param.update(title=f"{SPEC.info.title}: {event.new}"), "title")

page.servable()
