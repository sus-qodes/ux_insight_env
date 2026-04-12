import asyncio

try:
    from ... import inference
    from ... import client as client_module
except ImportError:
    import inference
    import client as client_module


def test_clamp_task_score_stays_strictly_in_range():
    assert inference.clamp_task_score(-5.0) == 0.01
    assert inference.clamp_task_score(0.0) == 0.01
    assert inference.clamp_task_score(0.42) == 0.42
    assert inference.clamp_task_score(1.0) == 0.99
    assert inference.clamp_task_score(7.0) == 0.99


def test_run_task_failure_path_still_returns_strict_score(monkeypatch):
    class DummyOpenAI:
        def __init__(self, *args, **kwargs):
            pass

    class BrokenEnv:
        def __init__(self, base_url=None):
            self.base_url = base_url

        async def connect(self):
            raise RuntimeError("simulated connect failure")

        async def close(self):
            return None

    monkeypatch.setattr(inference, "OpenAI", DummyOpenAI)
    monkeypatch.setattr(inference, "resolve_api_key", lambda: "test-token")
    monkeypatch.setattr(client_module, "UXInsightEnv", BrokenEnv)

    result = asyncio.run(inference.run_task("easy", model_name="dummy/model"))

    assert 0.0 < result["score"] < 1.0
    assert result["score"] == 0.01
    assert result["error"] == "simulated connect failure"
