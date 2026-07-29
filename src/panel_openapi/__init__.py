"""Accessible imports for the panel_openapi package."""

import importlib.metadata
import warnings

from panel_openapi.editor import OpenAPIRecordEditor
from panel_openapi.form import OpenAPIForm
from panel_openapi.main import create_app
from panel_openapi.schema import Field
from panel_openapi.schema import collect_fields
from panel_openapi.schema import find_update_operations
from panel_openapi.schema import get_operation
from panel_openapi.schema import load_openapi
from panel_openapi.schema import response_schema
from panel_openapi.widgets import schema_to_widget

try:
    __version__ = importlib.metadata.version(__name__)
except importlib.metadata.PackageNotFoundError as e:  # pragma: no cover
    warnings.warn(f"Could not determine version of {__name__}\n{e!s}", stacklevel=2)
    __version__ = "unknown"

__all__: list[str] = [
    "Field",
    "OpenAPIForm",
    "OpenAPIRecordEditor",
    "__version__",
    "collect_fields",
    "create_app",
    "find_update_operations",
    "get_operation",
    "load_openapi",
    "response_schema",
    "schema_to_widget",
]
