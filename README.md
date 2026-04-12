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

- Space: https://huggingface.co/spaces/sushere/ux-insight-env
- API endpoint: https://sushere-ux-insight-env.hf.space
- Health check: `https://sushere-ux-insight-env.hf.space/health`

## Real-World Task

This environment models a practical workflow used by UX analysts and product teams at e-commerce companies:

1. Review behavioral analytics reports from tools such as Microsoft Clarity, Hotjar, or Mixpanel.
2. Inspect session summaries, heatmaps, rage-click reports, dead-click reports, funnel drop-offs, and device-specific metrics.
3. Identify the real UX friction points.
4. Avoid false positives from normal behavior, such as high exit rate on an order confirmation page.
5. Produce prioritized recommendations with expected metric impact.

This fills a useful benchmark gap: most agent environments test code, search, support, or planning, but not behavioral analytics interpretation and UX recommendation quality.

## API Usage

**Health check:**

```bash
curl https://sushere-ux-insight-env.hf.space/health
```

**Start an episode:**

```bash
curl -X POST https://sushere-ux-insight-env.hf.space/reset
```

**Start a deterministic easy episode with seed:**

```bash
curl -X POST https://sushere-ux-insight-env.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"seed": 101, "task_id": "easy"}'
```

**Submit an action (step):**

```bash
curl -X POST https://sushere-ux-insight-env.hf.space/step \
  -H "Content-Type: application/json" \
  -d '{
    "finding_type": "issue",
    "affected_element": "Flash Sale banner image",
    "issue_category": "dead_click",
    "severity": "high",
    "recommendation": "Make the Flash Sale banner image clickable and link it directly to the active flash sale page so users who tap the promotional banner reach the expected deals instead of waiting after a dead click.",
    "fix_category": "fix_broken_link",
    "impact_estimate": "Expected 20-30% reduction in dead clicks and measurable lift in flash sale click-through conversion.",
    "confidence": 0.9
  }'
```

## Action Space

The agent submits a `UXAction` for each page analyzed.

| Field | Type | Description |
|---|---|---|
| `finding_type` | `"issue"`, `"no_issue"`, or `"ambiguous"` | Whether the page contains a real UX issue, normal behavior, or an unclear signal. |
| `affected_element` | `str` | Specific UI element, such as `Add to Cart button`. Use `N/A` for no issue. |
| `issue_category` | `str` | Problem type, such as `rage_click`, `dead_click`, `funnel_dropoff`, `scroll_dropoff`, `mobile_layout_break`, `quickback`, `form_abandonment`, `cta_invisible`, `search_no_results`, `high_bounce`, `normal_behavior`, or `unclear`. |
| `severity` | `"critical"`, `"high"`, `"medium"`, `"low"`, or `"none"` | Severity assessment. Use `none` for `no_issue`. |
| `recommendation` | `str` | Specific actionable recommendation of at least 20 words. Must describe the exact change and reference the affected element. |
| `fix_category` | `str` | Fix type, such as `fix_broken_link`, `add_loading_state`, `fix_mobile_layout`, `reposition_element`, `increase_contrast`, `add_feedback`, `reduce_steps`, `redesign_element`, `no_fix_needed`, or `investigate_further`. |
| `impact_estimate` | `str` | Expected metric impact (e.g., "5-10% increase in click-through rate") or `N/A` for no issue. |
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
| `cumulative_score` | `float` | Running normalized score (strictly in (0, 1)). |
| `grader_feedback` | `str` | Feedback for the previous action. |
| `task_context` | `Dict[str, Any]` | App-level metadata. |
| `ground_truth` | `Optional[Dict]` | Hidden expected answer (only in teaching mode). |

`PageAnalyticsData` contains:
- Session counts, bounce rates (overall, mobile, desktop)
- Scroll-depth percentiles (p50, p80)
- Mobile/desktop session split
- Heatmap zones with click density and scroll metrics
- Behavioral signals (rage clicks, dead clicks, etc.) with rates and session counts
- Funnel steps (for multi-stage pages)
- Session recording summary

## Tasks

