# UX Insight Analyst - Quick Reference Guide

## Quick Links to Key Files

| Purpose | File | Lines | Key Classes/Functions |
|---------|------|-------|----------------------|
| **Data Models** | `models.py` | 1-166 | UXAction, UXObservation, UXState, PageAnalyticsData |
| **Environment** | `server/environment.py` | 1-500 | UXInsightEnvironment, reset(), step(), state |
| **Grading** | `server/grader.py` | 1-300+ | grade_step(), compute_step_reward(), grade_episode() |
| **Data Gen** | `server/data_generator.py` | 1-200+ | generate_episode_data() |
| **Problems** | `server/problem_templates.py` | - | PROBLEM_TEMPLATES, RELATED_CATEGORIES |
| **API Entry** | `server/app.py` | 1-134 | create_app(), /reset, /step, /ground_truth |
| **Frontend** | `static/playground.html` | 1-400+ | UI with Pydantic form auto-generation |

---

## API Endpoint Quick Reference

### Reset (Start Episode)
```bash
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{
    "seed": 101,
    "episode_id": "easy"
  }'
```
**Returns**: `UXObservation` (page 1/N, ground_truth, task_context)

### Step (Submit Action)
```bash
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{
    "finding_type": "issue",
    "affected_element": "Add to Cart button",
    "issue_category": "dead_click",
    "severity": "high",
    "recommendation": "Make the button clickable...",
    "fix_category": "fix_broken_link",
    "impact_estimate": "Expected 15-25% improvement",
    "confidence": 0.9
  }'
```
**Returns**: `UXObservation` (next page or done=true, reward, feedback)

### Ground Truth (Teaching Mode)
```bash
curl http://localhost:7860/ground_truth
```
**Returns**: Expected finding for current page (for auto-fill)

### Health Check
```bash
curl http://localhost:7860/health
```
**Returns**: `{"status": "ok"}`

### Get Schema
```bash
curl http://localhost:7860/schema
```
**Returns**: JSON schema for UXAction, UXObservation

---

## Data Model Reference

### UXAction (What Agent Submits)
```python
{
  "finding_type": "issue" | "no_issue" | "ambiguous",
  "affected_element": str,                    # Element name
  "issue_category": str,                      # rage_click, dead_click, funnel_dropoff, ...
  "severity": "critical" | "high" | "medium" | "low" | "none",
  "recommendation": str,                      # >=20 words required
  "fix_category": str,                        # redesign_element, fix_broken_link, ...
  "impact_estimate": str,                     # "Expected X-Y% improvement in metric"
  "confidence": float                         # 0.0-1.0
}
```

### UXObservation (What Agent Sees)
```python
{
  "task_id": "easy" | "medium" | "hard",
  "task_description": str,
  "current_step": int,                        # 1-indexed
  "total_steps": int,                         # 1, 3, or 6
  "pages_to_analyze": [str],                  # All page names
  "current_page_data": PageAnalyticsData,     # Current page only
  "findings_so_far": [FindingEntry],          # Prior submissions
  "cumulative_score": float,                  # [0.0-1.0]
  "grader_feedback": str,                     # NL feedback on prev step
  "task_context": dict,                       # App metadata
  "ground_truth": dict,                       # Teaching mode: expected answer
  "done": bool,
  "reward": float
}
```

### PageAnalyticsData (Current Page)
```python
{
  "page_name": str,
  "page_url_pattern": str,
  "total_sessions": int,
  "avg_session_duration_seconds": float,
  "bounce_rate": float,                       # 0.0-1.0
  "scroll_depth_p50": float,                  # 50th percentile
  "scroll_depth_p80": float,                  # 80th percentile
  "mobile_sessions_pct": float,               # % mobile traffic
  "mobile_bounce_rate": float,
  "desktop_bounce_rate": float,
  "heatmap_zones": [                          # Click density by zone
    {
      "zone_name": str,
      "click_density_pct": float,
      "scroll_depth_reached_pct": float | null
    }
  ],
  "behavioral_signals": [                     # Anomalies
    {
      "signal_type": str,                     # rage_click, dead_click, etc.
      "affected_element": str,
      "rate": float,                          # % of sessions
      "session_count": int
    }
  ],
  "funnel_steps": [                           # If applicable
    {
      "step_name": str,
      "sessions_entered": int,
      "sessions_dropped": int,
      "dropoff_rate": float
    }
  ],
  "session_recording_summary": str            # NL description
}
```

---

## Grading Rubric

### Per-Step Score (0.0-1.0)

