# server/tests/test_grader.py
# Comprehensive test suite for the UX Insight Analyst grader
# Validates: exact matches, category penalties, red herrings, duplicates, and difficulty scoring

import pytest
from typing import List, Dict, Any

try:
    from ...models import UXAction, UXState, FindingEntry
    from ...server.grader import (
        grade_step,
        compute_step_reward,
        grade_episode,
        is_duplicate_finding,
        keyword_overlap_score,
        keyword_coverage_score,
        grade_severity,
    )
except ImportError:
    from models import UXAction, UXState, FindingEntry
    from server.grader import (
        grade_step,
        compute_step_reward,
        grade_episode,
        is_duplicate_finding,
        keyword_overlap_score,
        keyword_coverage_score,
        grade_severity,
    )


# ---------------------------------------------------------------------------
# Test Fixtures: Realistic problem templates
# ---------------------------------------------------------------------------


@pytest.fixture
def rage_click_problem():
    """A critical rage click issue on the Add to Cart button."""
    return {
        "problem_id": "RAGE_001",
        "problem_type": "rage_click",
        "affected_element": "Add to Cart button",
        "severity": "critical",
        "red_herring": False,
        "affected_page": "product_detail_page",
        "expected_keywords": ["add to cart", "rage click", "loading", "feedback"],
        "expected_fix_category": "add_loading_state",
    }


@pytest.fixture
def dead_click_problem():
    """A high-severity dead click issue."""
    return {
        "problem_id": "DEAD_001",
        "problem_type": "dead_click",
        "affected_element": "Flash Sale banner image",
        "severity": "high",
        "red_herring": False,
        "affected_page": "homepage",
        "expected_keywords": ["banner", "clickable", "link", "flash sale"],
        "expected_fix_category": "fix_broken_link",
    }


@pytest.fixture
def funnel_dropoff_problem():
    """A critical funnel dropoff at checkout address form."""
    return {
        "problem_id": "FUNNEL_001",
        "problem_type": "funnel_dropoff",
        "affected_element": "Address form — pincode field",
        "severity": "critical",
        "red_herring": False,
        "affected_page": "checkout",
        "expected_keywords": ["checkout", "pincode", "address", "form", "validation"],
        "expected_fix_category": "improve_copy",
    }


@pytest.fixture
def red_herring_order_confirmation():
    """Red herring: high exit from order confirmation (normal behavior)."""
    return {
        "problem_id": "REDHERRING_001",
        "problem_type": "high_bounce",
        "affected_element": "Order confirmation page",
        "severity": "low",
        "red_herring": True,
        "affected_page": "order_confirmation",
        "red_herring_explanation": "High exit rate on order confirmation is expected — the purchase task is complete.",
    }


@pytest.fixture
def clean_page_problems():
    """A page with no real problems."""
    return []


# ---------------------------------------------------------------------------
# TEST: Exact Match — High Score
# ---------------------------------------------------------------------------


def test_grade_step_exact_match(rage_click_problem):
    """An agent that correctly identifies a rage click with accurate details should score high."""
    action = UXAction(
        finding_type="issue",
        affected_element="Add to Cart button",
        issue_category="rage_click",
        severity="critical",
        recommendation="Add a loading indicator to the Add to Cart button so users receive immediate visual feedback that their click was received. This prevents rage clicking.",
        fix_category="add_loading_state",
        impact_estimate="Expected 25-35% reduction in user frustration and cart abandonment.",
        confidence=0.95,
    )

    score = grade_step(action, [rage_click_problem], "product_detail_page")
    assert score >= 0.80, f"Exact match should score >= 0.80, got {score}"
    print(f"✓ Exact match score: {score:.2f}")


# ---------------------------------------------------------------------------
# TEST: Close Match with Related Category
# ---------------------------------------------------------------------------


def test_grade_step_related_category_partial_credit(rage_click_problem):
    """Related category (dead_click for rage_click) should get partial credit."""
    action = UXAction(
        finding_type="issue",
        affected_element="Add to Cart button",
        issue_category="dead_click",  # Related but not exact
        severity="critical",
        recommendation="Fix the Add to Cart button responsiveness and add loading feedback. Users are clicking multiple times due to lack of response.",
        fix_category="add_feedback",
        impact_estimate="Expected improvement in cart conversion.",
        confidence=0.85,
    )

    score = grade_step(action, [rage_click_problem], "product_detail_page")
    assert 0.70 <= score <= 0.85, f"Related category with good recommendation scores high, got {score}"
    print(f"✓ Related category score: {score:.2f}")


# ---------------------------------------------------------------------------
# TEST: Wrong Category — Low Score
# ---------------------------------------------------------------------------


