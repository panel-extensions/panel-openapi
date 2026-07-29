# Read and Submit Values

A form can be driven entirely from code: read what it holds, fill it from a
record, and submit it without anyone clicking a button.

## Reading

`values` returns what would be sent, keyed by field name:

```python
form.values
# {"name": "Rex", "tags": ["a", "b"]}
```

Three things to know about it:

- JSON text areas are returned **parsed**, so `tags` is a list, not a string.
- Empty fields are **omitted**, matching the request, which does not send them.
- `readOnly` fields are omitted, since the server would reject them.

Restrict it to one part of the request with `get_values`:

```python
form.get_values("path")    # {"petId": 7}
form.get_values("body")    # just the JSON body properties
form.get_values("query")   # just the query string
```

This matters when an API takes updates as query parameters rather than a body,
which the Swagger Petstore's `POST /pet/{petId}` does.

## Reaching the widgets

```python
form.widgets["name"].value = "Rex"     # set one directly
form.widgets["name"].disabled = True   # or restyle it
```

`form.fields` gives the descriptors behind them, each with `name`, `location`,
`schema`, `required` and `read_only`, and `form.operation` is the parsed
operation if you need to consult the document.

## Populating from a record

```python
skipped = form.populate({"name": "Rex", "tags": ["a", "b"], "server_id": 12})
# skipped == ["server_id"]
```

`populate` is deliberately tolerant. A record from a live API routinely carries
keys the request body does not accept, and values a widget cannot represent.
Rather than raising, both are skipped and returned, so a partially populated form
is still usable. Values are coerced where a widget needs it: lists and dicts are
serialized into JSON text areas, and ISO timestamps are parsed for the datetime
picker.

## Submitting

```python
response = await form.submit()
if response is not None and response.is_success:
    record = response.json()
```

`submit` is a coroutine. It returns the `httpx.Response`, or `None` when a
required field was empty, a JSON text area did not parse, or the request failed.
In every one of those cases the reason is rendered into `form.response`, so a
`None` is never silent.

To send a body other than exactly what the widgets hold, pass `extra`, which
replaces the body:

```python
# Send only what changed, which is what PATCH means.
await form.submit(extra={"title": "A new title"})
```

Path, query and header values still come from the widgets.

## Clearing the response

```python
form.response[:] = []
```

It is a plain Panel `Column`, so emptying it clears the displayed result, which
is worth doing before showing something a stale response would contradict.