| Component | Weight | Perfect | Partial | None |
|-----------|--------|---------|---------|------|
| **Element** | 25% | 0.25 (100% match) | 0.15 (60% match) | 0.0 |
| **Category** | 20% | 0.20 (exact) | 0.10 (related) | 0.0 |
| **Severity** | 15% | 0.15 (exact) | 0.075 (±1) | 0.0 |
| **Recommendation** | 25% | 0.25 (keywords + length + element) | 0.125 | 0.0 |
| **Fix Category** | 15% | 0.15 (exact) | 0.075 (compatible) | 0.0 |

**Anti-Exploit Penalties** (subtracted):
- Duplicate finding: −0.40
- Inconsistency (finding_type ≠ severity): −0.20
- Over-confidence on wrong: −0.10
- Minimal recommendation (<10 chars): −0.15

**Formula**: `base_score = sum(components)`, then `final = max(min(base - penalties, 1.0), -0.5)`

### End-of-Episode Bonus (−0.10 to +0.25)
- Priority ranking (medium/hard): +0.10
- Red herring handling (hard): +0.10 correct, −0.05 wrong
- Impact estimate quality (hard): +0.05
- False positive penalty (all): −0.05 per low-score finding

### Cumulative Score
```
cumulative_score = sum(step_rewards + final_bonus) / max_steps
Clipped to [0.0, 1.0]
```

---

## Problem Categories & Fixes

### Issue Categories (issue_category field)
```
rage_click          → User clicks repeatedly due to delayed feedback
dead_click          → User clicks element that's not interactive
funnel_dropoff      → Users abandon at step (conversion funnel)
scroll_dropoff      → Users not reaching below-fold content
mobile_layout_break → UI breaks on mobile (layout, overlaps)
quickback           → Users immediately go back (expectation mismatch)
form_abandonment    → Users leave mid-form (friction)
cta_invisible       → Call-to-action not visible/prominent
search_no_results   → Search returns no results (no suggestions)
high_bounce         → Users leave immediately (not engaged)
normal_behavior     → Metric is normal (use for no_issue)
unclear             → Signal is ambiguous
```

### Fix Categories (fix_category field)
```
redesign_element      → Redesign the UI element
reposition_element    → Move element to better location
fix_broken_link       → Make link/button actually work
improve_copy          → Improve text/messaging
add_feedback          → Add visual feedback (loading, confirmation)
reduce_steps          → Simplify process
increase_contrast     → Make element more visible
add_loading_state     → Show processing state
fix_mobile_layout     → Fix mobile responsiveness
no_fix_needed         → Use only for "no_issue" finding_type
investigate_further   → Need more data before deciding
```

---

## Difficulty & Task Breakdown

### Task Config

| Aspect | Easy | Medium | Hard |
|--------|------|--------|------|
| **# Pages** | 1 | 3 | 6 |
| **Clear issues** | 1 high-signal | 2-3 mixed | 3-4 real + red herrings |
| **Red herrings** | 0 | 0-1 | 2-3 |
| **Clean pages** | 0 | 0-1 | 1-2 |
| **Target score** | 0.70-0.85 | 0.50-0.70 | 0.20-0.45 |
| **Baseline** | 0.8450 | 0.8134 | 0.7864 |

### Score Interpretation
- **[0.85, 1.0]**: Excellent (all components perfect)
- **[0.70, 0.85]**: Good (minor component misses)
- **[0.50, 0.70]**: Fair (some good, some poor)
- **[0.30, 0.50]**: Below target (mixed accuracy)
- **[0.0, 0.30]**: Poor (significant errors)
- **Negative**: Validation error or major penalty

---

## Common Mistakes & Fixes

### ❌ Low Grading Reasons

| Issue | Symptom | Fix |
|-------|---------|-----|
| **Short recommendation** | `<20 words → ×0.5 penalty` | Use _generate_recommendation() for auto-fill |
| **Missing keywords** | Low keyword_coverage_score | Check expected_keywords in problem_templates |
| **Wrong element match** | Element token overlap too low | Use exact element name from PageAnalyticsData |
| **Inconsistent fields** | finding_type="issue" but severity="none" | Validate consistency in _validate_action |
| **No impact estimate** | impact_estimate = empty/generic | Include percentages: "Expected X-Y% improvement" |
| **Phantom problem** | No matching ground truth problem | Check if page actually has the issue |
| **Red herring false pos** | finding_type="issue" on clean page | Look for red_herring flag in embedded_problems |

### ✓ High Grading Procedures

