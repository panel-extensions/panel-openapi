# Examples

The scripts in [`examples/`](https://github.com/panel-extensions/panel-openapi/tree/main/examples)
are longer and messier than the how-to snippets on purpose: they run against real
APIs and cover the awkward parts. Unless noted, run them with:

```bash
panel serve examples/<name>.py --show
```

| Example | What it shows |
| --- | --- |
| `01_inline_spec.py` | An inline spec annotated to show which schema construct produces which widget. |
| `02_fastapi_app.py` | A FastAPI app and its generated client in one process. Run with `python examples/02_fastapi_app.py`. |
| `03_remote_spec.py` | A spec loaded from a URL, with one form repointed at any operation in it. |
| `04_authenticated.py` | Auth headers, and swapping credentials at runtime. |
| `05_custom_form.py` | The introspection helpers, with grouped sections and a request preview. |
| `06_custom_layout.py` | The public `form` and `response` containers as sidebar and main. |
| `07_record_editor.py` | `OpenAPIRecordEditor` against the Swagger Petstore, with a confirmation dialog. |
| `08_patch_editor.py` | `PATCH` semantics against a local FastAPI app, displaying every body it receives. Run with `python examples/08_patch_editor.py`. |

Examples 01, 03, 04, 06 and 07 need network access, since they target public
services. 02 and 08 are self-contained, and 05 previews the request it would send
rather than sending one.

## Reading order

Start with `01_inline_spec.py` for the schema-to-widget mapping, then
`02_fastapi_app.py` for the case where you own the API. `03` and `04` cover
loading specs remotely and authenticating. `05` and `06` are the two
customization routes: `06` rearranges what `OpenAPIForm` builds, `05` bypasses it
and builds its own.

`07` and `08` move from submitting a form to editing an existing record. Read
`07` for the shape of `OpenAPIRecordEditor`, and `08` for what actually goes over
the wire, which is the part worth being sure about before pointing it at an API
you care about.

## The documentation snippets

Every how-to page embeds a runnable script from
[`docs/snippets/`](https://github.com/panel-extensions/panel-openapi/tree/main/docs/snippets).
They are smaller than the examples and each makes one point. Serve them the same
way:

```bash
panel serve docs/snippets/quickstart.py --show
```

The screenshots in these docs are generated from those same scripts by
`docs/screenshots.py`, so the code on a page is the code in its picture.
