# models.py — Pydantic Type Definitions for UX Insight Analyst Environment
# Extends OpenEnv base types: Action, Observation, State

from openenv.core.env_server import Action, Observation, State
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional


# ---------------------------------------------------------------------------
# Sub-models for nested analytics data
# ---------------------------------------------------------------------------

class HeatmapZone(BaseModel):
    """Click-density zone on a page heatmap."""
    zone_name: str                                      # e.g. "hero_banner", "nav_bar"
    click_density_pct: float                            # 0.0–1.0 fraction of clicks
    scroll_depth_reached_pct: Optional[float] = None    # % of users who scrolled here


class FunnelStep(BaseModel):
    """One step in a conversion funnel (e.g. checkout flow)."""
    step_name: str                                      # e.g. "add_to_cart", "payment"
    sessions_entered: int
    sessions_dropped: int
    dropoff_rate: float                                 # 0.0–1.0


class BehavioralSignal(BaseModel):
    """A single behavioral analytics signal for an element."""
    signal_type: str                                    # "rage_click", "dead_click", etc.
    affected_element: str                               # Specific UI element name
    rate: float                                         # Fraction of sessions
    session_count: int                                  # Absolute session count


class PageAnalyticsData(BaseModel):
    """Full analytics payload for one page of the simulated e-commerce app."""
    page_name: str
    page_url_pattern: str                               # e.g. "/products/{id}"
    total_sessions: int
    avg_session_duration_seconds: float
    bounce_rate: float
    scroll_depth_p50: float                             # 50th-percentile scroll depth %
    scroll_depth_p80: float
    mobile_sessions_pct: float
    mobile_bounce_rate: float
    desktop_bounce_rate: float
    heatmap_zones: List[HeatmapZone]
    behavioral_signals: List[BehavioralSignal]
    funnel_steps: Optional[List[FunnelStep]] = None
    session_recording_summary: str                      # NL summary of session patterns


class FindingEntry(BaseModel):
    """One finding submitted by the agent during an episode."""
    step: int
    page_analyzed: str
    finding_type: Literal["issue", "no_issue", "ambiguous"]
    affected_element: str
    issue_category: str
    severity: Literal["critical", "high", "medium", "low", "none"]
    recommendation: str
    fix_category: str
    impact_estimate: str
    confidence: float
    step_reward: float                                  # Reward received for this finding


# ---------------------------------------------------------------------------
# Core OpenEnv types
# ---------------------------------------------------------------------------

class UXAction(Action):
    """
    The agent's structured finding for the current page being analyzed.
    Every field must be filled — the grader uses all of them.
    """
    finding_type: Literal["issue", "no_issue", "ambiguous"] = Field(
        ...,
        description=(
            "'issue' = real UX problem found. "
            "'no_issue' = data is normal (use for red herrings). "
            "'ambiguous' = signal is unclear."
        ),
    )
    affected_element: str = Field(
        ...,
        description=(
            "Name of the specific UI element with the problem. "
            "E.g. 'Add to Cart button', 'Checkout pincode field'. "
            "Use 'N/A' if no_issue."
        ),
    )
    issue_category: str = Field(
        ...,
        description=(
            "Category from: rage_click, dead_click, funnel_dropoff, "
            "scroll_dropoff, mobile_layout_break, quickback, form_abandonment, "
            "cta_invisible, search_no_results, normal_behavior, unclear"
        ),
    )
    severity: Literal["critical", "high", "medium", "low", "none"] = Field(
        ...,
        description="Severity of the issue. Use 'none' for no_issue findings.",
    )
    recommendation: str = Field(
        ...,
        description=(
            "Specific, actionable recommendation. Must mention the element name "
            "and the specific change to make. Min 20 words."
        ),
    )
    fix_category: str = Field(
        ...,
        description=(
            "One of: redesign_element, reposition_element, fix_broken_link, "
            "improve_copy, add_feedback, reduce_steps, increase_contrast, "
            "add_loading_state, fix_mobile_layout, no_fix_needed, investigate_further"
        ),
    )
    impact_estimate: str = Field(
        ...,
        description=(
            "Expected metric impact of the fix. "
            "E.g. 'Expected 15-25% reduction in checkout abandonment rate'. "
            "Use 'N/A' if no_issue."
        ),
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Agent's confidence in this finding, 0.0 to 1.0.",
    )


class UXObservation(Observation):
    """
    What the agent can see at each step.
    `done` and `reward` are INHERITED from Observation base class — do NOT redefine.
    """
    task_id: str                                        # "easy", "medium", or "hard"
    task_description: str                               # Plain English task description
    current_step: int                                   # Which step (1-indexed)
    total_steps: int                                    # Total steps in episode
    pages_to_analyze: List[str]                         # Page names (not full data)
    current_page_data: PageAnalyticsData                # Analytics for THIS step's page
    findings_so_far: List[FindingEntry]                 # Agent's prior findings
    cumulative_score: float                             # Running score 0.0–1.0
    grader_feedback: str                                # Feedback on PREVIOUS step
    task_context: Dict[str, Any]                        # App metadata
    ground_truth: Optional[Dict[str, Any]] = None       # Expected answer (for teaching playground)


class UXState(State):
    """Internal state — returned by the state() property. Hidden from agent."""
    current_step: int
    task_id: str
    task_seed: int                                      # Seed for reproducibility
    embedded_problems: List[str]                        # problem_ids (hidden from agent)
    pages_sequence: List[str]
    findings_submitted: List[FindingEntry]
    episode_rewards: List[float]
    total_reward_so_far: float
    is_done: bool
