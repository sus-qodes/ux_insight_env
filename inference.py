"""
inference.py - Baseline evaluation script for UX Insight Analyst Environment
MUST be in the root directory of the project.
MUST complete in under 20 minutes.
MUST run on 2 vCPUs / 8GB RAM.
"""

import asyncio
from datetime import datetime, timezone
import json
import os
from typing import Any, Dict, List

from openai import OpenAI

try:
    from huggingface_hub import get_token
except Exception:
    get_token = None

# ---------------------------------------------------------------------------
# Configuration (from environment variables - NEVER hardcode)
# ---------------------------------------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1/")
MODEL_NAME   = os.getenv("MODEL_NAME", "meta-llama/Llama-3.3-70B-Instruct")
HF_TOKEN     = os.getenv("HF_TOKEN")
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Multi-model baselines
# ---------------------------------------------------------------------------
BASELINE_MODELS: List[str] = [
    MODEL_NAME,
    "meta-llama/Llama-4-Scout-17B-16E-Instruct",
]

# ---------------------------------------------------------------------------
# Evaluation settings
# ---------------------------------------------------------------------------
LOCAL_IMAGE_NAME    = os.getenv("LOCAL_IMAGE_NAME")
ENV_BASE_URL        = os.getenv("OPENENV_BASE_URL", "https://sushere-ux-insight-env.hf.space")
BENCHMARK           = "ux-insight-env"
TEMPERATURE         = 0.3       # Low temp for analytical tasks
MAX_TOKENS          = 800
MAX_STEPS           = 6         # Max steps per episode (covers hard task)
MAX_TOTAL_REWARD    = 6.0       # 6 steps x max 1.0 reward each
SUCCESS_THRESHOLD   = 0.5
PER_STEP_TIMEOUT    = 30        # seconds - API timeout per LLM call
TASK_TIMEOUT        = 300       # seconds - max per task
TASK_SEEDS          = {"easy": 101, "medium": 202, "hard": 303}
TASK_MAX_REWARD     = {"easy": 1.0, "medium": 3.0, "hard": 6.0}
TASK_ORDER          = ["easy", "medium", "hard"]

# ---------------------------------------------------------------------------
# System prompt for the LLM agent
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

For each page, you MUST submit a structured finding. Your finding must include:
1. finding_type: "issue" (real UX problem), "no_issue" (data is normal - use when high numbers are EXPECTED, like exit rates on confirmation pages), or "ambiguous" (unclear signal needing more data)
2. affected_element: The specific UI element with the problem (or "N/A")
3. issue_category: The type of problem (rage_click, dead_click, funnel_dropoff, scroll_dropoff, mobile_layout_break, quickback, form_abandonment, cta_invisible, search_no_results, normal_behavior, unclear)
4. severity: critical / high / medium / low / none
5. recommendation: A SPECIFIC, ACTIONABLE recommendation of at least 20 words that names the element and describes the exact change to make
6. fix_category: The type of fix (redesign_element, reposition_element, fix_broken_link, improve_copy, add_feedback, reduce_steps, increase_contrast, add_loading_state, fix_mobile_layout, no_fix_needed, investigate_further)
7. impact_estimate: Expected metric improvement (or "N/A")
8. confidence: Your confidence in this finding (0.0-1.0)

IMPORTANT: Not everything is a problem. High exit rates on thank-you/confirmation pages are NORMAL. High time-on-page for rich content pages can mean engagement. Think before labeling something a "critical" issue - be a thoughtful analyst, not a pattern-matcher.

