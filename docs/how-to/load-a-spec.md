# Load a Specification

`OpenAPIForm`, `OpenAPIRecordEditor` and `load_openapi` all accept the same three
forms of specification.

## From a URL

Most published APIs serve their document. It is fetched once, when the object is
constructed.

```python
from panel_openapi import OpenAPIForm

form = OpenAPIForm(
    "https://petstore3.swagger.io/api/v3/openapi.json",
    base_url="https://petstore3.swagger.io/api/v3",
    path="/pet/findByStatus",
    method="get",
)
```

Redirects are followed and a non-2xx response raises, so a typo in the URL fails
immediately rather than producing an empty form.

## From a dict

Useful for a hand-written spec, one loaded from a file, or a small subset of a
large API you only need part of:

```python
import json
from pathlib import Path

spec = json.loads(Path("openapi.json").read_text())
form = OpenAPIForm(spec, base_url="https://api.example.com", path="/things", method="get")
```

## From a FastAPI app

FastAPI derives a document from your pydantic models, so a form for your own API
needs no extra schema authoring. Call `api.openapi()` rather than fetching the
URL:

```python
from fastapi import FastAPI
from panel.io.fastapi import add_application

from panel_openapi import OpenAPIForm

api = FastAPI()

# ... your endpoints ...

@add_application("/form", app=api, title="Client")
def form_app():
    return OpenAPIForm(api.openapi(), base_url=base_url(), path="/tasks", method="post")
```

`api.openapi()` builds the document in-process from the models and caches it on
the app, so there is no request involved. Fetching `/openapi.json` would mean
this app requesting a page from the server that is rendering it.

!!! tip "Do not hardcode the port"
    The base URL has to match wherever the app ended up, which is not the same
    under `python app.py`, `fastapi run` and a production server. Read it off the
    request instead:

    ```python
    import panel as pn

    def base_url() -> str:
        location = pn.state.location
        return f"{location.protocol}//{location.hostname}:{location.port}"
    ```

## From a parsed model

`load_openapi` returns an `openapi_pydantic` model, which every constructor also
accepts. Parse once and share it when several forms target the same API:

```python
from panel_openapi import OpenAPIForm, load_openapi

spec = load_openapi("https://petstore3.swagger.io/api/v3/openapi.json")

pets = OpenAPIForm(spec, base_url=BASE, path="/pet/{petId}", method="get")
orders = OpenAPIForm(spec, base_url=BASE, path="/store/order", method="post")
```

This also avoids fetching the same URL twice.

## Versions

OpenAPI 3.0 and 3.1 are both supported. The version string is read from the
document and the matching model is used, which matters because the two differ:
`anyOf` with a `null` branch is 3.1 only, while 3.0 spells the same thing
`nullable: true`. Both end up as a normal widget rather than a JSON text area.
