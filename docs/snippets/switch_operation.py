"""One form, repointed at any operation in the document."""

import panel as pn
import panel_material_ui as pmui

from panel_openapi import OpenAPIForm, load_openapi

pn.extension()

SPEC = load_openapi("https://petstore3.swagger.io/api/v3/openapi.json")
BASE_URL = "https://petstore3.swagger.io/api/v3"

OPERATIONS = {
    "Find pets by status": ("/pet/findByStatus", "get"),
    "Get a pet by id": ("/pet/{petId}", "get"),
    "Add a pet": ("/pet", "post"),
    "Place an order": ("/store/order", "post"),
}

form = OpenAPIForm(SPEC, base_url=BASE_URL, path="/pet/findByStatus", method="get")

selector = pmui.Select(label="Operation", options=list(OPERATIONS), value="Find pets by status")


def repoint(event):
    path, method = OPERATIONS[event.new]
    # Update both at once: one rebuild, and no transient path/method pair the
    # document does not define.
    form.param.update(path=path, method=method)


selector.param.watch(repoint, "value")

pmui.Column(selector, form, sizing_mode="stretch_width").servable(title="Switch operation")
