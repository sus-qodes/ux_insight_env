# server/rubrics.py
# RFC 004 Rubric exposure for OpenEnv RL training framework integration
# Allows training frameworks (GRPO, etc.) to access reward computation cleanly

from typing import Any, Optional

try:
    from ..models import UXAction, UXObservation
except ImportError:
    from models import UXAction, UXObservation


# ---------------------------------------------------------------------------
# Base Rubric Class (mimics OpenEnv rubric interface)
# ---------------------------------------------------------------------------


class Rubric:
    """Base rubric class for scoring actions."""

    def forward(self, action: Any, observation: Any) -> float:
        """
        Score an action given the current observation.

        Args:
            action: The agent's UXAction
            observation: The UXObservation (includes metadata with step_reward)

        Returns:
            float: Score in [-0.5, 1.0]
        """
        raise NotImplementedError

    def __call__(self, action: Any, observation: Any) -> float:
        """Allow rubric to be called as a function."""
        return self.forward(action, observation)

    def reset(self):
        """Optional: reset any internal state (for stateful rubrics)."""
        pass


# ---------------------------------------------------------------------------
# Component Rubrics
# ---------------------------------------------------------------------------


class UXOutcomeRubric(Rubric):
    """
    Score the outcome (correctness) of the action.
    Based on per-step grade + anti-exploit penalties.
    """

    def forward(self, action: UXAction, observation: UXObservation) -> float:
        """
        Extract the step reward from observation metadata.
        This is the per-step score after grading and anti-exploit penalties.
        """
        if not hasattr(observation, "metadata") or observation.metadata is None:
            return 0.0

        step_reward = observation.metadata.get("step_reward", 0.0)
        return max(min(step_reward, 1.0), -0.5)


class UXProcessRubric(Rubric):
    """
    Score the process of arriving at the action.
    Currently a placeholder for future process-based training.
    """

    def forward(self, action: UXAction, observation: UXObservation) -> float:
        """Process rubric: currently unused, returns 0.0."""
        return 0.0


class UXAmbigiousFindingBonus(Rubric):
    """
    Bonus for admitting uncertainty when signal is ambiguous.
    Rewards "ambiguous" finding_type on borderline cases.
    """

    def forward(self, action: UXAction, observation: UXObservation) -> float:
        """
        Return small bonus if agent marked finding as ambiguous.
        This encourages epistemic humility rather than overconfidence.
        """
        if action.finding_type == "ambiguous":
            return 0.05  # Small bonus for uncertainty
        return 0.0


# ---------------------------------------------------------------------------
# Composite Rubric (main entry point)
# ---------------------------------------------------------------------------


class UXAnalystRubric(Rubric):
    """
    Composite rubric combining outcome scoring and process evaluation.

    - On terminal steps (done=True): uses outcome rubric
    - On non-terminal steps: uses process rubric (currently 0.0)
    - Can be extended for future process-based training
    """

    def __init__(
        self,
        outcome: Optional[Rubric] = None,
        process: Optional[Rubric] = None,
        ambiguous_bonus: Optional[Rubric] = None,
    ):
        """
        Initialize the composite rubric.

        Args:
            outcome: Rubric for scoring correctness. Defaults to UXOutcomeRubric()
            process: Rubric for scoring process. Defaults to UXProcessRubric()
            ambiguous_bonus: Rubric for rewarding uncertainty. Defaults to UXAmbigiousFindingBonus()
        """
        self.outcome = outcome or UXOutcomeRubric()
        self.process = process or UXProcessRubric()
        self.ambiguous_bonus = ambiguous_bonus or UXAmbigiousFindingBonus()

    def forward(self, action: UXAction, observation: UXObservation) -> float:
        """
        Compute composite reward signal.

        Returns:
            - On done=True: outcome score (+ small ambiguous bonus if applicable)
            - On done=False: process score (+ small ambiguous bonus if applicable)
        """
        if observation.done:
            # Terminal step: use outcome score
            outcome_score = self.outcome(action, observation)
        else:
            # Non-terminal step: use process score
            outcome_score = self.process(action, observation)

        # Small bonus for ambiguous findings (within bounds)
        ambiguous_bonus = self.ambiguous_bonus(action, observation)

        combined = outcome_score + ambiguous_bonus
        return max(min(combined, 1.0), -0.5)

    def reset(self):
        """Reset internal state of all component rubrics."""
        if hasattr(self.outcome, "reset"):
            self.outcome.reset()
        if hasattr(self.process, "reset"):
            self.process.reset()
        if hasattr(self.ambiguous_bonus, "reset"):
            self.ambiguous_bonus.reset()


# ---------------------------------------------------------------------------
# Rubric Presets (for different training configurations)
# ---------------------------------------------------------------------------


def create_outcome_focused_rubric() -> UXAnalystRubric:
    """Create rubric optimized for outcome-based training (default)."""
    return UXAnalystRubric(
        outcome=UXOutcomeRubric(),
        process=UXProcessRubric(),
    )


def create_process_aware_rubric() -> UXAnalystRubric:
    """
    Create rubric that could support process-based training.
    (Future enhancement: implement process rubric with intermediate signals)
    """
    return UXAnalystRubric(
        outcome=UXOutcomeRubric(),
        process=UXProcessRubric(),  # Placeholder for future enhancements
    )


# Singleton default rubric
_default_rubric = UXAnalystRubric()


def get_default_rubric() -> UXAnalystRubric:
    """Get the default rubric instance."""
    return _default_rubric
