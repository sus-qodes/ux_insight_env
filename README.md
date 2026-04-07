# UX Insight Analyst Environment

An OpenEnv reinforcement learning environment that benchmarks LLM agents on the real-world task of interpreting e-commerce behavioral analytics and producing actionable UX recommendations.

**Live:** [sushere-ux-insight-env.hf.space](https://sushere-ux-insight-env.hf.space) | **Playground:** [/web](https://sushere-ux-insight-env.hf.space/web) | **Docs:** [/documentation](https://sushere-ux-insight-env.hf.space/documentation)

---

## Why This Environment Exists

Most agent benchmarks test code generation, search, customer support, or planning. None test **behavioral analytics interpretation** -- the daily work of UX analysts and product teams at every e-commerce company.

UX analysts at companies like Amazon, Flipkart, and Shopify spend hours reviewing data from tools like Microsoft Clarity, Hotjar, and Mixpanel: heatmaps, rage-click reports, funnel drop-offs, device-specific metrics, and session recordings. They must separate real friction from noise, avoid false positives, and produce prioritized, actionable recommendations.

This environment models that workflow. The agent receives synthetic but realistic analytics data from **StyleMart**, a simulated fashion e-commerce platform, and must:

1. Identify which pages have genuine UX problems
2. Classify the issue type and severity correctly
3. Resist false positives from normal behavior patterns (red herrings)
4. Produce specific, element-level recommendations with expected metric impact

---

## How It Works

```
reset(task_id, seed)
  |
  v
Observation: page analytics (sessions, bounce rate, heatmaps, behavioral signals, funnels, session recordings)
  |
  v
Agent submits UXAction (finding_type, element, category, severity, recommendation, fix, impact, confidence)
  |
  v
Environment grades against embedded ground truth across 5 dimensions --> dense reward
  |
  v
Next page (or episode done)
```

The environment uses the standard OpenEnv three-method interface:

- `reset()` -- generates deterministic analytics data from a seed and returns the first page observation
- `step(action)` -- grades the agent's finding and returns reward, feedback, and the next page
- `state` -- returns internal state (ground truth, hidden from agent during evaluation)

---

## Tasks

| Task | Steps | Description |
|------|------:|-------------|
| **Easy** | 1 | One page with a single clear, high-signal UX issue (rage click or dead click). Signal identification. |
| **Medium** | 3 | Three pages with mixed severity levels. Requires multi-step reasoning and priority ranking. |
| **Hard** | 6 | Six-page funnel audit mixing real issues, red herrings, and clean pages. Requires false-positive resistance and cross-page reasoning. |

50 problem templates across 10 page types and 10 issue categories. 45 real problems + 5 red herrings. All data generation is deterministic and seeded.

---

## Action Space

The agent submits a `UXAction` for each page:

| Field | Type | Description |
|-------|------|-------------|
| `finding_type` | `"issue"` / `"no_issue"` / `"ambiguous"` | Whether the page has a real UX problem |
| `affected_element` | `str` | Specific UI element (e.g. "Add to Cart button") |
| `issue_category` | `str` | `rage_click`, `dead_click`, `funnel_dropoff`, `scroll_dropoff`, `mobile_layout_break`, `quickback`, `form_abandonment`, `cta_invisible`, `search_no_results`, `high_bounce`, `normal_behavior`, `unclear` |
| `severity` | `"critical"` / `"high"` / `"medium"` / `"low"` / `"none"` | Severity assessment |
| `recommendation` | `str` | Actionable recommendation (min 20 words, must name the element) |
| `fix_category` | `str` | `redesign_element`, `reposition_element`, `fix_broken_link`, `improve_copy`, `add_feedback`, `reduce_steps`, `increase_contrast`, `add_loading_state`, `fix_mobile_layout`, `no_fix_needed`, `investigate_further` |
| `impact_estimate` | `str` | Expected metric impact (e.g. "15-25% reduction in checkout abandonment") |
| `confidence` | `float` | Agent confidence, 0.0 to 1.0 |

## Observation Space

The agent receives a `UXObservation` at each step:

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | `str` | `easy`, `medium`, or `hard` |
| `task_description` | `str` | Natural-language task instructions |
| `current_step` / `total_steps` | `int` | Step progress |
| `pages_to_analyze` | `List[str]` | Page names for the episode |
| `current_page_data` | `PageAnalyticsData` | Full analytics for this page |
| `findings_so_far` | `List[FindingEntry]` | Prior submissions and rewards |
| `cumulative_score` | `float` | Running normalized score |
| `grader_feedback` | `str` | Feedback on previous action |
| `task_context` | `Dict` | App metadata (name, date range, device split) |

`PageAnalyticsData` includes: session counts, bounce rates, scroll-depth percentiles (p50/p80), mobile/desktop split, heatmap zones with click density, behavioral signals (type, element, rate, count), funnel steps (for checkout/cart), and a session recording summary.

---

## Reward System

### Per-Step Grading (dense, multi-component)

Each step is graded against embedded ground truth. Not binary pass/fail -- partial credit across five weighted dimensions:

| Dimension | Weight | Method |
|-----------|-------:|--------|
| Element identification | 25% | Keyword overlap (Jaccard) against ground truth element |
| Issue category | 20% | Exact match = 1.0, related category = 0.5 |
| Severity accuracy | 15% | Exact = 1.0, off-by-one = 0.5 |
| Recommendation quality | 25% | Keyword coverage + element mention + length check |
| Fix category | 15% | Exact match or compatible pair |

### Anti-Exploit Penalties

| Condition | Penalty |
|-----------|--------:|
| Duplicate finding (same element + category) | -0.40 |
| Inconsistent (issue + severity=none) | -0.20 |
| Invalid category values | -0.20 |
| Trivial recommendation (<10 chars) | -0.15 |
| Overconfident wrong (grade<0.3, confidence>0.8) | -0.10 |

### Episode-Level Bonuses (applied after final step)

| Bonus | Tasks | Range |
|-------|-------|------:|
| Priority ordering (severity ranking) | medium, hard | 0.00 to +0.10 |
| Red herring handling (correct no_issue) | hard | 0.00 to +0.10 |
| Impact estimate quality | hard | 0.00 to +0.05 |
| False positive penalty | all | -0.05 per FP |

---

## Baseline Scores

| Model | Params | Easy | Medium | Hard | Avg |
|-------|-------:|-----:|-------:|-----:|----:|
| meta-llama/Llama-3.3-70B-Instruct | 70B | 0.8867 | 0.5226 | 0.8448 | 0.7514 |
| meta-llama/Llama-4-Maverick-17B-128E-Instruct | 17Bx128E | -- | -- | -- | -- |
| meta-llama/Llama-4-Scout-17B-16E-Instruct | 17Bx16E | -- | -- | -- | -- |
| google/gemma-4-31b-it | 31B | -- | -- | -- | -- |
| Qwen/Qwen3.5-9B | 9B | -- | -- | -- | -- |

Run configuration:

- Inference endpoint: `https://router.huggingface.co/v1/`
- Environment endpoint: `https://sushere-ux-insight-env.hf.space`
- Deterministic seeds: easy `101`, medium `202`, hard `303`
- Temperature: 0.3
- Success threshold: 0.5

### Key Observations

- **Easy task is reliably solvable.** High-signal issues (rage clicks, dead clicks) are consistently identified by large LLMs with scores above 0.85.
- **Medium task is the hardest to score well on.** Multi-page severity ranking and prioritization challenges models more than raw signal detection.
- **Red-herring resistance is better than expected in larger models.** The hard task's 0.84 score reflects correct identification of both real issues and normal-behavior pages (e.g., high exit rate on order confirmation).
- **Recommendation specificity is the weakest dimension.** Models tend toward generic advice; element-specific, actionable recommendations with metric estimates score highest.

---

## Data Coverage

### Issue Categories (10)

`rage_click` (7 templates), `dead_click` (7), `funnel_dropoff` (5), `mobile_layout_break` (6), `quickback` (5), `scroll_dropoff` (4), `form_abandonment` (3), `cta_invisible` (3), `search_no_results` (2), `high_bounce` (3)

### Pages (10 -- StyleMart Platform)

`homepage` `/` | `category_page` `/category/{slug}` | `search_results` `/search?q={query}` | `product_detail_page` `/products/{id}` | `cart` `/cart` | `checkout` `/checkout` | `order_confirmation` `/order/confirmation/{id}` | `account_login` `/account/login` | `wishlist` `/wishlist` | `flash_sale` `/flash-sale`

### Red Herrings (5)

Normal behaviors that look anomalous: high exit rate on order confirmation (purchase complete), login page "bounces" (successful redirects), deep scroll on PDP (engaged review reading), low quickback from wishlist (efficient navigation).

---

## Quick Start

### API

```bash
# Health check
curl https://sushere-ux-insight-env.hf.space/health

# Start an easy episode
curl -X POST https://sushere-ux-insight-env.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"seed": 101, "episode_id": "easy"}'
```

### Python Client

```python
from client import UXInsightEnv
from models import UXAction

env = UXInsightEnv(base_url="https://sushere-ux-insight-env.hf.space")
await env.connect()
result = await env.reset(task_id="easy", seed=101)

action = UXAction(
    finding_type="issue",
    affected_element="Flash Sale banner image",
    issue_category="dead_click",
    severity="high",
    recommendation="Make the Flash Sale banner image clickable and link it to the flash sale page so users reach the expected deals.",
    fix_category="fix_broken_link",
    impact_estimate="Expected 20-30% reduction in dead clicks.",
    confidence=0.9,
)
result = await env.step(action)
```

### Run Baselines

```bash
# Single model
export HF_TOKEN="hf_..."
export MODEL_NAME="meta-llama/Llama-3.3-70B-Instruct"
python inference.py

# All 5 models
export RUN_ALL_BASELINES=true
python inference.py
```

### Docker

```bash
docker build -t ux-insight-env:latest -f server/Dockerfile .
docker run --rm -p 7860:7860 ux-insight-env:latest
```

### Validate

```bash
openenv validate
```

---

## Architecture

```
ux_insight_env/
  inference.py              Baseline evaluation (multi-model, async)
  models.py                 Pydantic types: UXAction, UXObservation, UXState
  client.py                 EnvClient subclass for remote/Docker connection
  openenv.yaml              OpenEnv spec (v1, port 7860, web interface enabled)
  pyproject.toml            Package metadata and dependencies
  static/
    index.html              Landing page (monochrome, served at /)
    docs.html               Documentation page (served at /documentation)
  server/
    app.py                  FastAPI entry point via create_app + custom routes
    environment.py          Core RL environment: reset(), step(), state
    grader.py               Deterministic grading (5 dimensions + penalties)
    data_generator.py       Seeded synthetic analytics generator
    problem_templates.py    50 problem templates (45 real + 5 red herrings)
    requirements.txt        Server dependencies
    Dockerfile              python:3.11-slim, single worker, port 7860
```

### Dependencies

Server: `openenv-core`, `fastapi`, `uvicorn`, `pydantic`. No ML models, no GPU, no heavy packages. Fits within 2 vCPU / 8 GB RAM.

Inference: `openai` (OpenAI-compatible client for HF endpoint), `huggingface_hub` (token management).

---

## Technical Details

### Determinism

All episode data is generated from a seed via `random.Random(seed)`. Same seed + same task = identical analytics data, identical ground truth, identical grading. Verified: two resets with seed=101 produce byte-identical responses.

### Grading Pipeline

1. Agent action is validated (category values, consistency checks)
2. Best-matching ground-truth problem is found via element keyword overlap + category match
3. Five-dimension grade is computed against the matched problem
4. Anti-exploit penalties are applied (duplicates, inconsistency, overconfidence, trivial output)
5. Episode-level bonuses computed after final step (priority ranking, red-herring handling, impact quality)

### Red Herring Design

Hard-task episodes embed pages where metrics look anomalous but behavior is normal:

| Signal | Page | Why It Is Normal |
|--------|------|------------------|
| 89% exit rate | order_confirmation | Purchase complete -- users leave |
| 76% "bounce" | account_login | Successful logins redirect away |
| Deep scroll + 3 min | product_detail_page | Users reading reviews thoroughly |
| 15% quickback | wishlist | Brief check, then navigate to product |

Agents must classify these as `no_issue` with `normal_behavior` category to score well.

---

## Links

| Resource | URL |
|----------|-----|
| HF Space | https://huggingface.co/spaces/sushere/ux-insight-env |
| Landing Page | https://sushere-ux-insight-env.hf.space/ |
| Playground | https://sushere-ux-insight-env.hf.space/web |
| Documentation | https://sushere-ux-insight-env.hf.space/documentation |
| API Schema | https://sushere-ux-insight-env.hf.space/docs |
| Health | https://sushere-ux-insight-env.hf.space/health |

## License

MIT
