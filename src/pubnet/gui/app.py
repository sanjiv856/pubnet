"""Dash app factory for PubNet GUI.

Usage:
    app = create_app()
    app.run(port=8050, debug=True)

    # Or with a pre-loaded profile:
    app = create_app(scholar_url="https://scholar.google.com/citations?user=ML7X29AAAAAJ")
"""

from __future__ import annotations

import os

import dash

from pubnet.gui.layouts import build_layout
from pubnet.gui.callbacks import register_callbacks

# Assets directory lives alongside this module
_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def create_app(scholar_url: str | None = None) -> dash.Dash:
    """Create and configure the PubNet Dash application.

    Args:
        scholar_url: Optional Scholar URL to pre-load on startup.

    Returns:
        Configured Dash app ready to run.
    """
    app = dash.Dash(
        __name__,
        title="PubNet",
        update_title="PubNet - Loading...",
        suppress_callback_exceptions=True,
        assets_folder=_ASSETS_DIR,
    )

    app.layout = build_layout(scholar_url=scholar_url)
    register_callbacks(app)

    return app


# Allow running directly: python -m pubnet.gui.app
if __name__ == "__main__":
    app = create_app()
    app.run(port=8050, debug=True)
