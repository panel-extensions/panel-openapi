"""Regenerate the documentation screenshots.

Serves each snippet in ``docs/snippets`` with Panel and captures it with
Playwright, so every screenshot in the docs shows the code the page embeds.

Run with::

    python docs/screenshots.py

Requires Playwright and its Chromium build::

    pip install playwright && playwright install chromium
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

DOCS = Path(__file__).parent
SNIPPETS = DOCS / "snippets"
OUTPUT = DOCS / "assets" / "screenshots"

# Snippet name -> (viewport, actions performed before the shot).
# Actions run against the served page; each is (label, action) where action is a
# callable taking the Playwright page.
SHOTS: dict[str, dict] = {
    "quickstart": {
        "size": (1200, 640),
        "fill": {"Name": "Ada Lovelace", "age": None},
        "click": "Submit",
    },
    "widget_mapping": {"size": (560, 1080)},
    # Shot after switching, so the form shown is one the selector rebuilt.
    "switch_operation": {"size": (1150, 620), "select": ("Operation", "Add a pet")},
    "custom_layout": {"size": (1250, 660), "fill": {"message": "Hello"}, "click": "Submit"},
    "authentication": {"size": (1150, 640), "click": "Submit"},
    "record_editor": {"size": (900, 750)},
    "build_your_own": {"size": (1250, 700), "click": "Preview request"},
}


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("", 0))
        return int(sock.getsockname()[1])


def capture(name: str, config: dict) -> Path:
    """Serve one snippet and screenshot it."""
    port = free_port()
    path = SNIPPETS / f"{name}.py"
    server = subprocess.Popen(
        [sys.executable, "-m", "panel", "serve", str(path), "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    target = OUTPUT / f"{name}.png"
    try:
        time.sleep(6)
        width, height = config["size"]
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=2)
            page.goto(f"http://localhost:{port}/{name}", wait_until="networkidle")
            # Panel renders after the websocket connects, which networkidle
            # does not wait for.
            page.wait_for_timeout(5000)
            if "select" in config:
                label, option = config["select"]
                page.get_by_label(label, exact=False).first.click()
                page.wait_for_timeout(600)
                page.get_by_text(option, exact=True).first.click()
                page.wait_for_timeout(2000)
            for label, value in config.get("fill", {}).items():
                if value is None:
                    continue
                field = page.get_by_label(label, exact=False).first
                field.fill(value)
                field.press("Tab")
                page.wait_for_timeout(400)
            if "click" in config:
                page.get_by_text(config["click"], exact=True).first.click()
                # Long enough for a live request to come back.
                page.wait_for_timeout(4000)
            page.screenshot(path=str(target))
            browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)
    return target


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    names = sys.argv[1:] or list(SHOTS)
    for name in names:
        target = capture(name, SHOTS[name])
        size = target.stat().st_size // 1024
        print(f"{target.relative_to(DOCS.parent)} ({size} KB)")


if __name__ == "__main__":
    main()
