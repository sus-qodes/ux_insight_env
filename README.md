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

## Episode Lifecycle & Contracts

### Deterministic Reproducibility

All episodes are **100% deterministic** given a seed. The same `seed` + `task_id` produces identical analytics data and identical expected ground-truth problems across re-runs. This enables:

- **Reproducible evaluation** of agent performance
- **Benchmark consistency** across multiple training runs
- **Exact comparison** of model capabilities

### Episode Flow Contract

1. **reset(seed=INT, task_id="easy"|"medium"|"hard")** → UXObservation
   - Initializes episode with deterministic problem set
   - Returns `observation.done = False`, first page data

2. **step(action: UXAction)** → UXObservation  (repeat for all pages)
   - Grades the finding against embedded ground truth
   - Updates `cumulative_score` and `findings_so_far`
   - Returns next page or `observation.done = True`

3. **After done=True**
   - Episode is **terminal**; further `step()` calls will return `done=True, reward=-0.1`
   - You **MUST call reset()** to start a new episode
   - WebSocket sessions preserve state; HTTP is stateless (auto-reset per request)

### Difficulty-Specific Scoring Targets

Based on baseline model performance, expected score ranges are:

| Task | Pages | Expected Score | Baseline (Llama 3.3-70B) |
|------|-------|-|---|
| **Easy** | 1 | **0.70–0.85** | 0.8450 |
| **Medium** | 3 | **0.50–0.70** | 0.8134 |
| **Hard** | 6 | **0.20–0.45** | 0.7864 |

Hard tasks target **0.2–0.4** due to red herring handling penalties and complexity. Higher baseline scores (0.6–0.9) reflect models' ability to identify obvious issues; hard tasks test reasoning robustness.

## Reward Composition (Detailed Formula)

### Per-Step Reward (0.0 – 1.0)

The grader computes 5 component scores, then applies anti-exploit penalties:

**Component Scoring:**

1. **Element Identification** (25%): Jaccard-like overlap between predicted and ground-truth element names
   - Perfect match (100% word overlap): `0.25`
   - Partial match (60% overlap): `0.15`
   - No match: `0.0`

2. **Issue Category Accuracy** (20%):
   - Exact match (e.g., `rage_click` = `rage_click`): `0.20`
   - Related category (e.g., `dead_click` for `rage_click`): `0.10`
   - Unrelated: `0.0`

3. **Severity Ranking** (15%):
   - Exact match (critical=critical): `0.15`
   - Off-by-one (critical vs high): `0.075` (half credit)
   - Wrong (critical vs low): `0.0`

4. **Recommendation Quality** (25%):
   - Keyword coverage: % of expected keywords present in recommendation
   - Length bonus: +0.2 if ≥20 words (else ×0.5 penalty)
   - Element mention: +0.2 if recommendation mentions affected element
   - **Maximum**: `0.25`

5. **Fix Category Compatibility** (15%):
   - Exact match: `0.15`
   - Compatible fix (e.g., `reposition_element` ↔ `redesign_element`): `0.075`
   - Incompatible: `0.0`

**Anti-Exploit Penalties** (subtracted from base score):

- **Duplicate finding**: -0.40 (agent submits same element+category twice)
- **Inconsistency**: -0.20 (says "issue" but severity="none")
- **Over-confidence on wrong**: -0.10 (grade<0.3 but confidence>0.8)
- **Minimal recommendation**: -0.15 (< 10 characters)

**Final step reward**: `max(min(base_score - penalties, 1.0), -0.5)`

### End-of-Episode Bonus (added at done=True)

After all steps, the environment computes holistic bonuses:

1. **Priority ranking bonus** (medium/hard): +0.10 if findings ordered by severity
2. **Red herring handling** (hard only): +0.10 for correctly identifying no-issue pages
3. **Impact estimate quality** (hard only): +0.05 if estimates include percentages + metrics
4. **False positive penalty**: -0.05 per low-score (< 0.1) issue findings

**Total episode bonus**: `[-0.10, +0.25]`

### Normalized Score

Returned as `observation.cumulative_score`:

```
cumulative_score = sum(step_rewards + episode_bonus) / num_steps
clipped to [0.0, 1.0]
```

For example, a hard task (6 steps) with all 0.8 step rewards + 0.15 bonus:
```
score = (0.8*6 + 0.15) / 6 = 4.95 / 6 = 0.825
```

## Design Simplifications & Future Enhancements

### Current Design: Single-Issue-Per-Page

This environment intentionally simplifies real-world UX analysis:

