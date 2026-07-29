# Build a Form

`OpenAPIForm` targets exactly one operation. It needs a specification, the base
URL to send requests to, and the path and method that identify the operation.

```python
from panel_openapi import OpenAPIForm

form = OpenAPIForm(
    spec,                     # URL, dict, or parsed OpenAPI model
    base_url="https://api.example.com",
    path="/pets/{petId}",     # exactly as written in the document
    method="get",
)
```

The `path` must match the document's key, braces and all. `/pets/7` will not be
found; `/pets/{petId}` will, and the widget for `petId` fills in the 7.

## What gets a widget

Every input the operation declares, wherever it lives in the request:

| Location | Source | Where it ends up |
| --- | --- | --- |
| `path` | Path parameters | Substituted into the URL |
| `query` | Query parameters | The query string |
| `header` | Header parameters | Request headers |
| `body` | Properties of the JSON request body | The JSON body |

Parameters declared on the path item, shared by all its operations, are included
too. Cookie parameters are not supported.

If the body schema is not an object, for instance a bare array, a single `body`
field carries the whole payload as JSON.

## Required fields

A field is required when the document says so: `required: true` on a parameter,
or the property's name in the body schema's `required` list. Submitting with one
empty stops the request and reports which:

```python
await form.submit()   # -> None, and "Missing required fields: name" is shown
```

## Read-only fields

A body property marked `readOnly` is server-assigned, so sending it would be
rejected. Those are shown as **disabled widgets** for context and left out of the
request. To hide them instead:

```python
form = OpenAPIForm(spec, base_url=..., path=..., method="patch", skip_read_only=True)
```

Either way they are never sent. `skip_read_only` only chooses between hidden and
shown-disabled.

## Titles

`form.title` is derived from the operation: its `summary`, else its
`operationId`, else `"GET /pets/{petId}"`. Pass `title=` to fix it, and it will
survive later operation changes.

## Errors

Two failure modes, reported rather than raised:

- **A bad target.** Constructing with a path or method the document does not
  define raises `KeyError`, since that is a programming error. Setting `path` or
  `method` to something undefined later renders an error listing what is
  available, because reactive updates pass through invalid pairs on the way to
  valid ones.
- **A bad request.** A non-2xx response, invalid JSON in a text area, or a
  connection failure all render in `form.response`. `submit()` returns `None`.

## What submit does

```python
response = await form.submit()
```

It collects the widget values, groups them by location, builds the request,
issues it with `httpx`, and renders the status and body into `form.response`.
The return value is the `httpx.Response`, or `None` if nothing was sent.

## Related

- [Read and Submit Values](values.md) for driving a form from code
- [Understand Widget Mapping](widget-mapping.md) for the schema-to-widget rules
