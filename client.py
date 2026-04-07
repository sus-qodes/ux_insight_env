# client.py - EnvClient implementation for training code
# Used to connect to the UX Insight Analyst environment remotely.

from typing import Any, Dict

from openenv.core.env_client import EnvClient, StepResult

try:
    from .models import UXAction, UXObservation, UXState
except ImportError:
    from models import UXAction, UXObservation, UXState


class UXInsightEnv(EnvClient):
    """Client for connecting to the UX Insight Analyst environment."""

    env_name = "ux-insight-env"
    Action = UXAction
    Observation = UXObservation

    def _step_payload(self, action: UXAction) -> Dict[str, Any]:
        return action.model_dump()

    def _parse_result(self, payload: Dict[str, Any]) -> StepResult[UXObservation]:
        observation_data = payload.get("observation", {})
        reward = payload.get("reward")
        done = bool(payload.get("done", False))

        observation = UXObservation.model_validate(observation_data)
        observation.reward = reward
        observation.done = done

        return StepResult(observation=observation, reward=reward, done=done)

    def _parse_state(self, payload: Dict[str, Any]) -> UXState:
        return UXState.model_validate(payload)
