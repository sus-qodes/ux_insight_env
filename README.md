---
title: UX Insight Analyst Environment
emoji: 🔍
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
app_port: 7860
tags:
  - openenv
---

# UX Insight Analyst Environment

`ux-insight-env` is an OpenEnv reinforcement learning environment that simulates the work of a UX analyst reviewing e-commerce behavioral analytics data.

The agent receives synthetic but realistic StyleMart analytics data, including heatmaps, rage clicks, dead clicks, funnel drop-offs, mobile-vs-desktop behavior, quickbacks, and session recording summaries. The agent must produce structured, actionable UI/UX findings and recommendations.

## Live Space

- Space page: https://huggingface.co/spaces/sushere/ux-insight-env
- API host: https://sushere-ux-insight-env.hf.space
- Health check: https://sushere-ux-insight-env.hf.space/health
- Reset endpoint: https://sushere-ux-insight-env.hf.space/reset
- Web UI: https://sushere-ux-insight-env.hf.space/web
- Landing page: https://sushere-ux-insight-env.hf.space/
- Documentation: https://sushere-ux-insight-env.hf.space/documentation

## Real-World Task

This environment models a practical workflow used by UX analysts and product teams at e-commerce companies:

1. Review behavioral analytics reports from tools such as Microsoft Clarity, Hotjar, or Mixpanel.
2. Inspect session summaries, heatmaps, rage-click reports, dead-click reports, funnel drop-offs, and device-specific metrics.
3. Identify the real UX friction points.
4. Avoid false positives from normal behavior, such as high exit rate on an order confirmation page.
5. Produce prioritized recommendations with expected metric impact.

This fills a useful benchmark gap: most agent environments test code, search, support, or planning, but not behavioral analytics interpretation and UX recommendation quality.

## Web UI Usage

Open the web interface:

```text
https://sushere-ux-insight-env.hf.space/web
```

The OpenEnv web interface provides:

- **Reset** — start a new episode with a task ID (easy/medium/hard) and optional seed.
- **Observation panel** — view the current page analytics data, task description, and step count.
- **Action form** — submit a structured `UXAction` with fields for finding type, affected element, issue category, severity, recommendation, fix category, impact estimate, and confidence. The form is auto-generated from the Pydantic model.
- **Reward and feedback** — see the reward signal and grader feedback after each step.
- **State inspection** — view the internal environment state (hidden ground truth for debugging).
- **Schema viewer** — inspect the Action and Observation JSON schemas.

Example action to submit when the current page shows a dead click on a flash sale banner:

```json
{
  "finding_type": "issue",
  "affected_element": "Flash Sale banner image",
  "issue_category": "dead_click",
  "severity": "high",
  "recommendation": "Make the Flash Sale banner image clickable and link it directly to the active flash sale page so users who tap the promotional banner reach the expected deals instead of waiting after a dead click.",
  "fix_category": "fix_broken_link",
  "impact_estimate": "Expected 20-30% reduction in dead clicks and measurable lift in flash sale click-through conversion.",
  "confidence": 0.9
}
```

## API Usage

Health check:

```bash
curl https://sushere-ux-insight-env.hf.space/health
```

Start an episode:

```bash
curl -X POST https://sushere-ux-insight-env.hf.space/reset
```

Start a deterministic easy episode:

```bash
curl -X POST https://sushere-ux-insight-env.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"seed": 101, "episode_id": "easy"}'
```

## Action Space

The agent submits a `UXAction` for each page analyzed.

| Field | Type | Description |
|---|---|---|
| `finding_type` | `"issue"`, `"no_issue"`, or `"ambiguous"` | Whether the page contains a real UX issue, normal behavior, or an unclear signal. |
| `affected_element` | `str` | Specific UI element, such as `Add to Cart button`. Use `N/A` for no issue. |
| `issue_category` | `str` | Problem type, such as `rage_click`, `dead_click`, `funnel_dropoff`, `scroll_dropoff`, `mobile_layout_break`, `quickback`, `form_abandonment`, `cta_invisible`, `search_no_results`, `high_bounce`, `normal_behavior`, or `unclear`. |
| `severity` | `"critical"`, `"high"`, `"medium"`, `"low"`, or `"none"` | Severity assessment. Use `none` for `no_issue`. |
| `recommendation` | `str` | Specific actionable recommendation of at least 20 words. |
| `fix_category` | `str` | Fix type, such as `fix_broken_link`, `add_loading_state`, `fix_mobile_layout`, `reposition_element`, `increase_contrast`, `add_feedback`, `reduce_steps`, `no_fix_needed`, or `investigate_further`. |
| `impact_estimate` | `str` | Expected metric impact, or `N/A` for no issue. |
| `confidence` | `float` | Confidence from `0.0` to `1.0`. |

## Observation Space

The agent receives a `UXObservation` at each step.

| Field | Type | Description |
|---|---|---|
| `task_id` | `str` | `easy`, `medium`, or `hard`. |
| `task_description` | `str` | Natural-language task instructions. |
| `current_step` | `int` | Current step, one-indexed. |
| `total_steps` | `int` | Total steps in this episode. |
| `pages_to_analyze` | `List[str]` | Page sequence for the episode. |
| `current_page_data` | `PageAnalyticsData` | Current page analytics. |
| `findings_so_far` | `List[FindingEntry]` | Prior agent submissions and rewards. |
| `cumulative_score` | `float` | Running normalized score. |
| `grader_feedback` | `str` | Feedback for the previous action. |
| `task_context` | `Dict[str, Any]` | App-level metadata. |

