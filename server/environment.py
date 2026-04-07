# server/environment.py
# Core environment class implementing the OpenEnv 3-method interface:
#   reset() -> UXObservation
#   step(action: UXAction) -> UXObservation with inherited reward/done fields
#   state (property) -> UXState

try:
    from ..models import UXAction, UXObservation, UXState, FindingEntry, PageAnalyticsData
except ImportError:
    from models import UXAction, UXObservation, UXState, FindingEntry, PageAnalyticsData

from openenv.core.env_server import Environment

try:
    from .data_generator import generate_episode_data
    from .grader import grade_step, compute_step_reward, grade_episode, generate_grader_feedback
except ImportError:
    from server.data_generator import generate_episode_data
    from server.grader import grade_step, compute_step_reward, grade_episode, generate_grader_feedback

import random
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TASK_IDS = ["easy", "medium", "hard"]
MAX_STEPS_BY_TASK = {"easy": 1, "medium": 3, "hard": 6}

TASK_DESCRIPTIONS = {
    "easy": (
        "Analyze the provided analytics data for ONE page and identify any UX issues. "
        "If the data shows normal behavior, report it as 'no_issue'. "
        "Submit your finding using the structured action format."
    ),
    "medium": (
        "Analyze analytics data across THREE pages sequentially. "
        "Identify all UX issues, correctly assess their severity, and be prepared to explain their relative priority. "
        "Submit one structured finding per page."
    ),
    "hard": (
        "Conduct a full funnel UX audit across SIX pages. "
        "Identify real problems, correctly dismiss red herrings (normal behaviors that look like problems), "
        "resolve conflicting signals, and provide impact-estimated recommendations for each page. "
        "Not every anomalous metric is a problem — think critically."
    ),
}


