# server/grader.py
# Deterministic grading logic for the UX Insight Analyst Environment.
# All graders return float in [0.0, 1.0]. Deterministic given the same inputs.

from typing import Any, Dict, List, Optional, Tuple

try:
    from ..models import UXAction, UXState, FindingEntry
except ImportError:
    from models import UXAction, UXState, FindingEntry

try:
    from .problem_templates import RELATED_CATEGORIES, COMPATIBLE_FIXES
except ImportError:
    from server.problem_templates import RELATED_CATEGORIES, COMPATIBLE_FIXES


# ---------------------------------------------------------------------------
# Utility: keyword matching
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> set:
    """Simple whitespace + punctuation tokenizer."""
    import re
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def keyword_overlap_score(text_a: str, text_b: str, threshold: float = 0.4) -> float:
    """Word-level Jaccard-like overlap between two strings, 0.0–1.0."""
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    score = len(intersection) / len(union)
    return min(score / threshold, 1.0) if threshold > 0 else score


def keyword_coverage_score(text: str, expected_keywords: List[str]) -> float:
    """Fraction of expected keywords that appear in text."""
    if not expected_keywords:
        return 1.0  # no keywords to match = perfect score
    text_lower = text.lower()
    matched = sum(1 for kw in expected_keywords if kw.lower() in text_lower)
    return matched / len(expected_keywords)


# ---------------------------------------------------------------------------
# Severity grading
# ---------------------------------------------------------------------------

_SEVERITY_RANKS = {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}


def grade_severity(predicted: str, expected: str) -> float:
    """Score severity accuracy. Exact match = 1.0, off-by-one = 0.5, else 0.0."""
    pred_rank = _SEVERITY_RANKS.get(predicted, 0)
    exp_rank = _SEVERITY_RANKS.get(expected, 0)
    diff = abs(pred_rank - exp_rank)
    if diff == 0:
        return 1.0
    elif diff == 1:
        return 0.5
    else:
        return 0.0


# ---------------------------------------------------------------------------
# Category relatedness
# ---------------------------------------------------------------------------

def are_related_categories(cat_a: str, cat_b: str) -> bool:
    return (cat_a, cat_b) in RELATED_CATEGORIES


def are_compatible_fix_categories(fix_a: str, fix_b: str) -> bool:
    return (fix_a, fix_b) in COMPATIBLE_FIXES


# ---------------------------------------------------------------------------
# Find best matching problem for an action
# ---------------------------------------------------------------------------