`PageAnalyticsData` contains session counts, bounce rates, scroll-depth percentiles, mobile/desktop split, heatmap zones, behavioral signals, funnel data, and a session recording summary.

## Tasks

| Task | Steps | Description | Expected difficulty |
|---|---:|---|---|
| Easy | 1 | One clear, high-signal UX issue such as a rage click or dead click. | Basic LLMs should identify it. |
| Medium | 3 | Three pages with multiple issues requiring multi-step reasoning and severity assessment. | Requires prioritization. |
| Hard | 6 | Six-page funnel analysis with real problems, red herrings, and clean pages. | Requires careful reasoning and false-positive resistance. |

## Reward Function

Each step receives dense partial credit rather than only terminal pass/fail reward.

| Component | Weight |
|---|---:|
| Element identification | 25% |
| Issue category | 20% |
| Severity accuracy | 15% |
| Recommendation quality | 25% |
| Fix category | 15% |

The environment also penalizes invalid categories, inconsistent actions, duplicate findings, vague recommendations, false positives, false negatives, and overconfident wrong answers.

## Setup Instructions

Install dependencies:

```bash
pip install -r server/requirements.txt
```

Run locally:

```bash
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

Build and run Docker:

```bash
docker build -t ux-insight-env:latest -f server/Dockerfile .
docker run --rm -p 7860:7860 ux-insight-env:latest
```

Validate:

```bash
openenv validate
```

Deploy:

```bash
openenv push --repo-id sushere/ux-insight-env --interface
```

## Baseline Inference

The baseline script uses the Hugging Face OpenAI-compatible inference endpoint and the local Docker image.

PowerShell:

```powershell
$env:API_BASE_URL = "https://router.huggingface.co/v1/"
$env:MODEL_NAME = "meta-llama/Llama-3.3-70B-Instruct"
$env:OPENENV_BASE_URL = "https://sushere-ux-insight-env.hf.space"
$env:LOCAL_IMAGE_NAME = "ux-insight-env:latest"
py -3.12 inference.py
```

To run all baseline models:

PowerShell:

```powershell
$env:RUN_ALL_BASELINES = "true"
$env:HF_TOKEN = "hf_your_token_here"
py -3.12 inference.py
```

If `HF_TOKEN` is not set, `inference.py` will try to use your cached Hugging Face CLI login token. If `OPENENV_BASE_URL` is empty, the script falls back to launching `LOCAL_IMAGE_NAME` locally with OpenEnv's Docker client.

## Baseline Scores

| Task | Model | Params | Score | Steps | Success |
|---|---|---:|---:|---:|---|
| easy | meta-llama/Llama-3.3-70B-Instruct | 70B | 0.8867 | 1 | True |
| medium | meta-llama/Llama-3.3-70B-Instruct | 70B | 0.5226 | 3 | True |
| hard | meta-llama/Llama-3.3-70B-Instruct | 70B | 0.8448 | 6 | True |
| easy | meta-llama/Llama-4-Maverick-17B-128E-Instruct | 17Bx128E | -- | 1 | -- |
| medium | meta-llama/Llama-4-Maverick-17B-128E-Instruct | 17Bx128E | -- | 3 | -- |
| hard | meta-llama/Llama-4-Maverick-17B-128E-Instruct | 17Bx128E | -- | 6 | -- |
| easy | meta-llama/Llama-4-Scout-17B-16E-Instruct | 17Bx16E | -- | 1 | -- |
| medium | meta-llama/Llama-4-Scout-17B-16E-Instruct | 17Bx16E | -- | 3 | -- |
| hard | meta-llama/Llama-4-Scout-17B-16E-Instruct | 17Bx16E | -- | 6 | -- |
| easy | google/gemma-4-31b-it | 31B | -- | 1 | -- |
| medium | google/gemma-4-31b-it | 31B | -- | 3 | -- |
| hard | google/gemma-4-31b-it | 31B | -- | 6 | -- |
| easy | Qwen/Qwen3.5-9B | 9B | -- | 1 | -- |
| medium | Qwen/Qwen3.5-9B | 9B | -- | 3 | -- |
| hard | Qwen/Qwen3.5-9B | 9B | -- | 6 | -- |

Run details:

- Date: 2026-04-07
- Inference endpoint: `https://router.huggingface.co/v1/`
- Environment endpoint: `https://sushere-ux-insight-env.hf.space`
- Deterministic seeds: easy `101`, medium `202`, hard `303`
- Success threshold: `0.5`
- Multi-model baselines: set `RUN_ALL_BASELINES=true` to evaluate all models
- Note: the hard-task baseline scored high in this run because the model identified most issue pages and one red-herring page successfully.

## End-to-End Walkthrough

```text
1. reset()
   The observation returns one StyleMart analytics page, current task metadata, and available page data.

2. Agent submits UXAction
   The agent identifies an issue, affected element, category, severity, recommendation, fix category, impact estimate, and confidence.

3. step(action)
   The environment grades the finding against deterministic embedded ground truth.

4. Reward and transition
   The environment returns dense reward, grader feedback, updated findings, and the next page if the episode is not complete.

5. Termination
   The episode ends after 1 easy step, 3 medium steps, or 6 hard steps.
```

## File Structure

```text
ux_insight_env/
  __init__.py
  client.py
  inference.py (copy to repo root for submission)
  models.py
  openenv.yaml
  pyproject.toml
  README.md
  static/
    index.html
    docs.html
  server/
    app.py
    data_generator.py
    environment.py
    grader.py
    problem_templates.py
    requirements.txt
    Dockerfile

(At project root for submission)
inference.py (MUST be here - required by hackathon spec)
```

## License

MIT