| Task | Pages | Description | Expected Difficulty |
|---|---:|---|---|
| **Easy** | 1 | One clear, high-signal UX issue such as a rage click or dead click on a high-traffic element. | Basic LLMs should identify it with 0.75+ score. |
| **Medium** | 3 | Three pages with multiple distinct issues, requiring multi-step reasoning and severity assessment across different problem types. | Requires prioritization; baseline ~0.65 score. |
| **Hard** | 6 | Six-page funnel analysis with real problems mixed with red herrings (pages with normal behavior) and clean pages. | Requires reasoning robustness and false-positive resistance; baseline ~0.45 score. |

## Reward Function

Each step receives dense partial credit based on 5 grading components, with anti-exploit penalties.

### Component Scoring (per step)

| Component | Weight | Scoring |
|---|---:|---|
| Element identification | 25% | Jaccard overlap of element names (0.01–0.99) |
| Issue category | 20% | Exact match (0.20), related (0.10), or unrelated (0.0) |
| Severity accuracy | 15% | Exact match (0.95), off-by-one (0.55), or wrong (0.05) |
| Recommendation quality | 25% | Keyword coverage + length (≥20 words) + element mention (0.01–0.99) |
| Fix category | 15% | Exact match (0.15), compatible (0.075), or incompatible (0.0) |

### Anti-Exploit Penalties

- **Duplicate finding**: -0.40 (same element + category submitted twice)
- **Inconsistency**: -0.20 (finding_type="issue" but severity="none")
- **Over-confidence on wrong**: -0.10 (grade < 0.3 but confidence > 0.8)
- **Minimal recommendation**: -0.15 (< 10 characters)

**Per-step reward**: `min(max(component_sum - penalties, 0.01), 0.99)`

### End-of-Episode Bonus (added at done=True)

1. **Priority ranking bonus** (medium/hard): +0.10 if findings correctly ordered by severity
2. **Red herring handling** (hard only): +0.10 for correctly identifying no-problem pages
3. **Impact estimate quality** (hard only): +0.05 if estimates include percentages + metrics
4. **False positive penalty**: -0.05 per low-score (< 0.1) issue finding

**Total episode bonus**: `[-0.10, +0.25]`

### Normalized Score

```
cumulative_score = sum(step_rewards + episode_bonus) / num_steps
Clamped strictly to (0.01, 0.99)
```

Example (hard task, 6 steps with 0.7 average reward + 0.10 bonus):
```
score = (0.7*6 + 0.10) / 6 = 4.30 / 6 = 0.717
```

## Episode Lifecycle

### Deterministic Reproducibility

All episodes are **100% deterministic** given a seed. The same `seed` + `task_id` produces:
- Identical analytics data
- Identical embedded ground-truth problems
- Identical expected recommendations

This enables reproducible evaluation across multiple runs and training iterations.

### Episode Flow

1. **`POST /reset`** → `UXObservation`
   - Initializes episode with deterministic problem set
   - Returns first page data, `done=False`

2. **`POST /step(action: UXAction)`** → `UXObservation` (repeat for all pages)
   - Grades the finding against embedded ground truth
   - Updates `cumulative_score` and `findings_so_far`
   - Returns next page or `done=True` when all pages analyzed

3. **After `done=True`**
   - Episode is terminal; further steps return `done=True, reward=-0.1`
   - **Must call `/reset`** to start a new episode

### Task-Specific Constraints

| Task | Max Steps |
|---|---:|
| Easy | 1 |
| Medium | 3 |
| Hard | 6 |

## Expected Performance

| Task | Expected Score Range | Baseline (Llama 3.3-70B) |
|---|---|---|
| **Easy** | 0.70–0.85 | 0.8450 |
| **Medium** | 0.50–0.70 | 0.8134 |
| **Hard** | 0.20–0.45 | 0.7864 |

Hard tasks target lower ranges due to red herring penalties and reasoning complexity.

## Why This Environment

### Real-World Workflow

This environment models the actual job at e-commerce companies:

```
Input:   Behavioral analytics (Clarity, Hotjar, Mixpanel)
Task:    Identify genuine UX friction vs. normal behavior
Output:  Prioritized findings + actionable recommendations
```

### Benchmark Gap

Unlike code/search/reasoning benchmarks, this tests:
- **Data interpretation**: Distinguish signal from noise in behavioral metrics
- **User empathy**: Understand intent behind rage clicks, dead clicks, quickbacks
- **Recommendation quality**: Propose specific, measurable fixes with realistic impact