def find_best_matching_problem(
    action: UXAction,
    ground_truth_problems: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Find the ground-truth problem that best matches the agent's action.
    Returns None if no reasonable match exists."""
    if not ground_truth_problems:
        return None

    best: Optional[Dict[str, Any]] = None
    best_score = -1.0

    for prob in ground_truth_problems:
        if prob.get("red_herring"):
            continue  # Red herrings are handled separately

        # Score: element name overlap + category match
        elem_score = keyword_overlap_score(
            action.affected_element.lower(),
            prob["affected_element"].lower(),
            threshold=0.3,
        )
        cat_score = 1.0 if action.issue_category == prob["problem_type"] else (
            0.5 if are_related_categories(action.issue_category, prob["problem_type"]) else 0.0
        )
        combined = 0.6 * elem_score + 0.4 * cat_score

        if combined > best_score and combined > 0.15:  # Minimum match threshold
            best_score = combined
            best = prob

    return best


# ---------------------------------------------------------------------------
# Per-step grader (CORE)
# ---------------------------------------------------------------------------

def grade_step(
    action: UXAction,
    ground_truth_problems: List[Dict[str, Any]],
    current_page: str,
) -> float:
    """
    Grade a single step's finding against the ground truth for the current page.
    Returns float in [0.0, 1.0].
    """
    score = 0.0

    # Separate real problems from red herrings on THIS page
    real_probs = [p for p in ground_truth_problems if not p.get("red_herring")]
    red_herrings = [p for p in ground_truth_problems if p.get("red_herring")]
    has_only_red_herrings = len(real_probs) == 0 and len(red_herrings) > 0
    has_no_problems = len(ground_truth_problems) == 0

    # --- CASE 1: Page has NO real problems (clean page or red herring only) ---
    if has_no_problems or has_only_red_herrings:
        if action.finding_type == "no_issue":
            score += 0.50  # Correctly identified as no issue
            if action.issue_category in ("normal_behavior",):
                score += 0.30  # Correctly categorized
            if action.severity == "none":
                score += 0.20  # Correctly assessed severity
        elif action.finding_type == "ambiguous":
            score += 0.20  # Partial credit for uncertainty
        else:
            # Penalty for false positive (fabricating a problem)
            score -= 0.10
        return max(min(score, 1.0), 0.0)

    # --- CASE 2: Page has real problem(s) ---
    best_match = find_best_matching_problem(action, ground_truth_problems)

    if best_match is None:
        # Agent found wrong element or completely missed
        if action.finding_type == "no_issue":
            score -= 0.20  # Penalty for false negative
        elif action.finding_type == "ambiguous":
            score += 0.05  # Tiny credit for at least being uncertain
        return max(min(score, 1.0), 0.0)

    prob = best_match

    # 1. Element identification (0.25 weight)
    element_match = keyword_overlap_score(
        action.affected_element.lower(),
        prob["affected_element"].lower(),
        threshold=0.4,
    )
    score += 0.25 * element_match

    # 2. Issue category (0.20 weight)
    if action.issue_category == prob["problem_type"]:
        score += 0.20
    elif are_related_categories(action.issue_category, prob["problem_type"]):
        score += 0.10

    # 3. Severity accuracy (0.15 weight)
    severity_score = grade_severity(action.severity, prob["severity"])
    score += 0.15 * severity_score

    # 4. Recommendation quality (0.25 weight)
    rec_score = keyword_coverage_score(
        action.recommendation.lower(),
        prob.get("expected_keywords", []),
    )
    # Bonus if recommendation mentions the specific element
    if prob["affected_element"].lower() in action.recommendation.lower():
        rec_score = min(rec_score + 0.2, 1.0)
    # Penalize vague recommendations (under 20 words)
    if len(action.recommendation.split()) < 20:
        rec_score *= 0.5
    score += 0.25 * rec_score

    # 5. Fix category accuracy (0.15 weight)
    if prob.get("expected_fix_category") and action.fix_category == prob["expected_fix_category"]:
        score += 0.15
    elif prob.get("expected_fix_category") and are_compatible_fix_categories(
        action.fix_category, prob["expected_fix_category"]
    ):
        score += 0.07

    return max(min(score, 1.0), 0.0)


# ---------------------------------------------------------------------------
# Step reward (wraps grade + anti-exploit penalties)
# ---------------------------------------------------------------------------

def is_duplicate_finding(action: UXAction, prior_findings: List[FindingEntry]) -> bool:
    """Check if the agent is submitting a duplicate finding."""
    action_elem = action.affected_element.lower().strip()
    for f in prior_findings:
        if f.affected_element.lower().strip() == action_elem and f.issue_category == action.issue_category:
            return True
    return False


def compute_step_reward(
    step_grade: float,
    action: UXAction,
    state: "UXState",
) -> float:
    """
    Convert the step grade into the actual reward signal.
    Provides continuous partial progress + anti-exploit penalties.
    """
    base_reward = step_grade

    # Penalty: duplicate findings
    if is_duplicate_finding(action, state.findings_submitted):
        base_reward -= 0.40

    # Penalty: inconsistency (saying "issue" with severity "none")
    if action.finding_type == "issue" and action.severity == "none":
        base_reward -= 0.20

    # Penalty: over-confident on wrong findings
    if step_grade < 0.3 and action.confidence > 0.8:
        base_reward -= 0.10

    # Penalty: trivial / minimal-effort recommendation
    if len(action.recommendation.strip()) < 10:
        base_reward -= 0.15

    return max(min(base_reward, 1.0), -0.5)


# ---------------------------------------------------------------------------
# Episode-level grader (holistic bonuses after done=True)
# ---------------------------------------------------------------------------

def compute_priority_ranking_score(
    findings: List[FindingEntry],
    embedded_problem_ids: List[str],
) -> float:
    """Score how well the agent ranked issues by severity.
    1.0 if perfectly ordered critical > high > medium > low, 0.0 if reversed."""
    issue_findings = [f for f in findings if f.finding_type == "issue"]
    if len(issue_findings) < 2:
        return 0.5  # Not enough data to judge ranking

    _ranks = {"critical": 4, "high": 3, "medium": 2, "low": 1, "none": 0}
    severities = [_ranks.get(f.severity, 0) for f in issue_findings]

    # Count correctly ordered pairs
    correct = 0
    total = 0
    for i in range(len(severities)):
        for j in range(i + 1, len(severities)):
            total += 1
            if severities[i] >= severities[j]:
                correct += 1

    return correct / total if total > 0 else 0.5


def compute_red_herring_score(
    findings: List[FindingEntry],
    embedded_problem_ids: List[str],
) -> float:
    """Score how well the agent handled red herrings.
    1.0 if all red herrings correctly flagged as no_issue, 0.0 if all mislabeled."""
    # We need to know which findings correspond to red herring pages
    # For simplicity: any finding with finding_type="no_issue" on a page that only has
    # red herrings is counted as correct
    no_issue_count = sum(1 for f in findings if f.finding_type == "no_issue")
    # Give partial credit based on how many no_issues the agent submitted
    # (in hard task with 2 red herrings, ideal is at least 2 no_issue findings)
    expected_no_issues = 2  # hard task has 2 red herrings
    return min(no_issue_count / expected_no_issues, 1.0) if expected_no_issues > 0 else 1.0


def compute_impact_estimate_score(findings: List[FindingEntry]) -> float:
    """Score impact estimate quality. Rewards specific numerical estimates."""
    issue_findings = [f for f in findings if f.finding_type == "issue"]
    if not issue_findings:
        return 0.0

    scores = []
    for f in issue_findings:
        est = f.impact_estimate.lower()
        s = 0.0
        # Has a percentage or number
        if any(c.isdigit() for c in est):
            s += 0.5
        # Has a metric name
        metric_keywords = ["conversion", "bounce", "abandonment", "click", "engagement", "retention", "drop-off", "revenue"]
        if any(kw in est for kw in metric_keywords):
            s += 0.3
        # Not just "N/A"
        if est.strip() not in ("n/a", "na", "none", ""):
            s += 0.2
        scores.append(min(s, 1.0))

    return sum(scores) / len(scores)


def count_false_positives(
    findings: List[FindingEntry],
    embedded_problem_ids: List[str],
) -> int:
    """Count findings where agent reported an issue but the page had no real problem."""
    # Simple heuristic: very low-scoring issue findings are likely false positives
    return sum(
        1
        for f in findings
        if f.finding_type == "issue" and f.step_reward < 0.1
    )


def grade_episode(state: "UXState", task_id: str) -> float:
    """
    Compute final episode holistic bonus/penalty.
    Returns float in [-0.10, +0.25].
    """
    findings = state.findings_submitted
    embedded = state.embedded_problems

    bonus = 0.0

    # BONUS 1: Priority ordering (medium + hard)
    if task_id in ("medium", "hard"):
        prio_score = compute_priority_ranking_score(findings, embedded)
        bonus += 0.10 * prio_score

    # BONUS 2: Red herring handling (hard only)
    if task_id == "hard":
        rh_score = compute_red_herring_score(findings, embedded)
        bonus += 0.10 * rh_score

    # BONUS 3: Impact estimate quality (hard only)
    if task_id == "hard":
        impact_score = compute_impact_estimate_score(findings)
        bonus += 0.05 * impact_score

    # PENALTY: False positives
    fp_count = count_false_positives(findings, embedded)
    penalty = 0.05 * fp_count

    total = max(bonus - penalty, -0.10)
    return max(min(total, 0.25), -0.10)


# ---------------------------------------------------------------------------
# Grader feedback generator (for transparency to agent)
# ---------------------------------------------------------------------------

def generate_grader_feedback(
    step_grade: float,
    action: UXAction,
    ground_truth_problems: List[Dict[str, Any]],
) -> str:
    """Generate human-readable feedback for the agent about last step."""
    if step_grade >= 0.8:
        return f"Excellent analysis. Your finding was accurate and well-supported. Score: {step_grade:.2f}"
    elif step_grade >= 0.5:
        return f"Good analysis with room for improvement. Some aspects of the finding were correct. Score: {step_grade:.2f}"
    elif step_grade >= 0.2:
        return f"Partial credit. The analysis identified some relevant aspects but missed key details or mischaracterized the issue. Score: {step_grade:.2f}"
    elif step_grade > 0.0:
        return f"Weak analysis. The finding did not align well with the data signals present on this page. Score: {step_grade:.2f}"
    else:
        return f"Incorrect analysis. The finding does not match the data. Possible false positive or missed problem. Score: {step_grade:.2f}"
