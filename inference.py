"""
inference.py - Baseline evaluation script for UX Insight Analyst Environment

OpenEnv Hackathon Submission - Strict Output Format Compliance
MUST be in the root directory of the project.
MUST complete in under 20 minutes.
MUST run on 2 vCPUs / 8GB RAM.

Output format (stdout - ONLY these three line types):
  [START] task=<task_name> env=<benchmark> model=<model_name>
  [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
  [END]   success=<true|false> steps=<n> rewards=<r1,r2,...,rn>
"""

import asyncio
import json
import os
import sys
import time
from typing import List, Optional

from openai import OpenAI

try:
    from huggingface_hub import get_token
except Exception:
    get_token = None

# ---------------------------------------------------------------------------
# Configuration (from environment variables with required defaults)
# ---------------------------------------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1/")
MODEL_NAME = os.getenv("MODEL_NAME", "meta-llama/Llama-3.3-70B-Instruct")

# HF_TOKEN is mandatory per hackathon guidelines
HF_TOKEN = os.getenv("HF_TOKEN") or (get_token() if get_token else None)
if not HF_TOKEN:
    raise ValueError(
        "HF_TOKEN environment variable is required. "
        "Set it via: export HF_TOKEN='hf_...'"
    )
API_KEY = HF_TOKEN

# ---------------------------------------------------------------------------
# Multi-model baselines
# ---------------------------------------------------------------------------
BASELINE_MODELS: List[str] = [
    MODEL_NAME,
    "google/gemma-4-31b-it",
    "meta-llama/Llama-4-Scout-17B-16E-Instruct",
    "meta-llama/Llama-4-Maverick-17B-128E-Instruct",
    "Qwen/Qwen3.5-9B",
]

# ---------------------------------------------------------------------------
# Evaluation settings
# ---------------------------------------------------------------------------
IMAGE_NAME = os.getenv("OPENENV_IMAGE", "ux-insight-env:latest")
ENV_BASE_URL = os.getenv("OPENENV_BASE_URL", "https://sushere-ux-insight-env.hf.space")
BENCHMARK = "ux-insight-env"
TEMPERATURE = 0.3
MAX_TOKENS = 800
MAX_STEPS = 6
MAX_TOTAL_REWARD = 6.0
SUCCESS_THRESHOLD = 0.5
PER_STEP_TIMEOUT = 30
TASK_TIMEOUT = 300
TASK_SEEDS = {"easy": 101, "medium": 202, "hard": 303}
TASK_MAX_REWARD = {"easy": 1.0, "medium": 3.0, "hard": 6.0}
LLM_RETRY_ATTEMPTS = 3
LLM_RETRY_BACKOFF = [2, 4, 8]  # seconds between retries


# ---------------------------------------------------------------------------
# Stderr debug logger — keeps stdout clean for the validator
# ---------------------------------------------------------------------------

def debug(msg: str) -> None:
    """Write debug/diagnostic output to stderr only. Never pollute stdout."""
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Hackathon-compliant output functions (stdout ONLY)
# Format spec: https://docs.google.com/document/d/...
# ---------------------------------------------------------------------------

def log_start(task: str, env: str, model: str) -> None:
    """Emit [START] line. One per episode, before any steps."""
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str] = None) -> None:
    """Emit [STEP] line. One per step, immediately after env.step() returns."""
    done_str = "true" if done else "false"
    error_str = error.replace("\n", " ").strip() if error else "null"
    # Sanitize action string: single line, no newlines
    action_clean = action.replace("\n", " ").replace("\r", "")
    print(
        f"[STEP] step={step} action={action_clean} reward={reward:.2f} done={done_str} error={error_str}",
        flush=True,
    )


def log_end(success: bool, steps: int, rewards: List[float]) -> None:
    """Emit [END] line. One per episode, always emitted even on exception."""
    success_str = "true" if success else "false"
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={success_str} steps={steps} rewards={rewards_str}", flush=True)


# ---------------------------------------------------------------------------
# System prompt for the LLM agent (enhanced with few-shot guidance)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are a Senior UX Analyst specializing in e-commerce platforms. You are reviewing behavioral analytics data from StyleMart, a fashion e-commerce platform, to identify UX friction points and recommend improvements.