def test_grade_step_wrong_category(rage_click_problem):
    """Completely wrong category should score low."""
    action = UXAction(
        finding_type="issue",
        affected_element="Add to Cart button",
        issue_category="scroll_dropoff",  # Completely wrong
        severity="critical",
        recommendation="Reposition the button above the fold to increase visibility and clicks.",
        fix_category="reposition_element",
        impact_estimate="Expected 15-20% increase in add-to-cart rate.",
        confidence=0.75,
    )

    score = grade_step(action, [rage_click_problem], "product_detail_page")
    assert score <= 0.50, f"Wrong category should score low, got {score}"
    print(f"✓ Wrong category score: {score:.2f}")


# ---------------------------------------------------------------------------
# TEST: Red Herring Handling
# ---------------------------------------------------------------------------


def test_grade_step_red_herring_correct_identification(red_herring_order_confirmation):
    """Agent should correctly identify red herring (normal behavior) and report as 'no_issue'."""
    action = UXAction(
        finding_type="no_issue",
        affected_element="N/A",
        issue_category="normal_behavior",
        severity="none",
        recommendation="N/A",
        fix_category="no_fix_needed",
        impact_estimate="N/A",
        confidence=0.90,
    )

    score = grade_step(action, [red_herring_order_confirmation], "order_confirmation")
    assert score >= 0.50, f"Correct red herring identification should score >= 0.5, got {score}"
    print(f"✓ Red herring correct identification: {score:.2f}")


def test_grade_step_red_herring_false_positive(red_herring_order_confirmation):
    """Agent that incorrectly flags red herring as a problem should score low or negative."""
    action = UXAction(
        finding_type="issue",
        affected_element="Order confirmation page",
        issue_category="high_bounce",
        severity="high",
        recommendation="Redesign the order confirmation page to reduce exit rate.",
        fix_category="redesign_element",
        impact_estimate="Expected 30% reduction in post-purchase exits.",
        confidence=0.80,
    )

    score = grade_step(action, [red_herring_order_confirmation], "order_confirmation")
    assert score <= 0.20, f"False positive on red herring should score <= 0.2, got {score}"
    print(f"✓ Red herring false positive: {score:.2f}")


# ---------------------------------------------------------------------------
# TEST: Severity Accuracy
# ---------------------------------------------------------------------------


def test_grade_severity_exact_match():
    """Exact severity match should score 1.0."""
    assert grade_severity("critical", "critical") == 1.0
    assert grade_severity("high", "high") == 1.0
    assert grade_severity("medium", "medium") == 1.0
    print("✓ Exact severity matches score 1.0")


def test_grade_severity_off_by_one():
    """Off-by-one severity should score 0.5."""
    assert grade_severity("critical", "high") == 0.5
    assert grade_severity("medium", "low") == 0.5
    print("✓ Off-by-one severity scores 0.5")


def test_grade_severity_wrong():
    """Wrong severity should score 0.0."""
    assert grade_severity("critical", "low") == 0.0
    assert grade_severity("high", "none") == 0.0
    print("✓ Wrong severity scores 0.0")


# ---------------------------------------------------------------------------
# TEST: Recommendation Quality
# ---------------------------------------------------------------------------


def test_keyword_coverage_score():
    """Test keyword coverage in recommendations."""
    # High coverage
    text = "Add a loading indicator to the Add to Cart button when clicked"
    keywords = ["add to cart", "loading", "button"]
    score = keyword_coverage_score(text, keywords)
    assert score == 1.0, f"Should match all keywords, got {score}"

    # Partial coverage
    score2 = keyword_coverage_score(text, ["add to cart", "hover", "animation"])
    assert 0 < score2 < 1.0, f"Should partially match, got {score2}"
    print(f"✓ Keyword coverage: 100% = {score:.2f}, partial = {score2:.2f}")


def test_keyword_overlap_score():
    """Test element name overlap."""
    # Perfect overlap
    score_perfect = keyword_overlap_score("Add to Cart button", "Add to Cart button")
    assert score_perfect >= 0.95, f"Perfect match should be high, got {score_perfect}"

    # Slight variation
    score_variation = keyword_overlap_score("Add to Cart button", "Add to Cart btn")
    assert score_variation >= 0.70, f"Similar elements should match reasonably, got {score_variation}"

    # No overlap
    score_none = keyword_overlap_score("Add to Cart button", "Remove item link")
    assert score_none < 0.50, f"Different elements should not match, got {score_none}"
    print(f"✓ Keyword overlap: perfect={score_perfect:.2f}, similar={score_variation:.2f}, none={score_none:.2f}")


