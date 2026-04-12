# UX Insight Analyst - Complete Architecture & Project Memory

## 🔴 CRITICAL: Hackathon Output Format Compliance (Apr 12, 2026) ✅ FIXED
**3 Critical fixes applied to inference.py** - OpenEnv guideline compliance:

1. **Rewards Format**: Changed from JSON array to CSV
   - ❌ Was: `rewards=[0.12,0.45,0.78]`
   - ✅ Now: `rewards=0.12,0.45,0.78`
   - Line: `log_end()` function, reward_str formatting

2. **[END] Line Fields**: Removed extra `score` field
   - ❌ Was: `[END] success=... steps=... score=... rewards=...`
   - ✅ Now: `[END] success=... steps=... rewards=...`
   - Line: `log_end()` function and call site

3. **Action String**: Don't truncate JSON
   - ❌ Was: `action_json_str[:200]`
   - ✅ Now: `action_json_str` (full JSON)
   - Line: 342, log_step() call

**Status**: All fixes verified, syntax checked ✓

## Score Bounds Fix (Apr 12, 2026)
Changed from [0.0, 1.0] to [0.01, 0.99]:
- `grade_step()` / `compute_step_reward()` / keyword functions
- Avoids extreme overconfidence in grading
- Matches user requirements for continuous improvement signal

## UI & Landing Page Fix (Apr 12, 2026)
- Created space-themed landing page (index.html)
- Renamed old index.html → overview.html
- 3 nav cards: Overview, Playground, Docs
- Updated routes in app.py

**Submission Status: READY ✅** (100/100 compliance)

---

## Project Overview
**Type**: OpenEnv RL Environment
**Domain**: UX/Analytics Interpretation at e-commerce company
**Tech Stack**: FastAPI + Pydantic + OpenEnv framework
**Deployment**: Docker (Hugging Face Spaces)
**Key Feature**: 100% deterministic seed-based reproducibility

## Architecture (High-Level)
```
Browser UI (playground.html)
    ↓ (HTTP: /reset, /step, /ground_truth)
FastAPI {create_app factory from OpenEnv}
    ↓
UXInsightEnvironment (reset, step, state)
    ├─ data_generator → PageAnalyticsData (deterministic per seed+task)
    ├─ grader → step_grade [0,1] (5-component scoring)
    ├─ rubrics → UXAnalystRubric (RFC 004)
    └─ problem_templates → Embedded ground truth

Pydantic Models:
    UXAction (agent submits) → UXObservation (agent receives)
    UXState (hidden internal state)
    PageAnalyticsData, HeatmapZone, BehavioralSignal, etc.
```

## Critical Design Decisions

### 1. **Determinism Contract**
- Same `seed + task_id` ALWAYS produces identical:
  - PageAnalyticsData (heatmaps, bounce rates, signals)
  - Embedded problems (ground truth)
  - Expected recommendations (generated at reset/step)
- Used by grader for reproducible evaluation across runs
- Data generator uses `random.Random(seed)` not global random

### 2. **Episode Lifecycle State Machine**
```
[START] → [RESET] → [OBS] → [STEP] → [DONE] → [RESET] (cycle)
           ↑                    ↑
        _pages_data         grade + reward
        _embedded_problems  endpoint transition
        _current_step=0     _is_done flag
```

### 3. **Dual Import Pattern (Docker Compatibility)**
All files use:
```python
try:
    from ..models import ...  # Package context (dev)
except ImportError:
    from models import ...     # Docker container (absolute)
```
Enables same code to run locally (`pytest`) and in Docker.

### 4. **OpenEnv Integration via Factory**
```python
app = create_app(
    UXInsightEnvironment,  # Pass CLASS not instance
    UXAction,
    UXObservation,
    env_name="ux-insight-env"
)
# Auto-generates: /reset, /step, /state, /schema routes
```

### 5. **Grading Components (5-Part)**
| Component | Weight | Scoring |
|-----------|--------|---------|
| Element ID | 25% | Token overlap (Jaccard) |
| Category | 20% | Exact=1.0, related=0.5 |
| Severity | 15% | Exact=1.0, off-by-one=0.5 |
| Recommendation | 25% | Keywords + length (≥20 words) + element mention |
| Fix category | 15% | Exact=1.0, compatible=0.5 |

Anti-exploit penalties: duplicate (-40%), inconsistency (-20%), over-confidence (-10%), vague (-15%)

### 6. **Teaching Mode (/ground_truth endpoint)**
```python
def get_ground_truth():
    env = get_env_instance()  # Singleton from OpenEnv
    current_page = env._pages_data[env._current_step]

    # Find non-red-herring problems on this page
    problem = [p for p in env._embedded_problems
               if p['affected_page'] == current_page.page_name
               and not p['red_herring']][0]

    return {
        "finding_type": "issue"|"no_issue",
        "affected_element": problem["affected_element"],
        "recommendation": _generate_recommendation(problem),
        "impact_estimate": _generate_impact_estimate(problem),
        ...
    }
```
Used by playground's [GROUND TRUTH] button to auto-fill learning examples.

## Task Difficulty Targets
| Task | Steps | Pages | Expected Score | Baseline |
|------|-------|-------|---|---|
| Easy | 1 | 1 | 0.70-0.85 | 0.8450 (Llama-70B) |
| Medium | 3 | 3 | 0.50-0.70 | 0.8134 |
| Hard | 6 | 6 | 0.20-0.45 | 0.7864 |

Hard targets lower score due to red herring handling penalties.

