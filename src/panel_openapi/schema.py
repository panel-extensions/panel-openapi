"""Load and introspect OpenAPI documents.

This module wraps :mod:`openapi_pydantic` to load an OpenAPI schema from a URL
or dictionary, resolve ``$ref`` references, locate a specific operation and
flatten its parameters and JSON request body into a list of field descriptors
that the widget layer can turn into inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Literal

import httpx
from openapi_pydantic import OpenAPI
from openapi_pydantic import Operation
from openapi_pydantic import Parameter
from openapi_pydantic import Reference
from openapi_pydantic import Schema
from openapi_pydantic import parse_obj
from openapi_pydantic.v3.v3_0 import Reference as ReferenceV30
from openapi_pydantic.v3.v3_1 import Reference as ReferenceV31

FieldLocation = Literal["path", "query", "header", "body"]

# ``parse_obj`` returns version-specific models (3.0 or 3.1), so Reference
# checks must accept either version's class.
_REFERENCE_TYPES = (Reference, ReferenceV30, ReferenceV31)

_JSON_MEDIA_TYPES = ("application/json", "application/*+json")


@dataclass
class Field:
    """A single input derived from an operation's parameters or request body.

    Parameters
    ----------
    name : str
        The parameter or property name used when assembling the request.
    location : FieldLocation
        Where the value belongs in the request (``path``, ``query``, ``header``
        or ``body``).
    schema : Schema
        The resolved JSON schema describing the value.
    required : bool
        Whether the field must be provided.
    read_only : bool
        Whether the schema marks the value ``readOnly``. Such fields are
        returned by the server but never sent in a request.
    """

    name: str
    location: FieldLocation
    schema: Schema
    required: bool = False
    read_only: bool = False


def load_openapi(source: str | dict[str, Any] | OpenAPI) -> OpenAPI:
    """Load and validate an OpenAPI document.

    Parameters
    ----------
    source : str or dict or OpenAPI
        Either an already parsed :class:`~openapi_pydantic.OpenAPI` model, a URL
        pointing at an ``openapi.json`` document, or the raw specification as a
        dictionary.

    Returns
    -------
    OpenAPI
        The validated OpenAPI model.
    """
    if isinstance(source, OpenAPI):
        return source
    if isinstance(source, str):
        response = httpx.get(source, follow_redirects=True)
        response.raise_for_status()
        source = response.json()
    # ``parse_obj`` inspects the ``openapi`` version string and returns the
    # matching 3.0 or 3.1 model, unlike ``OpenAPI.model_validate`` which is
    # pinned to 3.1.
    return parse_obj(source)


def resolve_ref(openapi: OpenAPI, obj: Reference | Schema | Parameter | None) -> Any:
    """Resolve a ``$ref`` against the document's components.

    Parameters
    ----------
    openapi : OpenAPI
        The document the reference is resolved against.
    obj : Reference or Schema or Parameter or None
        The object to resolve. Non-reference objects are returned unchanged.

    Returns
    -------
    Any
        The referenced component, or ``obj`` if it was not a reference.
    """
    if not isinstance(obj, _REFERENCE_TYPES):
        return obj

    ref = obj.ref
    if not ref.startswith("#/"):
        raise ValueError(f"Only local references are supported, got {ref!r}.")

    node: Any = openapi
    for part in ref.lstrip("#/").split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict):
            node = node[part]
        else:
            # Component containers use the alias names (e.g. ``schemas``) which
            # match the model attribute names, so getattr is sufficient.
            node = getattr(node, part)
        if node is None:
            raise KeyError(f"Could not resolve reference {ref!r}.")
    return resolve_ref(openapi, node) if isinstance(node, _REFERENCE_TYPES) else node


def get_operation(openapi: OpenAPI, path: str, method: str) -> Operation:
    """Return the :class:`Operation` for a path and HTTP method.

    Parameters
    ----------
    openapi : OpenAPI
        The document to look the operation up in.
    path : str
        The templated path, e.g. ``/pets/{petId}``.
    method : str
        The HTTP method, case-insensitive.

    Returns
    -------
    Operation
        The matching operation, with any parameters declared on the path item
        merged into its own.

    Raises
    ------
    KeyError
        If the path is unknown or the method is not defined for it.
    """
    paths = openapi.paths or {}
    if path not in paths:
        available = ", ".join(sorted(paths)) or "none"
        raise KeyError(f"Path {path!r} not found. Available paths: {available}.")

    path_item = paths[path]
    method = method.lower()
    operation = getattr(path_item, method, None)
    if operation is None:
        available = ", ".join(m for m in ("get", "put", "post", "delete", "options", "head", "patch", "trace") if getattr(path_item, m, None) is not None)
        raise KeyError(f"Method {method.upper()!r} not defined for {path!r}. " f"Available methods: {available or 'none'}.")
    return _with_path_parameters(openapi, path_item, operation)


def _parameter_key(openapi: OpenAPI, parameter: Parameter | Reference) -> tuple[str, str]:
    """Identify a parameter the way the spec does, by name and location."""
    resolved = resolve_ref(openapi, parameter)
    location = getattr(resolved.param_in, "value", resolved.param_in)
    return (resolved.name, str(location))


def _with_path_parameters(openapi: OpenAPI, path_item: Any, operation: Operation) -> Operation:
    """Merge parameters declared on the path item into the operation.

    A path item may declare parameters shared by all its operations, which is
    how a hand-written spec usually expresses a path parameter like ``petId``.
    The operation's own parameters win where both declare the same name and
    location, as the specification requires.
    """
    shared = getattr(path_item, "parameters", None)
    if not shared:
        return operation
    own = {_parameter_key(openapi, p) for p in operation.parameters or []}
    inherited = [p for p in shared if _parameter_key(openapi, p) not in own]
    if not inherited:
        return operation
    # A copy, so the document keeps describing what it was given.
    merged = operation.model_copy()
    merged.parameters = [*inherited, *(operation.parameters or [])]
    return merged


def _json_schema(openapi: OpenAPI, content: dict[str, Any] | None) -> Schema | None:
    """Return the schema of the first JSON media type in a content mapping."""
    for media_type in _JSON_MEDIA_TYPES:
        if media_type in (content or {}):
            return resolve_ref(openapi, content[media_type].media_type_schema)
    return None


def _body_schema(openapi: OpenAPI, operation: Operation) -> Schema | None:
    """Return the JSON request body schema for an operation, if any."""
    request_body = resolve_ref(openapi, operation.requestBody)
    if request_body is None:
        return None
    return _json_schema(openapi, request_body.content)


def response_schema(openapi: OpenAPI, operation: Operation) -> Schema | None:
    """Return the JSON schema of an operation's success response.

    The lowest 2xx response that declares a JSON body wins, falling back to a
    ``default`` response. This is the schema of the record a ``GET`` returns,
    which :class:`~panel_openapi.editor.OpenAPIRecordEditor` populates a form
    from.

    Parameters
    ----------
    openapi : OpenAPI
        The document the operation belongs to.
    operation : Operation
        The operation to inspect.

    Returns
    -------
    Schema or None
        The response schema, or ``None`` if the operation declares no JSON
        success response.
    """
    responses = operation.responses or {}
    codes = sorted(str(code) for code in responses if str(code).startswith("2"))
    for code in [*codes, "default"]:
        if code not in responses:
            continue
        response = resolve_ref(openapi, responses[code])
        schema = _json_schema(openapi, getattr(response, "content", None))
        if schema is not None:
            return schema
    return None


# Methods that can update an existing record, in the order they are preferred.
# PATCH is a partial update, PUT a full replace, and POST is only an update by
# convention (some APIs use it to create a subresource instead).
_UPDATE_METHODS = ("patch", "put", "post")


def find_update_operations(openapi: OpenAPI, path: str) -> list[str]:
    """Return the methods on ``path`` that could update the record it returns.

    Only the path is used as evidence, since request and response schemas
    routinely differ for the same record: the Swagger Petstore reuses ``Pet``
    for both, while FastAPI typically responds with a model carrying
    server-assigned fields that the request model omits.

    Parameters
    ----------
    openapi : OpenAPI
        The document to inspect.
    path : str
        The templated path whose operations are considered.

    Returns
    -------
    list of str
        Matching methods, most likely first (``patch``, then ``put``, then
        ``post``). Empty if the path defines none of them.
    """
    path_item = (openapi.paths or {}).get(path)
    if path_item is None:
        return []
    return [method for method in _UPDATE_METHODS if getattr(path_item, method, None) is not None]


def collect_fields(openapi: OpenAPI, operation: Operation, skip_read_only: bool = False) -> list[Field]:
    """Flatten an operation's parameters and JSON body into fields.

    Parameters
    ----------
    openapi : OpenAPI
        The document the operation belongs to.
    operation : Operation
        The operation to introspect.
    skip_read_only : bool
        Whether to drop body properties marked ``readOnly`` entirely. When
        ``False`` they are still returned, flagged via ``Field.read_only`` so
        callers can show them without sending them.

    Returns
    -------
    list of Field
        Ordered descriptors for every path, query, header and body field.
    """
    fields: list[Field] = []

    for parameter in operation.parameters or []:
        parameter = resolve_ref(openapi, parameter)
        location = parameter.param_in.value if hasattr(parameter.param_in, "value") else str(parameter.param_in)
        if location not in ("path", "query", "header"):
            # Cookie parameters are not supported.
            continue
        schema = resolve_ref(openapi, parameter.param_schema) or Schema()
        if parameter.description and not schema.description:
            # A parameter documents itself, while a body property documents
            # itself through its schema. Copy it across so the widget layer only
            # has to look in one place.
            schema = schema.model_copy(update={"description": parameter.description})
        fields.append(
            Field(
                name=parameter.name,
                location=location,  # type: ignore[arg-type]
                schema=schema,
                required=bool(parameter.required),
            )
        )

    body_schema = _body_schema(openapi, operation)
    if body_schema is not None:
        required = set(body_schema.required or [])
        properties = body_schema.properties or {}
        if properties:
            for prop_name, prop_schema in properties.items():
                schema = resolve_ref(openapi, prop_schema) or Schema()
                read_only = bool(schema.readOnly)
                if skip_read_only and read_only:
                    continue
                fields.append(
                    Field(
                        name=prop_name,
                        location="body",
                        schema=schema,
                        required=prop_name in required,
                        read_only=read_only,
                    )
                )
        else:
            # Body without object properties (e.g. free-form object or array):
            # expose a single raw field carrying the whole payload.
            fields.append(
                Field(
                    name="body",
                    location="body",
                    schema=body_schema,
                    required=bool((resolve_ref(openapi, operation.requestBody) or Schema()).required),
                )
            )

    return fields