### Code Architecture

**Core Components:**

- **models.py**: Pydantic types for `UXAction`, `UXObservation`, `UXState`
- **environment.py**: OpenEnv 3-method interface (reset/step/state)
- **grader.py**: Deterministic 5-component scoring with 40+ test cases
- **data_generator.py**: Seed-based synthetic analytics (50+ problem templates)
- **problem_templates.py**: Real UX issues (rage clicks, dead clicks, funnels, mobile breaks)
- **inference.py**: OpenAI-based baseline agent

**Quality Attributes:**

- ✅ 100% deterministic (seed-based reproducibility)
- ✅ Strict input validation in `step()`
- ✅ Dense per-step grading (not just terminal reward)
- ✅ Comprehensive test suite (test_grader.py with 20+ assertions)
- ✅ OpenEnv-compliant dual-import pattern (Docker + local dev)
- ✅ Score bounds enforced strictly to (0, 1)

## Setup & Installation

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

Validate with OpenEnv CLI:

```bash
openenv validate
```

Deploy to Hugging Face Spaces:

```bash
openenv push --repo-id your-username/ux-insight-env
```

## Baseline Inference

The baseline script evaluates agent performance using the Hugging Face inference router and OpenAI-compatible API.

### Setup

Set environment variables:

```bash
export API_BASE_URL="https://router.huggingface.co/v1/"
export MODEL_NAME="meta-llama/Llama-3.3-70B-Instruct"
export HF_TOKEN="hf_your_token_here"
```

### Run Inference

```bash
python inference.py
```

The script will:
1. Run all 3 tasks (easy → medium → hard) sequentially
2. Log structured `[START]`, `[STEP]`, `[END]` lines per hackathon format
3. Print final scores for each task

### Baseline Results

| Task | Model | Params | Score | Steps |
|---|---|---:|---:|---:|
| easy | meta-llama/Llama-3.3-70B-Instruct | 70B | 0.8450 | 1 |
| medium | meta-llama/Llama-3.3-70B-Instruct | 70B | 0.8134 | 3 |
| hard | meta-llama/Llama-3.3-70B-Instruct | 70B | 0.7864 | 6 |

**Test date**: April 8, 2026
**Inference endpoint**: https://router.huggingface.co/v1/
**Environment endpoint**: https://sushere-ux-insight-env.hf.space
**Deterministic seeds**: easy=101, medium=202, hard=303

## End-to-End Walkthrough

```
Step 1: reset()
→ Agent receives initial page (e.g., homepage analytics)
→ Observation contains: session counts, heatmap zones, behavioral signals

Step 2: Agent analyzes data
→ Agent identifies issues: "Users rage-clicking on CTA button (low contrast)"
→ Formulates UXAction with finding type, element, category, severity, recommendation

Step 3: step(action)
→ Environment grades finding against ground truth
→ Step reward computed: 0× 5 components - penalties
→ Environment returns next page or done=True

Step 4: Repeat for all pages
→ Easy: 1 page → agent stops after 1 step
→ Medium: 3 pages → steps 2 and 3
→ Hard: 6 pages → steps 2–6

Step 5: Terminal state
→ cumulative_score = avg(all step rewards + episode bonus)
→ Returns in (0.01, 0.99) range
```

## File Structure

```
ux_insight_env/
├── __init__.py
├── client.py
├── inference.py              # OpenAI-based baseline agent
├── models.py                 # Pydantic Action/Observation/State
├── openenv.yaml              # OpenEnv manifest
├── README.md
├── Dockerfile
├── pyproject.toml
├── server/
│   ├── __init__.py
│   ├── app.py                # FastAPI + create_app()
│   ├── environment.py        # UXInsightEnvironment (reset/step/state)
│   ├── grader.py             # 5-component grading
│   ├── data_generator.py     # Seed-based analytics generation
│   ├── problem_templates.py  # 50+ problem definitions
│   ├── rubrics.py            # RFC 004 Rubric classes
│   ├── requirements.txt
│   └── tests/
│       ├── __init__.py
│       └── test_grader.py    # 20+ test cases
└── static/
    └── (static HTML pages for /web and other routes)
```

## License

MIT

