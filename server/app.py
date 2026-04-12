# server/app.py
# FastAPI server entry point using OpenEnv's create_app factory.
# Uses mandatory dual-import pattern for both in-repo and Docker compatibility.
# Web interface is pure HTML/JavaScript served at /web (no Gradio).

from pathlib import Path
from fastapi.responses import HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware

try:
    from ..models import UXAction, UXObservation
    from .environment import UXInsightEnvironment
except ImportError:
    from models import UXAction, UXObservation
    from server.environment import UXInsightEnvironment

from openenv.core.env_server import create_app

# Import the recommendation generator
try:
    from .environment import _generate_recommendation, _generate_impact_estimate
except ImportError:
    from server.environment import _generate_recommendation, _generate_impact_estimate

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
_LANDING_HTML = (_STATIC / "index.html").read_text(encoding="utf-8")
_OVERVIEW_HTML = (_STATIC / "overview.html").read_text(encoding="utf-8")
_PLAYGROUND_HTML = (_STATIC / "playground.html").read_text(encoding="utf-8")
_DOCS_HTML = (_STATIC / "docs.html").read_text(encoding="utf-8")
_CUSTOM_PLAYGROUND_HTML = (_STATIC / "custom-playground.html").read_text(encoding="utf-8")

# Remove OpenEnv's default routes (gradiio ui) ONLY for "/" to use our landing page
# Keep "/config" and other endpoints available
_EXCLUDED_PATHS = {"/"}  # Only exclude "/" root, preserve OpenEnv's other UI routes
app.router.routes = [
    r for r in app.router.routes
    if not (hasattr(r, "path") and r.path in _EXCLUDED_PATHS)
]

# ---------------------------------------------------------------------------
# Middleware to inject navbar into Gradio routes (/web and /config)
# ---------------------------------------------------------------------------

class NavbarInjectionMiddleware(BaseHTTPMiddleware):
    """Injects navbar CSS and script into HTML responses for Gradio routes."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Only process HTML responses from /web and /config
        if request.url.path not in ["/web", "/config"]:
            return response

        # Check if response has content-type of text/html
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:
            return response

        try:
            # Read the response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            html_content = body.decode("utf-8")

            # Inject navbar CSS link in <head>
            navbar_css = '<link rel="stylesheet" href="/static/css/navbar.css">'
            html_content = html_content.replace("</head>", f"{navbar_css}\n</head>")

            # Inject navbar script before closing </body>
            navbar_script = '<script src="/static/js/navbar.js"></script>'
            html_content = html_content.replace("</body>", f"{navbar_script}\n</body>")

            # Return modified response
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=html_content, status_code=response.status_code)
        except Exception as e:
            # If injection fails, return original response
            return response

# Add middleware to the app
app.add_middleware(NavbarInjectionMiddleware)

# ---------------------------------------------------------------------------
# Custom pages — landing page, playground, and documentation
# Registered AFTER filtering to take priority
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def landing_page():
    """Serve the landing page with space theme and navigation buttons."""
    return _LANDING_HTML


@app.get("/overview", response_class=HTMLResponse, include_in_schema=False)
async def overview_page():
    """Serve the project overview page with full documentation and demo info."""
    return _OVERVIEW_HTML


@app.get("/web", response_class=HTMLResponse, include_in_schema=False)
async def playground_page():
    """Serve the interactive playground for testing the environment."""
    return _PLAYGROUND_HTML


@app.get("/documentation", response_class=HTMLResponse, include_in_schema=False)
async def documentation_page():
    """Serve the full API and usage documentation."""
    return _DOCS_HTML


@app.get("/custom-playground", response_class=HTMLResponse, include_in_schema=False)
async def custom_playground_page():
    """Serve the custom interactive playground."""
    return _CUSTOM_PLAYGROUND_HTML


@app.get("/ground_truth", include_in_schema=False)
async def get_ground_truth():
    """
    (Teaching mode) Returns the ground truth/expected answer for current page.
    Used by the playground to auto-fill forms for learning purposes.
    """
    # Get the shared env instance from the OpenEnv framework
    # This works because create_app() sets up a singleton environment manager
    try:
        from openenv.core.env_server import get_env_instance
        env = get_env_instance()

        if not env or not hasattr(env, '_current_step') or not hasattr(env, '_embedded_problems'):
            return {"error": "No active episode"}

        if env._current_step >= len(env._pages_data):
            return {"error": "Episode complete"}

        current_page = env._pages_data[env._current_step].page_name

        # Find ground truth for this page
        problems = [p for p in env._embedded_problems
                   if p.get("affected_page") == current_page and not p.get("red_herring")]

        if problems:
            p = problems[0]
            return {
                "finding_type": "issue",
                "affected_element": p.get("affected_element", "Unknown Element"),
                "issue_category": p.get("problem_type", "normal_behavior"),
                "severity": p.get("severity", "medium"),
                "recommendation": _generate_recommendation(p),
                "fix_category": p.get("expected_fix_category", "redesign_element"),
                "impact_estimate": _generate_impact_estimate(p),
                "confidence": 0.95
            }
        else:
            return {
                "finding_type": "no_issue",
                "affected_element": "N/A",
                "issue_category": "normal_behavior",
                "severity": "none",
                "recommendation": "No fix required",
                "fix_category": "no_fix_needed",
                "impact_estimate": "Normal engagement metrics",
                "confidence": 0.95
            }
    except Exception as e:
        return {"error": str(e)}


def main():
    """Entry point for running the server directly."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
