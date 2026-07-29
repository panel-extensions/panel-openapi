# panel-openapi examples

Each example is a standalone script. Unless noted otherwise, run them with:

```bash
panel serve examples/<name>.py --show
```

| Example | What it shows |
| --- | --- |
| [`01_inline_spec.py`](01_inline_spec.py) | The basics: an inline spec dict, annotated to show which schema construct produces which widget. |
| [`02_fastapi_app.py`](02_fastapi_app.py) | A live FastAPI app and its generated client in one process. Run with `python examples/02_fastapi_app.py`, then open http://localhost:8000/form. |
| [`03_remote_spec.py`](03_remote_spec.py) | Loading a spec from a URL and repointing one form at any operation in it via reactive `path`/`method`. |
| [`04_authenticated.py`](04_authenticated.py) | Sending auth headers, and swapping credentials at runtime by mutating the `headers` dict. |
| [`05_custom_form.py`](05_custom_form.py) | Dropping to `load_openapi`/`get_operation`/`collect_fields`/`schema_to_widget` to build a form with your own validation and submit behaviour. |
| [`06_custom_layout.py`](06_custom_layout.py) | Placing the public `form` and `response` containers independently, here as sidebar and main. |
| [`07_record_editor.py`](07_record_editor.py) | `OpenAPIRecordEditor`: looking up a Petstore record and editing it, with auto-detection of the update operation and a confirmation dialog. |
| [`08_patch_editor.py`](08_patch_editor.py) | `PATCH` semantics against a local FastAPI app: only changed fields are sent, `readOnly` fields are shown disabled and never sent, and every received body is displayed. Run with `python examples/08_patch_editor.py`, then open http://localhost:8001/editor. |

Examples 01, 03, 04, 06 and 07 issue requests to public services
([httpbin](https://httpbin.org), the [Swagger
Petstore](https://petstore3.swagger.io) and the GitHub API), so they need
network access. Examples 02 and 08 are fully self-contained, and 05 previews the
request it would send rather than sending one.

## Reading order

Start with `01_inline_spec.py` for the schema-to-widget mapping, then
`02_fastapi_app.py` for the case where you own the API. `03` and `04` cover
loading specs remotely and authenticating. `05` and `06` are the two
customization routes: `06` rearranges what `OpenAPIForm` builds, `05` bypasses
it and builds your own.

`07` and `08` move from submitting a form to editing an existing record. Read
`07` for the shape of `OpenAPIRecordEditor` and `08` for what actually goes over
the wire, which is the part worth being sure about before pointing it at an API
you care about.