RESPOND ONLY WITH A VALID JSON OBJECT matching the UXAction schema. No preamble, no explanation outside the JSON."""

# ---------------------------------------------------------------------------
# Logging functions (STRICT FORMAT - DO NOT MODIFY FIELD NAMES)
# ---------------------------------------------------------------------------

def _format_log_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(value, ensure_ascii=False)


def log_start(task: str, env: str, model: str):
    print(
        f"[START] task={task} env={env} model={model}",
        flush=True,
    )


def log_step(step: int, action: str, reward: float, done: bool, error=None):
    print(
        f"[STEP] step={_format_log_value(step)} "
        f"action={_format_log_value(action)} "
        f"reward={_format_log_value(reward)} "
        f"done={_format_log_value(done)} "
        f"error={_format_log_value(error)}",
        flush=True,
    )


def log_end(success: bool, steps: int, rewards: List[float]):
    reward_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={_format_log_value(success)} "
        f"steps={_format_log_value(steps)} "
        f"rewards={reward_str}",
        flush=True,
    )


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

class ModelInferenceError(RuntimeError):
    """Raised when the model endpoint cannot produce a response."""


def resolve_api_key() -> str:
    """Use HF_TOKEN when present, otherwise fall back to the cached HF CLI token."""
    if HF_TOKEN:
        return HF_TOKEN
    if get_token is not None:
        cached_token = get_token()
        if cached_token:
            return cached_token
    raise RuntimeError(
        "No Hugging Face token available. Set HF_TOKEN or login with `hf auth login`."
    )


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def get_agent_action(
    client: OpenAI,
    observation_text: str,
    history: List[str],
    model_name: str = MODEL_NAME,
) -> str:
    """Call the LLM to get the agent's action as JSON."""
    history_context = "\n".join(history[-3:]) if history else "No previous steps."
    user_prompt = f"""Analyze this page's analytics data and submit your structured finding.

ANALYTICS DATA:
{observation_text}

PREVIOUS FINDINGS IN THIS EPISODE:
{history_context}

Respond ONLY with a valid JSON object for the UXAction schema."""

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
        raw_content = completion.choices[0].message.content
        text = (raw_content or "").strip()
        if not text:
            raise ModelInferenceError("Model returned an empty response.")
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()
        return text
    except Exception as exc:
        print(f"[DEBUG] LLM call failed: {exc}", flush=True)
        raise ModelInferenceError(str(exc)) from exc


# ---------------------------------------------------------------------------
# Observation formatter
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

def make_fallback_action_dict() -> dict:
    return {
        "finding_type": "ambiguous",
        "affected_element": "N/A",
        "issue_category": "unclear",
        "severity": "none",
        "recommendation": "Could not parse the analytics data to produce a structured finding. Recommend manual review of the data signals on this page.",
        "fix_category": "investigate_further",
        "impact_estimate": "N/A",
        "confidence": 0.0,
    }


# ---------------------------------------------------------------------------
# Main evaluation loop
# ---------------------------------------------------------------------------

async def run_task(task_name: str, model_name: str = MODEL_NAME) -> Dict[str, Any]:
    """Run one task and return task-level metrics."""
    try:
        from ux_insight_env.client import UXInsightEnv
        from ux_insight_env.models import UXAction
    except ModuleNotFoundError:
        # When running from docker or as a standalone script from the repo root
        from client import UXInsightEnv
        from models import UXAction

    client = OpenAI(base_url=API_BASE_URL, api_key=resolve_api_key())

    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False
    task_error = None

    log_start(task=task_name, env=BENCHMARK, model=model_name)

    env = None
    try:
        if ENV_BASE_URL:
            env = UXInsightEnv(base_url=ENV_BASE_URL)
            await env.connect()
        else:
            env = await UXInsightEnv.from_docker_image(LOCAL_IMAGE_NAME)
        result = await env.reset(task_id=task_name, episode_id=task_name, seed=TASK_SEEDS[task_name])
        obs = result.observation

        for step in range(1, MAX_STEPS + 1):
            if result.done:
                break

            # Format observation for LLM
            obs_text = format_observation_for_llm(obs)
            try:
                action_json_str = get_agent_action(client, obs_text, history, model_name=model_name)
            except ModelInferenceError as llm_err:
                task_error = f"model_inference_failed: {llm_err}"
                print(
                    f"[DEBUG] Aborting task {task_name} for {model_name}: {task_error}",
                    flush=True,
                )
                break

            # Parse and validate action
            try:
                action_dict = json.loads(action_json_str)
                action = UXAction(**action_dict)
            except Exception as parse_err:
                print(f"[DEBUG] Action parse error: {parse_err}", flush=True)
                action = UXAction(**make_fallback_action_dict())

            # Execute step
            try:
                result = await env.step(action)
                obs = result.observation
                reward = result.reward or 0.0
                done = result.done
                error = None
            except Exception as step_err:
                print(f"[DEBUG] Step execution error: {step_err}", flush=True)
                reward = 0.0
                done = True
                error = str(step_err)

            rewards.append(reward)
            steps_taken = step

            log_step(
                step=step,
                action=action_json_str,
                reward=reward,
                done=done,
                error=error,
            )

            if obs and hasattr(obs, "findings_so_far") and obs.findings_so_far:
                last_f = obs.findings_so_far[-1]
                history.append(
                    f"Step {step} | Page: {last_f.page_analyzed} | "
                    f"Type: {last_f.finding_type} | Reward: {reward:.3f}"
                )
            else:
                history.append(f"Step {step} | Reward: {reward:.3f}")

            if done:
                break

        max_reward = TASK_MAX_REWARD.get(task_name, MAX_TOTAL_REWARD)
        score = sum(rewards) / max_reward if max_reward > 0 else 0.0
        score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_THRESHOLD

    except Exception as e:
        print(f"[DEBUG] Task {task_name} failed with error: {e}", flush=True)
        task_error = str(e)
    finally:
        if env is not None:
            try:
                await env.close()
            except Exception as e:
                print(f"[DEBUG] env.close() error: {e}", flush=True)
        log_end(success=success, steps=steps_taken, rewards=rewards)

    return {
        "score": score,
        "success": success,
        "steps": steps_taken,
        "rewards": rewards,
        "error": task_error,
    }