1. **Match element correctly**: Use heatmap zone names + behavioral signal element names
2. **Use right category**: Pick from issue_category enum exactly
3. **Assess severity properly**: critical (>40% impact) → high (15-40%) → medium (5-15%) → low (<5%)
4. **Write detailed recommendation**: ≥20 words, mention element, include keywords
5. **Specify fix**: Use fix_category from enum (be concrete, not vague)
6. **Quantify impact**: "Expected X-Y% improvement in [metric]" (e.g., "10-20% reduction in dead clicks")
7. **Set confidence**: High (0.8+) if strong match, low (0.5-) if uncertain

---

## Development Workflow

### Local Setup
```bash
cd /d/openEnv/ux_insight_env

# Install dependencies
pip install -r server/requirements.txt

# Run server locally
uvicorn server.app:app --host 0.0.0.0 --port 7860

# Run tests
pytest server/tests/test_grader.py -v

# Test client
python -c "from client import UXInsightEnv; env = UXInsightEnv('http://localhost:7860')"
```

### Docker Build & Run
```bash
# Build
docker build -t ux-insight-env:latest .

# Run
docker run --rm -p 7860:7860 ux-insight-env:latest

# Check health
curl http://localhost:7860/health
```

### Validation
```bash
openenv validate  # Checks openenv.yaml, Dockerfile, app.py structure

openenv push --repo-id sushere/ux-insight-env --interface  # Deploy to HF
```

---

## Determinism Verification Checklist

- [ ] Seed used by data_generator: `random.Random(seed)` (not `random.seed()`)
- [ ] No hardcoded randomness in grade_step, compute_step_reward
- [ ] All RNG seeding happens ONCE in generate_episode_data
- [ ] _generate_recommendation & _generate_impact_estimate use deterministic templates
- [ ] Unit test: `test_generate_episode_data_deterministic` passes
- [ ] Manual test: Same seed produces identical observations

```python
# Manual verification
from server.data_generator import generate_episode_data

pages1, probs1 = generate_episode_data(seed=101, task_id="easy")
pages2, probs2 = generate_episode_data(seed=101, task_id="easy")

assert pages1[0].bounce_rate == pages2[0].bounce_rate
assert len(probs1) == len(probs2)
assert probs1[0]["problem_id"] == probs2[0]["problem_id"]
```

---

## Performance Profiling

### Latency Targets
| Endpoint | Target | Typical |
|----------|--------|---------|
| `POST /reset` | <100ms | 50ms (data generation) |
| `POST /step` | <50ms | 30ms (grading) |
| `GET /ground_truth` | <50ms | 20ms (lookup) |
| `GET /state` | <20ms | 5ms |

### Memory Footprint
- **Episode**: ~5-10 MB (pages_data + problems)
- **Concurrent sessions**: ~50 MB per episode

---

## Deployment Checklist

- [ ] `HEALTHCHECK` in Dockerfile (HF Spaces requirement)
- [ ] All server imports use dual pattern (try/except)
- [ ] Requirements.txt updated with all dependencies
- [ ] `openenv.yaml` correctly configured
- [ ] Tests pass: `pytest server/tests/ -v`
- [ ] Health check responds: `GET /health`
- [ ] Ground truth endpoint works: `GET /ground_truth`
- [ ] Playground loads: `GET /web`
- [ ] Static files embedded in HTML (not served separately)

---

## Troubleshooting

### "No active episode" on /ground_truth
**Cause**: Environment not initialized
**Fix**: Call `/reset` first, then `/ground_truth` before `/step`

### Import error in Docker
**Cause**: Relative imports failing in container
**Fix**: Verify dual import pattern in all server/*.py files

### Grading unexpectedly low
**Cause**: Recommendation missing keywords or too short
**Fix**: Check problem_templates for expected_keywords, ensure >=20 words

### Determinism test fails
**Cause**: Using `random.seed()` instead of `random.Random(seed)`
**Fix**: Always use `rng = random.Random(seed)` in data_generator

### HEALTHCHECK fails on HF Spaces
**Cause**: Missing `/health` endpoint
**Fix**: Ensure app.py includes health check route

---

## Key Insights

1. **Determinism is critical**: Enables reproducible eval, benchmarking across runs
2. **Grading is detailed**: 5 components + 4 penalties = sophisticated scoring
3. **Teaching mode is useful**: `/ground_truth` enables supervised learning for SFT
4. **OpenEnv factory handles state**: Don't manually manage singleton environment
5. **Static files are embedded**: No separate static file serving in Docker
6. **Red herrings are hard**: Correctly rejecting normal behavior as "no_issue" is key
7. **Recommendation quality matters**: 25% of score, must include keywords + length + element