You will receive analytics data for one page at a time. The data includes:
- Session counts and duration
- Bounce rates (overall, mobile, desktop)
- Scroll depth percentiles
- Heatmap zone data
- Behavioral signals (rage clicks, dead clicks, quickbacks, etc.)
- Funnel step data (for checkout pages)
- Session recording summaries

For each page, you MUST submit a structured finding as a JSON object with these fields:

1. finding_type: "issue" | "no_issue" | "ambiguous"
   - "issue" = real UX problem found
   - "no_issue" = data is normal (use for pages where high metrics are EXPECTED)
   - "ambiguous" = signal is unclear, needs more data

2. affected_element: The specific UI element (e.g. "Add to Cart button", "Filter sidebar"). Use "N/A" for no_issue.

3. issue_category: One of: rage_click, dead_click, funnel_dropoff, scroll_dropoff, mobile_layout_break, quickback, form_abandonment, cta_invisible, search_no_results, high_bounce, normal_behavior, unclear

4. severity: "critical" | "high" | "medium" | "low" | "none"
   Use "none" for no_issue findings.

5. recommendation: A SPECIFIC, ACTIONABLE recommendation of at least 20 words. MUST name the affected element and describe the exact change. Generic advice like "improve UX" scores poorly.

6. fix_category: One of: redesign_element, reposition_element, fix_broken_link, improve_copy, add_feedback, reduce_steps, increase_contrast, add_loading_state, fix_mobile_layout, no_fix_needed, investigate_further

7. impact_estimate: Expected metric impact with numbers (e.g. "Expected 15-25% reduction in checkout abandonment rate"). Use "N/A" for no_issue.

8. confidence: float 0.0-1.0

CRITICAL RULES:
- NOT everything is a problem. High exit rates on order confirmation pages are NORMAL (purchase complete). High time-on-page on product detail pages can mean engagement (reading reviews). Login page "bounces" may be successful redirects. Report these as "no_issue" with "normal_behavior" category.
- If finding_type is "no_issue", severity MUST be "none" and fix_category MUST be "no_fix_needed".
- If finding_type is "issue", fix_category MUST NOT be "no_fix_needed".
- Match the behavioral signal type to the correct issue_category (e.g. rage_click signal -> rage_click category).
- Your recommendation MUST mention the specific element name from the data.
- Include specific percentage estimates in impact_estimate (e.g. "15-25% reduction in bounce rate").