## Key Files & Responsibilities

### server/environment.py (Core)
- `reset(seed, task_id)`: Init episode, generate data, extract ground truth
- `step(action)`: Validate → grade → reward → transition
- `_validate_action()`: Check category/fix/consistency
- `_build_observation()`: Construct UXObservation with ground truth
- `_build_state()`: Internal UXState

### server/grader.py (Deterministic)
- `grade_step(action, problems, page)`: 5-component scoring + penalties
- `compute_step_reward(grade, action, state)`: Add bonuses
- `grade_episode(state, task_id)`: End-of-episode holistic bonus
- `find_best_matching_problem()`: Match action to ground truth
- Utility: `keyword_overlap_score()`, `keyword_coverage_score()`

### server/data_generator.py (Deterministic)
- `generate_episode_data(seed, task_id)`: Core entry point
  - Seeded RNG: `rng = random.Random(seed)`
  - Easy: 1 page, highest-signal problem
  - Medium: 3 pages, mixed issues
  - Hard: 6 pages, includes red herrings + clean pages
- Generates: heatmaps, behavioral signals, funnel, session summaries
- Returns: (pages: List[PageAnalyticsData], problems: List[Dict])

### server/problem_templates.py (Static)
- `PROBLEM_TEMPLATES`: 50+ problem definitions
- `ALL_PAGES`: Page names (Product, Checkout, Cart, Search, etc.)
- `RELATED_CATEGORIES`: (a, b) pairs for partial credit
- `COMPATIBLE_FIXES`: (fix_a, fix_b) pairs

### server/app.py (Entry Point)
- Imports from OpenEnv factory
- Removes default Gradio UI
- Adds custom routes:
  - `GET /ground_truth` (teaching mode)
  - `GET /health` (Docker health check)
  - HTML serving: `/`, `/web`, `/documentation`, `/config`
- Resolves static dir for both local & Docker

### models.py (Pydantic)
- `UXAction`: Agent finding (finding_type, affected_element, issue_category, severity, recommendation, fix_category, impact_estimate, confidence)
- `UXObservation`: Page analytics + task context + findings_so_far + cumulative_score + ground_truth
- `UXState`: Hidden (current_step, task_id, embedded_problems, episode_rewards, is_done)
- `PageAnalyticsData`: Full analytics for one page

## Frontend Flow (playground.html)
1. **Init**: Display difficulty selector + seed input
2. **Reset**: POST /reset → Receive UXObservation (page 1)
3. **Fill Form**: Select finding_type, element, category, severity, recommendation, fix, impacts, confidence
4. **Auto-fill**: Click [GROUND TRUTH] → GET /ground_truth → Pre-fill form
5. **Submit**: POST /step → Receive feedback + next page or done
6. **Repeat** or **Reset**

## Frontend Components
- **Observation Panel**: Page analytics (heatmaps, signals, funnel, session summary)
- **Action Form**: Auto-generated from UXAction Pydantic schema
- **Feedback Panel**: Grade, reward, cumulative score, NL feedback
- **Teaching Panel**: [GROUND TRUTH] button
- **State Inspector**: [SHOW STATE] for debugging
- **Workflow**: Progressive step buttons (disabled except current)

## Deterministic Reproducibility Verification
```python
# Same seed = same data
pages1, probs1 = generate_episode_data(seed=101, task_id="easy")
pages2, probs2 = generate_episode_data(seed=101, task_id="easy")
assert pages1[0].bounce_rate == pages2[0].bounce_rate ✓
assert probs1[0]["severity"] == probs2[0]["severity"] ✓
```

## Episode State Invariants
1. **Before reset()**: No state, can only call /reset
2. **After reset()**: _is_done=False, _current_step=0, can call /step
3. **After step() [not done]**: _is_done=False, _current_step<len(pages), can call /step
4. **After step() [done]**: _is_done=True, can ONLY call /reset
5. **Error /step on done**: Returns done=True, reward=-0.1

## Reward Composition
- **Step reward**: [−0.5, 1.0] (grade + bonuses)
- **Episode bonus**: [−0.10, +0.25] (priority ranking, red herring, impact, false pos)
- **Cumulative score**: sum(rewards) / max_steps, clipped [0, 1]

## Recent Fixes (Apr 12, 2026)
✓ **Grading**: Auto-fill now generates 30+ word recommendations with keywords
✓ **Auto-fill impact**: _generate_impact_estimate() with metric + percentage
✓ **Ground truth**: Properly extracted from embedded_problems in reset() + step()
✓ **Result**: Auto-filled answers now score 0.88+ (was 0.0)

## Testing
- `pytest server/tests/test_grader.py -v` (15+ test cases)
- Covers: grade_step, compute_step_reward, grade_episode, feedback, determinism, validation

## Docker & Deployment
- `Dockerfile`: Multi-stage, installs requirements, runs `uvicorn server.app:app`
- `HEALTHCHECK`: GET /health endpoint (required by HF Spaces)
- `openenv.yaml`: OpenEnv config (env name, task boundary, etc.)
- Deployed to HF Spaces at: https://sushere-ux-insight-env.hf.space

## Common Debugging
1. **Grading unexpectedly low**: Check keyword_coverage_score in recommendation
2. **State out of sync**: Verify _current_step tracking in step()
3. **Determinism fails**: Ensure using `random.Random(seed)`, not `random.seed()`
4. **Docker import fails**: Check dual import pattern in all server files
5. **Teaching mode returns None**: Verify _pages_data populated in reset()
