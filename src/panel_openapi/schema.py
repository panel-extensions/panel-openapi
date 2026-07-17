"""Load and introspect OpenAPI documents.

This module wraps :mod:`openapi_pydantic` to load an OpenAPI schema from a URL
or dictionary, resolve ``$ref`` references, locate a specific operation and
flatten its parameters and JSON request body into a list of field descriptors
that the widget layer can turn into inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import httpx
from openapi_pydantic import OpenAPI, Operation, Parameter, Reference, Schema, parse_obj
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
    """

    name: str
    location: FieldLocation
    schema: Schema
    required: bool = False


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


def resolve_ref(
    openapi: OpenAPI, obj: Reference | Schema | Parameter | None
) -> Any:
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
        The matching operation.

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
        available = ", ".join(
            m for m in ("get", "put", "post", "delete", "options", "head", "patch", "trace")
            if getattr(path_item, m, None) is not None
        )
        raise KeyError(
            f"Method {method.upper()!r} not defined for {path!r}. "
            f"Available methods: {available or 'none'}."
        )
    return operation


def _body_schema(openapi: OpenAPI, operation: Operation) -> Schema | None:
    """Return the JSON request body schema for an operation, if any."""
    request_body = resolve_ref(openapi, operation.requestBody)
    if request_body is None:
        return None
    content = request_body.content or {}
    for media_type in _JSON_MEDIA_TYPES:
        if media_type in content:
            return resolve_ref(openapi, content[media_type].media_type_schema)
    return None


def collect_fields(openapi: OpenAPI, operation: Operation) -> list[Field]:
    """Flatten an operation's parameters and JSON body into fields.

    Parameters
    ----------
    openapi : OpenAPI
        The document the operation belongs to.
    operation : Operation
        The operation to introspect.

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
                fields.append(
                    Field(
                        name=prop_name,
                        location="body",
                        schema=resolve_ref(openapi, prop_schema) or Schema(),
                        required=prop_name in required,
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