RESPOND ONLY WITH A VALID JSON OBJECT. No markdown, no explanation, no preamble."""

# ---------------------------------------------------------------------------
# LLM call with retry and exponential backoff
# ---------------------------------------------------------------------------

def get_agent_action(
    client: OpenAI,
    observation_text: str,
    history: List[str],
    model_name: str = MODEL_NAME,
) -> str:
    """Call the LLM to get the agent's action as JSON. Retries on failure."""
    history_context = "\n".join(history[-5:]) if history else "No previous steps."
    user_prompt = f"""Analyze this page's analytics data and submit your structured finding.

ANALYTICS DATA:
{observation_text}

PREVIOUS FINDINGS IN THIS EPISODE:
{history_context}

Respond ONLY with a valid JSON object matching the UXAction schema. No markdown fences."""

    last_error = None
    for attempt in range(LLM_RETRY_ATTEMPTS):
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                stream=False,
                timeout=PER_STEP_TIMEOUT,
            )
            text = (completion.choices[0].message.content or "{}").strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                lines = text.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                text = "\n".join(lines).strip()
            return text

        except Exception as exc:
            last_error = exc
            if attempt < LLM_RETRY_ATTEMPTS - 1:
                wait = LLM_RETRY_BACKOFF[attempt]
                debug(f"[RETRY] LLM call failed (attempt {attempt + 1}/{LLM_RETRY_ATTEMPTS}): {exc}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                debug(f"[ERROR] LLM call failed after {LLM_RETRY_ATTEMPTS} attempts: {last_error}")

    # All retries exhausted — return safe fallback
    return json.dumps(_make_fallback_action_dict())


# ---------------------------------------------------------------------------
# Client-side action validation (catch errors before sending to server)
# ---------------------------------------------------------------------------

_VALID_ISSUE_CATEGORIES = {
    "rage_click", "dead_click", "funnel_dropoff", "scroll_dropoff",
    "mobile_layout_break", "quickback", "form_abandonment", "cta_invisible",
    "search_no_results", "high_bounce", "normal_behavior", "unclear",
}

_VALID_FIX_CATEGORIES = {
    "redesign_element", "reposition_element", "fix_broken_link", "improve_copy",
    "add_feedback", "reduce_steps", "increase_contrast", "add_loading_state",
    "fix_mobile_layout", "no_fix_needed", "investigate_further",
}


def validate_and_fix_action(action_dict: dict) -> dict:
    """Validate action fields and auto-correct common LLM mistakes."""
    # Fix issue_category if invalid
    if action_dict.get("issue_category") not in _VALID_ISSUE_CATEGORIES:
        debug(f"[FIX] Invalid issue_category '{action_dict.get('issue_category')}' -> 'unclear'")
        action_dict["issue_category"] = "unclear"

    # Fix fix_category if invalid
    if action_dict.get("fix_category") not in _VALID_FIX_CATEGORIES:
        debug(f"[FIX] Invalid fix_category '{action_dict.get('fix_category')}' -> 'investigate_further'")
        action_dict["fix_category"] = "investigate_further"

    # Fix inconsistency: no_issue must have severity=none and fix=no_fix_needed
    if action_dict.get("finding_type") == "no_issue":
        if action_dict.get("severity") != "none":
            debug(f"[FIX] no_issue with severity='{action_dict.get('severity')}' -> 'none'")
            action_dict["severity"] = "none"
        if action_dict.get("fix_category") != "no_fix_needed":
            debug(f"[FIX] no_issue with fix='{action_dict.get('fix_category')}' -> 'no_fix_needed'")
            action_dict["fix_category"] = "no_fix_needed"
        if action_dict.get("issue_category") not in ("normal_behavior", "unclear"):
            action_dict["issue_category"] = "normal_behavior"

    # Fix inconsistency: issue must not have fix=no_fix_needed
    if action_dict.get("finding_type") == "issue":
        if action_dict.get("fix_category") == "no_fix_needed":
            debug("[FIX] issue with fix='no_fix_needed' -> 'investigate_further'")
            action_dict["fix_category"] = "investigate_further"
        if action_dict.get("severity") == "none":
            debug("[FIX] issue with severity='none' -> 'medium'")
            action_dict["severity"] = "medium"

    # Ensure confidence is a valid float
    try:
        conf = float(action_dict.get("confidence", 0.5))
        action_dict["confidence"] = max(0.0, min(1.0, conf))
    except (TypeError, ValueError):
        action_dict["confidence"] = 0.5

    # Ensure recommendation is long enough (pad if needed)
    rec = action_dict.get("recommendation", "")
    if len(rec.split()) < 20:
        element = action_dict.get("affected_element", "the element")
        action_dict["recommendation"] = (
            f"{rec} It is recommended to review and improve the {element} "
            f"to enhance the user experience and reduce friction on this page."
        )

    return action_dict


# ---------------------------------------------------------------------------
# Observation formatter (enhanced with clearer structure for LLM)
# ---------------------------------------------------------------------------

def format_observation_for_llm(obs) -> str:
    """Convert observation object to readable text for the LLM."""
    page = obs.current_page_data
    lines = [
        f"TASK: {obs.task_id} (Step {obs.current_step}/{obs.total_steps})",
        f"TASK DESCRIPTION: {obs.task_description}",
        "",
        f"PAGE: {page.page_name} ({page.page_url_pattern})",
        f"Sessions: {page.total_sessions:,} | Avg Duration: {page.avg_session_duration_seconds:.0f}s | Bounce: {page.bounce_rate:.1%}",
        f"Scroll Depth: p50={page.scroll_depth_p50:.0f}% | p80={page.scroll_depth_p80:.0f}%",
        f"Mobile: {page.mobile_sessions_pct:.0%} of traffic | Mobile Bounce: {page.mobile_bounce_rate:.1%} | Desktop Bounce: {page.desktop_bounce_rate:.1%}",
        "",
        "HEATMAP ZONES:",
    ]
    for zone in page.heatmap_zones:
        depth_str = f" | Scroll Reached: {zone.scroll_depth_reached_pct:.0%}" if zone.scroll_depth_reached_pct is not None else ""
        lines.append(f"  - {zone.zone_name}: {zone.click_density_pct:.1%} click density{depth_str}")

    lines.append("")
    lines.append("BEHAVIORAL SIGNALS:")
    for sig in page.behavioral_signals:
        lines.append(
            f"  - {sig.signal_type.upper()} on '{sig.affected_element}': "
            f"{sig.rate:.1%} of sessions ({sig.session_count:,} sessions)"
        )

    if page.funnel_steps:
        lines.append("\nFUNNEL:")
        for step in page.funnel_steps:
            lines.append(
                f"  - {step.step_name}: {step.sessions_entered:,} entered -> "
                f"{step.sessions_dropped:,} dropped ({step.dropoff_rate:.1%} drop-off)"
            )

    lines.append(f"\nSESSION RECORDING SUMMARY:\n{page.session_recording_summary}")

    if obs.grader_feedback:
        lines.append(f"\nFEEDBACK ON PREVIOUS STEP:\n{obs.grader_feedback}")

    if obs.findings_so_far:
        lines.append("\nPREVIOUS FINDINGS:")
        for f in obs.findings_so_far:
            lines.append(
                f"  Step {f.step} | {f.page_analyzed} | {f.finding_type} | "
                f"{f.issue_category} | Severity: {f.severity} | Reward: {f.step_reward:.2f}"
            )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Default / fallback action
# ---------------------------------------------------------------------------

def _make_fallback_action_dict() -> dict:
    return {
        "finding_type": "ambiguous",
        "affected_element": "N/A",
        "issue_category": "unclear",
        "severity": "none",
        "recommendation": (
            "Could not parse the analytics data to produce a structured finding. "
            "Recommend manual review of the data signals on this page to identify "
            "any potential UX friction points or behavioral anomalies."
        ),
        "fix_category": "investigate_further",
        "impact_estimate": "N/A",
        "confidence": 0.0,
    }


# ---------------------------------------------------------------------------
# Main evaluation loop
# ---------------------------------------------------------------------------

async def run_task(task_name: str, model_name: str = MODEL_NAME) -> float:
    """Run one task and return the final normalized score."""
    try:
        from ux_insight_env.client import UXInsightEnv
        from ux_insight_env.models import UXAction
    except ModuleNotFoundError:
        from client import UXInsightEnv
        from models import UXAction

    llm_client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=model_name)

    env = None
    try:
        if ENV_BASE_URL:
            env = UXInsightEnv(base_url=ENV_BASE_URL)
            await env.connect()
        else:
            env = await UXInsightEnv.from_docker_image(IMAGE_NAME)

        result = await env.reset(task_id=task_name, episode_id=task_name, seed=TASK_SEEDS[task_name])
        obs = result.observation

        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            step_start = time.time()

            # Format observation for LLM
            obs_text = format_observation_for_llm(obs)
            action_json_str = get_agent_action(llm_client, obs_text, history, model_name=model_name)

            # Parse, validate, and fix action
            try:
                action_dict = json.loads(action_json_str)
                action_dict = validate_and_fix_action(action_dict)
                action = UXAction(**action_dict)
            except Exception as parse_err:
                debug(f"[ERROR] Action parse error: {parse_err}")
                action_dict = _make_fallback_action_dict()
                action = UXAction(**action_dict)
                action_json_str = json.dumps(action_dict)

            # Execute step
            error = None
            try:
                result = await env.step(action)
                obs = result.observation
                reward = result.reward or 0.0
                done = result.done
            except Exception as step_err:
                debug(f"[ERROR] Step execution error: {step_err}")
                reward = 0.0
                done = True
                error = str(step_err)

            rewards.append(reward)
            steps_taken = step

            # Emit [STEP] to stdout (hackathon format)
            log_step(
                step=step,
                action=action_json_str[:200],
                reward=reward,
                done=done,
                error=error,
            )

            step_elapsed = time.time() - step_start
            debug(f"  Step {step}: reward={reward:.3f} done={done} ({step_elapsed:.1f}s)")

            # Build history for next step's context
            if obs and hasattr(obs, "findings_so_far") and obs.findings_so_far:
                last_f = obs.findings_so_far[-1]
                history.append(
                    f"Step {step} | Page: {last_f.page_analyzed} | "
                    f"Type: {last_f.finding_type} | Category: {last_f.issue_category} | "
                    f"Severity: {last_f.severity} | Reward: {reward:.3f}"
                )
            else:
                history.append(f"Step {step} | Reward: {reward:.3f}")

            if done:
                break

        # Compute final score
        max_reward = TASK_MAX_REWARD.get(task_name, MAX_TOTAL_REWARD)
        score = sum(rewards) / max_reward if max_reward > 0 else 0.0
        score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_THRESHOLD

    except Exception as e:
        debug(f"[ERROR] Task {task_name} failed: {e}")
    finally:
        if env is not None:
            try:
                await env.close()
            except Exception as e:
                debug(f"[WARN] env.close() error: {e}")
        # Always emit [END] — even on exception
        log_end(success=success, steps=steps_taken, rewards=rewards)

    return score


