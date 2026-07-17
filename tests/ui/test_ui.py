"""UI Test Module."""

import pytest

pytest.importorskip("playwright")

from panel.tests.util import serve_component  # noqa: E402
from playwright.sync_api import expect  # noqa: E402

from panel_openapi.form import OpenAPIForm  # noqa: E402

pytestmark = pytest.mark.ui


def test_form_renders(page, petstore_spec):
    """The generated form renders its widgets and a submit button."""
    form = OpenAPIForm(petstore_spec, "https://api.example.com", "/pets/{petId}", "post")

    serve_component(page, form)

    # The body properties should each produce an input.
    expect(page.get_by_text("Submit")).to_be_visible()
    expect(page.locator("input").first).to_be_visible()