class UXInsightEnvironment(Environment):
    """
    UX Insight Analyst — an RL environment that simulates the job of a UX analyst
    at an e-commerce company reviewing behavioral analytics data.
    """

    def __init__(self):
        self._pages_data: list = []
        self._embedded_problems: list = []
        self._current_step: int = 0
        self._task_id: str = "easy"
        self._task_seed: int = 0
        self._findings: list = []
        self._episode_rewards: list = []
        self._is_done: bool = False

    # ------------------------------------------------------------------
    # reset()
    # ------------------------------------------------------------------

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        task_id: Optional[str] = None,
        **kwargs: Any,
    ) -> UXObservation:
        """Reset environment and start a new episode."""
        requested_task = task_id or (episode_id if episode_id in TASK_IDS else None)
        self._task_id = requested_task if requested_task in TASK_IDS else random.choice(TASK_IDS)
        self._task_seed = int(seed) if seed is not None else random.randint(0, 999999)
        self._current_step = 0
        self._findings = []
        self._episode_rewards = []
        self._is_done = False

        # Generate deterministic episode data
        self._pages_data, self._embedded_problems = generate_episode_data(
            seed=self._task_seed,
            task_id=self._task_id,
        )

        return UXObservation(
            task_id=self._task_id,
            task_description=TASK_DESCRIPTIONS[self._task_id],
            current_step=1,
            total_steps=MAX_STEPS_BY_TASK[self._task_id],
            pages_to_analyze=[p.page_name for p in self._pages_data],
            current_page_data=self._pages_data[0],
            findings_so_far=[],
            cumulative_score=0.0,
            grader_feedback="",
            task_context={
                "app_name": "StyleMart E-Commerce Platform",
                "date_range": "Last 7 days",
                "total_app_sessions": sum(p.total_sessions for p in self._pages_data),
                "primary_device": "Mobile (67% of traffic)",
            },
            done=False,
            reward=None,
        )

    # ------------------------------------------------------------------
    # step()
    # ------------------------------------------------------------------

    def step(
        self,
        action: UXAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> UXObservation:
        """Process one step — agent submits a finding for the current page."""
        if not self._pages_data:
            # HTTP /step is stateless in OpenEnv's FastAPI helper. Auto-reset
            # prevents a validation-time 500; WebSocket sessions keep state.
            self.reset(
                seed=kwargs.get("seed"),
                episode_id=kwargs.get("episode_id"),
                task_id=kwargs.get("task_id"),
            )

        if self._is_done:
            obs = self._build_observation(
                done=True,
                reward=-0.1,
                feedback="Episode is already complete. Call reset() to start a new episode.",
                info={"error": "episode_done", "terminal_reason": "completed"},
            )
            return obs

        # Validate step index
        if self._current_step >= len(self._pages_data):
            self._is_done = True
            obs = self._build_observation(
                done=True,
                reward=-0.1,
                feedback="No more pages are available to analyze. Call reset() to start a new episode.",
                info={"error": "no_pages_remaining", "terminal_reason": "max_steps_reached"},
            )
            return obs

        current_page = self._pages_data[self._current_step]
        problems_on_page = [
            p for p in self._embedded_problems
            if p["affected_page"] == current_page.page_name
        ]

        # Grade this step
        validation_error = self._validate_action(action)
        if validation_error:
            step_grade = 0.0
            step_reward = -0.2
        else:
            try:
                step_grade = grade_step(action, problems_on_page, current_page.page_name)
                step_reward = compute_step_reward(step_grade, action, self._build_state())
            except Exception:
                # Fallback: if grading crashes, keep the episode alive with a deterministic penalty.
                step_grade = 0.0
                step_reward = -0.1

        if validation_error:
            feedback = f"Invalid action rejected: {validation_error}. Score: 0.00"
        else:
            feedback = generate_grader_feedback(step_grade, action, problems_on_page)

        # Record finding
        finding = FindingEntry(
            step=self._current_step + 1,
            page_analyzed=current_page.page_name,
            finding_type=action.finding_type,
            affected_element=action.affected_element,
            issue_category=action.issue_category,
            severity=action.severity,
            recommendation=action.recommendation,
            fix_category=action.fix_category,
            impact_estimate=action.impact_estimate,
            confidence=action.confidence,
            step_reward=step_reward,
        )
        self._findings.append(finding)
        self._episode_rewards.append(step_reward)
        self._current_step += 1

        # Check if episode is done
        done = self._current_step >= len(self._pages_data)

        # Compute final bonus if done
        final_bonus = 0.0
        if done:
            self._is_done = True
            try:
                final_bonus = grade_episode(self._build_state(), self._task_id)
            except Exception:
                final_bonus = 0.0
            self._episode_rewards.append(final_bonus)

        # Cumulative score normalized to [0, 1]
        max_steps = MAX_STEPS_BY_TASK.get(self._task_id, 1)
        cumulative_score = min(
            max(sum(self._episode_rewards) / max_steps, 0.0),
            1.0,
        )

        info = {
            "step_grade": step_grade,
            "step_reward": step_reward,
            "final_bonus": final_bonus,
            "cumulative_score": cumulative_score,
            "grader_feedback": feedback,
        }
        if validation_error:
            info["error"] = "invalid_action"
            info["reason"] = validation_error
        if done:
            info["terminal_reason"] = "completed"

        obs = self._build_observation(
            done=done,
            reward=step_reward + final_bonus,
            feedback=feedback,
            cumulative_score=cumulative_score,
            info=info,
        )
        return obs

    def _validate_action(self, action: UXAction) -> Optional[str]:
        allowed_issue_categories = {
            "rage_click",
            "dead_click",
            "funnel_dropoff",
            "scroll_dropoff",
            "mobile_layout_break",
            "quickback",
            "form_abandonment",
            "cta_invisible",
            "search_no_results",
            "high_bounce",
            "normal_behavior",
            "unclear",
        }
        allowed_fix_categories = {
            "redesign_element",
            "reposition_element",
            "fix_broken_link",
            "improve_copy",
            "add_feedback",
            "reduce_steps",
            "increase_contrast",
            "add_loading_state",
            "fix_mobile_layout",
            "no_fix_needed",
            "investigate_further",
        }
        if action.issue_category not in allowed_issue_categories:
            return f"unsupported issue_category '{action.issue_category}'"
        if action.fix_category not in allowed_fix_categories:
            return f"unsupported fix_category '{action.fix_category}'"
        if action.finding_type == "no_issue" and action.severity != "none":
            return "no_issue findings must use severity 'none'"
        if action.finding_type == "issue" and action.fix_category == "no_fix_needed":
            return "issue findings must provide an actionable fix_category"
        return None

    def _build_observation(
        self,
        done: bool,
        reward: Optional[float],
        feedback: str,
        cumulative_score: Optional[float] = None,
        info: Optional[dict] = None,
    ) -> UXObservation:
        if not self._pages_data:
            self.reset()

        if not done and self._current_step < len(self._pages_data):
            page_data = self._pages_data[self._current_step]
        else:
            page_data = self._pages_data[-1]

        if cumulative_score is None:
            max_steps = MAX_STEPS_BY_TASK.get(self._task_id, 1)
            cumulative_score = min(max(sum(self._episode_rewards) / max_steps, 0.0), 1.0)

        obs = UXObservation(
            task_id=self._task_id,
            task_description=(
                f"Step {self._current_step + 1} of {len(self._pages_data)}"
                if not done
                else f"Episode complete. {len(self._pages_data)} pages analyzed."
            ),
            current_step=self._current_step + 1 if not done else self._current_step,
            total_steps=MAX_STEPS_BY_TASK[self._task_id],
            pages_to_analyze=[p.page_name for p in self._pages_data],
            current_page_data=page_data,
            findings_so_far=self._findings,
            cumulative_score=cumulative_score,
            grader_feedback=feedback,
            task_context={
                "app_name": "StyleMart E-Commerce Platform",
                "date_range": "Last 7 days",
                "total_app_sessions": sum(p.total_sessions for p in self._pages_data),
                "primary_device": "Mobile (67% of traffic)",
            },
            done=done,
            reward=reward,
        )
        obs.metadata = info or {}
        return obs

    # ------------------------------------------------------------------
    # state (property)
    # ------------------------------------------------------------------

    @property
    def state(self) -> UXState:
        return self._build_state()

    def _build_state(self) -> UXState:
        return UXState(
            current_step=self._current_step,
            task_id=self._task_id,
            task_seed=self._task_seed,
            embedded_problems=[p["problem_id"] for p in self._embedded_problems],
            pages_sequence=[p.page_name for p in self._pages_data],
            findings_submitted=self._findings,
            episode_rewards=self._episode_rewards,
            total_reward_so_far=sum(self._episode_rewards),
            is_done=self._is_done,
        )
