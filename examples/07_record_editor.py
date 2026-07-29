"""Look up a record and edit it.

``OpenAPIRecordEditor`` pairs a read operation with an update operation on the
same path. Point it at a path, and it finds the update operation itself,
fetches a record, populates a form from the response, and sends the edits back.

This one targets the Swagger Petstore, whose ``GET /pet/{petId}`` pairs with
``POST /pet/{petId}``. Load pet 1 (or any id that exists), change a field, and
save. ``confirm=True`` shows the pending changes before anything is sent.

Note that the Petstore is a shared public sandbox, so records change under you
and ids come and go.

Run with::

    panel serve examples/07_record_editor.py --show
"""

from __future__ import annotations

import panel as pn
import panel_material_ui as pmui

from panel_openapi import OpenAPIRecordEditor, find_update_operations, load_openapi

pn.extension()

SPEC_URL = "https://petstore3.swagger.io/api/v3/openapi.json"
BASE_URL = "https://petstore3.swagger.io/api/v3"

SPEC = load_openapi(SPEC_URL)
PATH = "/pet/{petId}"

editor = OpenAPIRecordEditor(
    SPEC,
    base_url=BASE_URL,
    path=PATH,
    # update_method is auto-detected: PATCH, then PUT, then POST on the same
    # path. Here that resolves to POST, which the editor displays so the
    # heuristic is never invisible. Pass update_method="put" to override.
    confirm=True,
)

# Petstore's POST /pet/{petId} takes its updates as query parameters rather than
# a JSON body, which is worth seeing spelled out.
candidates = ", ".join(m.upper() for m in find_update_operations(SPEC, PATH))

pmui.Page(
    title="Petstore record editor",
    main=[
        pmui.Column(
            pmui.Alert(
                object=(
                    f"Update operations found on `{PATH}`: {candidates}. "
                    f"Using **{editor.update_method.upper()}**. Try petId 1."
                ),
                severity="info",
            ),
            editor,
            margin=10,
            sizing_mode="stretch_width",
        )
    ],
).servable()