async def run_single_model(model_name: str) -> Dict[str, Dict[str, Any]]:
    """Run all tasks for a single model."""
    scores: Dict[str, Dict[str, Any]] = {}
    for task in TASK_ORDER:
        print(f"[DEBUG] === {model_name} | task: {task} ===", flush=True)
        task_result = await run_task(task, model_name=model_name)
        scores[task] = task_result
        print(
            f"[DEBUG] {model_name} | {task} score: {task_result['score']:.4f}",
            flush=True,
        )
    return scores


async def main() -> None:
    # Determine which models to run
    run_all = os.environ.get("RUN_ALL_BASELINES", "").lower() in ("1", "true", "yes")
    models = BASELINE_MODELS if run_all else [MODEL_NAME]

    all_results: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for model in models:
        print(f"\n[DEBUG] {'='*60}", flush=True)
        print(f"[DEBUG] RUNNING MODEL: {model}", flush=True)
        print(f"[DEBUG] {'='*60}", flush=True)
        all_results[model] = await run_single_model(model)

    # Print summary table
    print("\n[DEBUG] === MULTI-MODEL BASELINE RESULTS ===", flush=True)
    print(f"[DEBUG] {'Model':<55} {'Easy':>6} {'Medium':>8} {'Hard':>6} {'Avg':>6}", flush=True)
    print(f"[DEBUG] {'-'*55} {'-'*6} {'-'*8} {'-'*6} {'-'*6}", flush=True)
    for model, task_results in all_results.items():
        avg = (
            sum(task["score"] for task in task_results.values()) / len(task_results)
            if task_results
            else 0.0
        )
        print(
            f"[DEBUG] {model:<55} {task_results.get('easy', {}).get('score', 0.0):.4f} "
            f"{task_results.get('medium', {}).get('score', 0.0):.4f} "
            f"{task_results.get('hard', {}).get('score', 0.0):.4f} {avg:.4f}",
            flush=True,
        )

    # Save results to JSON
    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark": BENCHMARK,
        "endpoint": API_BASE_URL,
        "environment": ENV_BASE_URL,
        "seeds": TASK_SEEDS,
        "results": {
            model: {
                "tasks": task_results,
                "avg": (
                    sum(task["score"] for task in task_results.values()) / len(task_results)
                    if task_results
                    else 0.0
                ),
            }
            for model, task_results in all_results.items()
        },
    }
    results_path = os.path.join(SCRIPT_DIR, "outputs", "evals", "baseline_results.json")
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n[DEBUG] Results saved to {results_path}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