1. **One primary problem per page** (not 2–3 simultaneous issues)
   - Real workflows may have correlated problems (layout + performance)
   - **Why**: Focus evaluation on signal detection, not problem decomposition

2. **No revision loop** (one finding per page, committed)
   - Users cannot re-analyze a page after feedback
   - **Why**: Test reasoning robustness in single pass

3. **Synthetic metrics** (deterministic, not statistical)
   - Real Clarity/Mixpanel sessions have statistical noise
   - **Why**: Ensure grading is deterministic and reproducible

4. **No multi-modal data** (text + images + videos)
   - Only heatmaps, funnel, behavioral signals, and session summaries
   - **Why**: Keep observation space manageable

### Rationale

These simplifications enable **precise, deterministic grading** and focus agent development on:
- ✅ Signal detection (does the issue exist?)
- ✅ Classification (what type of issue?)
- ✅ Recommendation quality (is the fix actionable?)

### Planned Enhancements

- [ ] **Multi-issue mode**: 2–3 correlated problems per page; agent must prioritize
- [ ] **Revision-allowed episodes**: Agent can re-analyze page after grader feedback
- [ ] **Confidence bounds**: Metrics include confidence intervals; agent must estimate uncertainty
- [ ] **Real dataset mode**: Anonymized Microsoft Clarity / Hotjar logs
- [ ] **Search iteration**: Multi-turn analytics exploration before final recommendation

## Why This Environment (Usability & Value)

### Real-World UX Analyst Workflow

This environment models the actual job performed by **UX researchers at e-commerce companies**:

```
Input:  Behavioral analytics (Clarity, Hotjar, Mixpanel)
Task:   Identify genuine UX friction vs. normal behavior
Output: Prioritized findings + actionable recommendations
```

Unlike code/search/reasoning benchmarks, this tests:
- **Data interpretation**: Distinguish signal from noise
- **User empathy**: Understand intent behind behavioral signals
- **Recommendation quality**: Propose specific, measurable fixes

### Code Architecture

The codebase is **production-grade OpenEnv**:

**Core Components:**

- **models.py**: Pydantic models for UXAction/UXObservation (strict typing)
- **environment.py**: 3-method interface (reset/step/state) + RFC 004 Rubric injection
- **grader.py**: Deterministic scoring with explicit rubric weights (40+ test cases)
- **data_generator.py**: Seed-based synthetic data generation (50+ problem templates)
- **problem_templates.py**: Real UX issues from e-commerce domain (rage clicks, dead clicks, funnels, mobile breaks, etc.)
- **rubrics.py**: RFC 004 Rubric classes for RL training framework integration

**Quality Attributes:**

- ✅ 100% deterministic (seed-based reproducibility)
- ✅ Strict input validation (explicit action validation in environment.step)
- ✅ Dense per-step grading (not just terminal reward)
- ✅ Comprehensive test suite (pytest with 15+ test cases)
- ✅ RFC 004 compliant (Rubric interface for RL frameworks)
- ✅ Clean imports (supports both Docker and local dev)

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
docker build -t ux-insight-env:latest .
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
| easy | meta-llama/Llama-3.3-70B-Instruct | 70B | 0.8450 | 1 | True |
| medium | meta-llama/Llama-3.3-70B-Instruct | 70B | 0.8134 | 3 | True |
| hard | meta-llama/Llama-3.3-70B-Instruct | 70B | 0.7864 | 6 | True |
| easy | meta-llama/Llama-4-Scout-17B-16E-Instruct | 17Bx16E | 0.9250 | 1 | True |
| medium | meta-llama/Llama-4-Scout-17B-16E-Instruct | 17Bx16E | 0.6012 | 3 | True |
| hard | meta-llama/Llama-4-Scout-17B-16E-Instruct | 17Bx16E | 0.8262 | 6 | True |

Run details:

- Date: 2026-04-08
- Inference endpoint: `https://router.huggingface.co/v1/`
- Environment endpoint: `https://sushere-ux-insight-env.hf.space`
- Deterministic seeds: easy `101`, medium `202`, hard `303`
- Success threshold: `0.5`
- Multi-model baselines: set `RUN_ALL_BASELINES=true` to evaluate the current working baseline set

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
  inference.py
  models.py
  openenv.yaml
  pyproject.toml
  README.md
  Dockerfile
  static/
    index.html
    docs.html
  server/
    app.py
    data_generator.py
    environment.py
    grader.py
    problem_templates.py
    rubrics.py
    requirements.txt
    tests/
      __init__.py
      test_grader.py
```

## License

MIT