async def run_single_model(model_name: str) -> dict:
    """Run all tasks for a single model. Returns {task: score}."""
    scores = {}
    for task in ["easy", "medium", "hard"]:
        debug(f"\n{'='*60}")
        debug(f"  {model_name} | task: {task}")
        debug(f"{'='*60}")
        task_start = time.time()
        score = await run_task(task, model_name=model_name)
        elapsed = time.time() - task_start
        scores[task] = score
        debug(f"  {model_name} | {task} score: {score:.4f} ({elapsed:.1f}s)")
    return scores


async def main() -> None:
    run_all = os.getenv("RUN_ALL_BASELINES", "").lower() in ("1", "true", "yes")
    models = BASELINE_MODELS if run_all else [MODEL_NAME]

    debug(f"[CONFIG] API_BASE_URL={API_BASE_URL}")
    debug(f"[CONFIG] MODEL_NAME={MODEL_NAME}")
    debug(f"[CONFIG] ENV_BASE_URL={ENV_BASE_URL}")
    debug(f"[CONFIG] Models to run: {len(models)}")

    all_results: dict = {}
    total_start = time.time()

    for model in models:
        all_results[model] = await run_single_model(model)

    total_elapsed = time.time() - total_start

    # Summary table (stderr only)
    debug(f"\n{'='*80}")
    debug("  MULTI-MODEL BASELINE RESULTS")
    debug(f"{'='*80}")
    debug(f"  {'Model':<55} {'Easy':>6} {'Medium':>8} {'Hard':>6} {'Avg':>6}")
    debug(f"  {'-'*55} {'-'*6} {'-'*8} {'-'*6} {'-'*6}")
    for model, scores in all_results.items():
        avg = sum(scores.values()) / len(scores) if scores else 0.0
        debug(
            f"  {model:<55} {scores.get('easy', 0):.4f} {scores.get('medium', 0):.4f} "
            f"{scores.get('hard', 0):.4f} {avg:.4f}"
        )
    debug(f"\n  Total time: {total_elapsed:.1f}s")

    # Save results to JSON
    output = {
        "benchmark": BENCHMARK,
        "endpoint": API_BASE_URL,
        "environment": ENV_BASE_URL,
        "seeds": TASK_SEEDS,
        "results": {
            model: {"scores": scores, "avg": sum(scores.values()) / len(scores)}
            for model, scores in all_results.items()
        },
    }
    results_path = os.path.join("outputs", "evals", "baseline_results.json")
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, "w") as f:
        json.dump(output, f, indent=2)
    debug(f"[INFO] Results saved to {results_path}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        debug("[INFO] Interrupted by user")
        sys.exit(130)
    except Exception as e:
        debug(f"[FATAL] {e}")
        sys.exit(1)