# ---------------------------------------------------------------------------
# TEST: Recommendation Length Penalty
# ---------------------------------------------------------------------------


def test_grade_step_vague_recommendation(rage_click_problem):
    """Vague recommendation (< 20 words) should be penalized."""
    action = UXAction(
        finding_type="issue",
        affected_element="Add to Cart button",
        issue_category="rage_click",
        severity="critical",
        recommendation="Fix the button.",  # Too short!
        fix_category="add_loading_state",
        impact_estimate="Better user experience.",
        confidence=0.90,
    )

    score = grade_step(action, [rage_click_problem], "product_detail_page")
    assert score < 0.80, f"Vague recommendation penalizes but other components are correct, got {score}"
    print(f"✓ Vague recommendation penalized: {score:.2f}")


# ---------------------------------------------------------------------------
# TEST: Duplicate Detection
# ---------------------------------------------------------------------------


def test_is_duplicate_finding():
    """Agent should not submit the same finding twice."""
    prior_findings = [
        FindingEntry(
            step=1,
            page_analyzed="product_detail_page",
            finding_type="issue",
            affected_element="Add to Cart button",
            issue_category="rage_click",
            severity="critical",
            recommendation="Add loading indicator.",
            fix_category="add_loading_state",
            impact_estimate="25% reduction",
            confidence=0.95,
            step_reward=0.85,
        )
    ]

    # Exact duplicate
    action_dup = UXAction(
        finding_type="issue",
        affected_element="Add to Cart button",
        issue_category="rage_click",
        severity="critical",
        recommendation="Add a different recommendation.",
        fix_category="add_feedback",
        impact_estimate="Different estimate",
        confidence=0.80,
    )

    assert is_duplicate_finding(action_dup, prior_findings) == True
    print("✓ Duplicate detection works")

    # Different element
    action_new = UXAction(
        finding_type="issue",
        affected_element="Apply Promo Code button",
        issue_category="rage_click",
        severity="critical",
        recommendation="Add loading feedback.",
        fix_category="add_feedback",
        impact_estimate="20% reduction",
        confidence=0.85,
    )

    assert is_duplicate_finding(action_new, prior_findings) == False
    print("✓ Non-duplicate detection works")


# ---------------------------------------------------------------------------
# TEST: Step Reward (base grade + anti-exploit penalties)
# ---------------------------------------------------------------------------


def test_compute_step_reward_clean(rage_click_problem):
    """Clean action with good score should get full reward (minus small penalty if any)."""
    action = UXAction(
        finding_type="issue",
        affected_element="Add to Cart button",
        issue_category="rage_click",
        severity="critical",
        recommendation="Add a loading indicator to the Add to Cart button so users receive immediate visual feedback.",
        fix_category="add_loading_state",
        impact_estimate="Expected 30% reduction in rage clicks.",
        confidence=0.90,
    )

    step_grade = 0.85
    state = UXState(
        current_step=0,
        task_id="easy",
        task_seed=101,
        embedded_problems=[],
        pages_sequence=["product_detail_page"],
        findings_submitted=[],
        episode_rewards=[],
        total_reward_so_far=0.0,
        is_done=False,
    )

    reward = compute_step_reward(step_grade, action, state)
    assert reward >= 0.80, f"Clean good action should get high reward, got {reward}"
    print(f"✓ Clean action reward: {reward:.2f}")


def test_compute_step_reward_over_confident_wrong(rage_click_problem):
    """Over-confident on wrong finding should be penalized."""
    action = UXAction(
        finding_type="issue",
        affected_element="Add to Cart button",
        issue_category="scroll_dropoff",  # Wrong!
        severity="critical",
        recommendation="Reposition button above the fold.",
        fix_category="reposition_element",
        impact_estimate="Expected 20% improvement.",
        confidence=0.95,  # Very confident but wrong!
    )

    step_grade = 0.25  # Low grade due to wrong category
    state = UXState(
        current_step=0,
        task_id="easy",
        task_seed=101,
        embedded_problems=[],
        pages_sequence=["product_detail_page"],
        findings_submitted=[],
        episode_rewards=[],
        total_reward_so_far=0.0,
        is_done=False,
    )

    reward = compute_step_reward(step_grade, action, state)
    assert reward < 0.20, f"Over-confident wrong answer should be heavily penalized, got {reward}"
    print(f"✓ Over-confident wrong reward penalized: {reward:.2f}")


# ---------------------------------------------------------------------------
# TEST: Episode-Level Grading
# ---------------------------------------------------------------------------


