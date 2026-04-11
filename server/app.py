# server/app.py
# FastAPI server entry point using OpenEnv's create_app factory.
# Uses mandatory dual-import pattern for both in-repo and Docker compatibility.
# Web interface is pure HTML/JavaScript served at /web (no Gradio).

from pathlib import Path
from fastapi.responses import HTMLResponse

try:
    from ..models import UXAction, UXObservation
    from .environment import UXInsightEnvironment
except ImportError:
    from models import UXAction, UXObservation
    from server.environment import UXInsightEnvironment

from openenv.core.env_server import create_app

# Create base app
app = create_app(
    UXInsightEnvironment,    # Pass the CLASS, not an instance
    UXAction,
    UXObservation,
    env_name="ux-insight-env",
)

# Resolve static directory - works in both local and Docker contexts
_STATIC = Path(__file__).resolve().parent.parent / "static"

# Ensure static directory exists
if not _STATIC.exists():
    _STATIC.mkdir(parents=True, exist_ok=True)

# Read HTML files upfront to serve via routes (avoids static file mount issues)
_INDEX_HTML = (_STATIC / "index.html").read_text(encoding="utf-8")
_PLAYGROUND_HTML = (_STATIC / "playground.html").read_text(encoding="utf-8")
_DOCS_HTML = (_STATIC / "docs.html").read_text(encoding="utf-8")

# Remove OpenEnv's default routes (gradiio ui) to use our custom pages
# Filter out paths that conflict with our custom UI
_EXCLUDED_PATHS = {"/", "/web", "/documentation", "/config"}
app.router.routes = [
    r for r in app.router.routes
    if not (hasattr(r, "path") and r.path in _EXCLUDED_PATHS)
]

# ---------------------------------------------------------------------------
# Custom pages — landing page, playground, and documentation
# Registered AFTER filtering to take priority
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing_page():
    """Serve the project landing page with full documentation and demo info."""
    return _INDEX_HTML


@app.get("/web", response_class=HTMLResponse, include_in_schema=False)
async def playground_page():
    """Serve the interactive playground for testing the environment."""
    return _PLAYGROUND_HTML


@app.get("/documentation", response_class=HTMLResponse, include_in_schema=False)
async def documentation_page():
    """Serve the full API and usage documentation."""
    return _DOCS_HTML


def main():
    """Entry point for running the server directly."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
