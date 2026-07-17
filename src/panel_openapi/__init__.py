"""Accessible imports for the panel_openapi package."""

import importlib.metadata
import warnings

from panel_openapi.form import OpenAPIForm
from panel_openapi.main import create_app
from panel_openapi.schema import Field, collect_fields, get_operation, load_openapi
from panel_openapi.widgets import schema_to_widget

try:
    __version__ = importlib.metadata.version(__name__)
except importlib.metadata.PackageNotFoundError as e:  # pragma: no cover
    warnings.warn(f"Could not determine version of {__name__}\n{e!s}", stacklevel=2)
    __version__ = "unknown"

__all__: list[str] = [
    "Field",
    "OpenAPIForm",
    "__version__",
    "collect_fields",
    "create_app",
    "get_operation",
    "load_openapi",
    "schema_to_widget",
]