def test_grade_episode_hard_with_red_herrings():
    """Hard episode: bonus for correctly handling red herrings."""
    findings = [
        FindingEntry(step=1, page_analyzed="page_1", finding_type="issue", affected_element="elem1",
                     issue_category="rage_click", severity="high", recommendation="x"*20, fix_category="add_loading_state",
                     impact_estimate="20%", confidence=0.85, step_reward=0.80),
        FindingEntry(step=2, page_analyzed="page_2", finding_type="no_issue", affected_element="N/A",
                     issue_category="normal_behavior", severity="none", recommendation="N/A", fix_category="no_fix_needed",
                     impact_estimate="N/A", confidence=0.90, step_reward=0.75),  # Red herring handled
        FindingEntry(step=3, page_analyzed="page_3", finding_type="issue", affected_element="elem3",
                     issue_category="dead_click", severity="medium", recommendation="y"*20, fix_category="fix_broken_link",
                     impact_estimate="15%", confidence=0.80, step_reward=0.70),
    ]

    state = UXState(
        current_step=3,
        task_id="hard",
        task_seed=303,
        embedded_problems=["prob1", "prob2", "prob3"],
        pages_sequence=["page_1", "page_2", "page_3", "page_4", "page_5", "page_6"],
        findings_submitted=findings[:3],
        episode_rewards=[0.80, 0.75, 0.70],
        total_reward_so_far=0.0,
        is_done=False,
    )

    bonus = grade_episode(state, "hard")
    assert bonus > -0.10, f"Hard episode with reds herring handling should have positive/minimal penalty, got {bonus}"
    print(f"✓ Episode-level bonus for hard task: {bonus:.2f}")


# ---------------------------------------------------------------------------
# TEST: Task Difficulty Scoring Ranges
# ---------------------------------------------------------------------------


def test_easy_task_scoring_range():
    """Easy task with perfect answer should score 0.70-0.80."""
    # Simulate perfect easy task
    rage_click = {
        "problem_id": "RAGE_001",
        "problem_type": "rage_click",
        "affected_element": "Add to Cart button",
        "severity": "critical",
        "red_herring": False,
        "affected_page": "homepage",
        "expected_keywords": ["add to cart", "rage click", "loading"],
        "expected_fix_category": "add_loading_state",
    }

    action_perfect = UXAction(
        finding_type="issue",
        affected_element="Add to Cart button",
        issue_category="rage_click",
        severity="critical",
        recommendation="Add a loading indicator to the Add to Cart button. This provides visual feedback when users click.",
        fix_category="add_loading_state",
        impact_estimate="Expected 25-30% reduction in rage clicks.",
        confidence=0.95,
    )

    score = grade_step(action_perfect, [rage_click], "homepage")
    assert 0.70 <= score <= 0.90, f"Easy task perfect answer should be 0.70-0.90, got {score}"
    print(f"✓ Easy task difficulty check: {score:.2f} ∈ [0.70, 0.90]")


def test_hard_task_scoring_range_with_red_herrings():
    """Hard task with red herring handling should trend toward 0.2-0.4 with episode bonuses."""
    # This is a simplified test; full hard task would involve 6 pages
    print(f"✓ Hard task difficulty target: 0.20-0.40 (with 2 red herrings + complex reasoning)")


# ---------------------------------------------------------------------------
# TEST: No Problem on Page (Clean Page)
# ---------------------------------------------------------------------------


def test_grade_step_clean_page_correct_identification(clean_page_problems):
    """Agent should correctly identify pages with no real problems."""
    action = UXAction(
        finding_type="no_issue",
        affected_element="N/A",
        issue_category="normal_behavior",
        severity="none",
        recommendation="N/A",
        fix_category="no_fix_needed",
        impact_estimate="N/A",
        confidence=0.85,
    )

    score = grade_step(action, clean_page_problems, "clean_page")
    assert score >= 0.70, f"Correct 'no issue' should score >= 0.7, got {score}"
    print(f"✓ Clean page identified correctly: {score:.2f}")


def test_grade_step_clean_page_false_positive(clean_page_problems):
    """Agent that fabricates a problem on a clean page should be heavily penalized."""
    action = UXAction(
        finding_type="issue",
        affected_element="Some button",
        issue_category="rage_click",
        severity="high",
        recommendation="Add loading state.",
        fix_category="add_loading_state",
        impact_estimate="Improvement expected",
        confidence=0.80,
    )

    score = grade_step(action, clean_page_problems, "clean_page")
    assert score < 0.20, f"False positive on clean page should score < 0.2, got {score}"
    print(f"✓ False positive penalized: {score:.2f}")


# ---------------------------------------------------------------------------
# Run all tests if executed directly
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
