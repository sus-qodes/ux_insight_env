# server/app.py
# FastAPI server entry point using OpenEnv's create_app factory.
# Uses mandatory dual-import pattern for both in-repo and Docker compatibility.
# Uses OpenEnv's built-in web interface at /web — no custom Gradio UI.

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


def main():
    """Entry point for running the server directly."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
