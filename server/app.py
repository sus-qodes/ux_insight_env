# server/app.py
# FastAPI server entry point using OpenEnv's create_app factory.
# Uses mandatory dual-import pattern for both in-repo and Docker compatibility.
# Uses OpenEnv's built-in web interface at /web — no custom Gradio UI.

from pathlib import Path

from fastapi.responses import HTMLResponse

try:
    from ..models import UXAction, UXObservation
    from .environment import UXInsightEnvironment
except ImportError:
    from models import UXAction, UXObservation
    from server.environment import UXInsightEnvironment

from openenv.core.env_server import create_app

app = create_app(
    UXInsightEnvironment,    # Pass the CLASS, not an instance
    UXAction,
    UXObservation,
    env_name="ux-insight-env",
)

# ---------------------------------------------------------------------------
# Custom pages — landing page and documentation
# ---------------------------------------------------------------------------

_STATIC = Path(__file__).resolve().parent.parent / "static"


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing_page():
    """Serve the project landing page."""
    return (_STATIC / "index.html").read_text(encoding="utf-8")


@app.get("/documentation", response_class=HTMLResponse, include_in_schema=False)
async def documentation_page():
    """Serve the full documentation page."""
    return (_STATIC / "docs.html").read_text(encoding="utf-8")


def main():
    """Entry point for running the server directly."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
