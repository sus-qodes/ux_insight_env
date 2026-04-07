# server/data_generator.py
# Deterministic synthetic analytics data generator for the UX Insight Analyst Environment.
# Accepts a seed + task_id and produces reproducible PageAnalyticsData with embedded problems.

import random
from typing import Any, Dict, List, Tuple

try:
    from ..models import PageAnalyticsData, HeatmapZone, BehavioralSignal, FunnelStep
except ImportError:
    from models import PageAnalyticsData, HeatmapZone, BehavioralSignal, FunnelStep

try:
    from .problem_templates import (
        PROBLEM_TEMPLATES,
        ALL_PAGES,
        PAGE_URL_PATTERNS,
        PAGE_HEATMAP_ZONES,
    )
except ImportError:
    from server.problem_templates import (
        PROBLEM_TEMPLATES,
        ALL_PAGES,
        PAGE_URL_PATTERNS,
        PAGE_HEATMAP_ZONES,
    )


# ---------------------------------------------------------------------------
# Session recording summary templates
# ---------------------------------------------------------------------------

_SUMMARY_TEMPLATES_NORMAL = [
    "Session recordings show typical browsing behavior. Users navigate through the page content at a steady pace with no unusual interaction patterns.",
    "Replay analysis reveals standard e-commerce browsing. Users scroll to view products, click on items of interest, and move through the funnel as expected.",
    "Aggregated sessions show healthy engagement. Users interact with primary CTAs and content sections without signs of frustration or confusion.",
]

_SUMMARY_TEMPLATES_PROBLEM: Dict[str, List[str]] = {
    "rage_click": [
        "Multiple sessions show users repeatedly clicking {element} with increasing speed. The element appears unresponsive for 2-5 seconds after each click. Users show visible frustration through rapid successive clicks.",
        "Session replays reveal a clear pattern: users click {element}, wait briefly, then click rapidly 5-8 more times. No visual feedback is provided between clicks.",
    ],
    "dead_click": [
        "Users frequently click on {element} and pause, seemingly expecting a navigation or modal to open. Nothing happens. Many users then look around the page for an alternative path.",
        "Recordings show users clicking {element} and waiting. The element styled like an interactive element (underlined text / button shape) but triggers no action.",
    ],
    "funnel_dropoff": [
        "Session recordings at the {element} step show users starting to fill in data, encountering an error or hesitation, and then abandoning the flow entirely.",
        "Users reach {element} and slow down significantly. Many begin backspacing or moving between fields repeatedly before leaving the page.",
    ],
    "scroll_dropoff": [
        "Heatmap and scroll data show that users stop scrolling well before reaching {element}. Content above the fold captures attention, but nothing motivates further scrolling.",
        "The majority of users slow their scroll speed and then reverse direction before reaching the primary CTA near {element}.",
    ],
    "mobile_layout_break": [
        "Mobile session replays show {element} rendering incorrectly. Elements overlap, causing confusion. Desktop sessions for the same page show no such issues.",
        "On mobile viewports, {element} is either partially hidden or overlaps other content. Users attempt to interact but mis-tap adjacent elements.",
    ],
    "quickback": [
        "Users navigate to this page and almost immediately hit the back button. The transition from the previous page sets an expectation that this page doesn't meet.",
        "Quick-return behavior is prominent. Users arrive, scan briefly, and return within 3-5 seconds. The content does not match what they expected from the linking page.",
    ],
    "form_abandonment": [
        "Users begin filling out the form at {element} but abandon partway through. Common friction points include unclear field labels and lack of input formatting hints.",
        "Session replays show users interacting with {element}, encountering validation errors, attempting corrections, and ultimately leaving.",
    ],
    "cta_invisible": [
        "Session recordings show users scrolling past {element} without noticing it. The element blends into the surrounding background due to low visual contrast.",
        "Users scan the page but do not interact with {element}. Eye-tracking patterns (inferred from cursor movement) suggest the element is not visually prominent enough.",
    ],
    "search_no_results": [
        "Users type queries into the search bar and receive empty result pages. There are no suggestions, spelling corrections, or alternative product recommendations.",
        "Search sessions show users trying 2-3 variations of their query, receiving no results each time, and then exiting the site.",
    ],
    "high_bounce": [
        "Users arrive on this page and leave within a few seconds. The page either loads slowly or the above-fold content does not engage them.",
        "Bounce behavior shows users landing, brief scanning the hero area, and leaving without scrolling or clicking anything.",
    ],
}


def _pick_summary(
    problem_type: str, element: str, rng: random.Random
) -> str:
    templates = _SUMMARY_TEMPLATES_PROBLEM.get(problem_type, _SUMMARY_TEMPLATES_NORMAL)
    template = rng.choice(templates)
    return template.replace("{element}", element)


# ---------------------------------------------------------------------------
# Heatmap zone generator
# ---------------------------------------------------------------------------

def generate_heatmap_zones(
    page_name: str,
    problems: List[Dict[str, Any]],
    rng: random.Random,
) -> List[HeatmapZone]:
    zone_names = PAGE_HEATMAP_ZONES.get(page_name, ["main_content", "header", "footer"])
    zones: List[HeatmapZone] = []
    # Distribute click density (must sum to ~1.0)
    raw = [rng.random() for _ in zone_names]
    total = sum(raw)
    densities = [r / total for r in raw]

    for name, density in zip(zone_names, densities):
        zones.append(
            HeatmapZone(
                zone_name=name,
                click_density_pct=round(density, 3),
                scroll_depth_reached_pct=round(rng.uniform(0.2, 0.95), 2),
            )
        )
    return zones


# ---------------------------------------------------------------------------
# Funnel data generator (for checkout / cart pages)
# ---------------------------------------------------------------------------

_CHECKOUT_FUNNEL_STEPS = [
    "cart_review",
    "address_entry",
    "payment_selection",
    "order_review",
    "order_placed",
]

_CART_FUNNEL_STEPS = [
    "view_cart",
    "update_quantity",
    "apply_promo",
    "proceed_to_checkout",
]


def generate_funnel_data(
    page_name: str,
    problems: List[Dict[str, Any]],
    rng: random.Random,
) -> List[FunnelStep]:
    if page_name == "checkout":
        step_names = _CHECKOUT_FUNNEL_STEPS
    elif page_name == "cart":
        step_names = _CART_FUNNEL_STEPS
    else:
        return []

    funnel: List[FunnelStep] = []
    entered = rng.randint(2000, 8000)
    for step_name in step_names:
        # Check if any problem specifies a dropoff at this step
        problem_dropoff: float | None = None
        for p in problems:
            sig = p.get("synthetic_signal", {})
            if sig.get("step") == step_name:
                problem_dropoff = sig.get("dropoff_rate")
                break

        if problem_dropoff is not None:
            dropoff_rate = problem_dropoff
        else:
            dropoff_rate = round(rng.uniform(0.05, 0.18), 2)

        dropped = int(entered * dropoff_rate)
        funnel.append(
            FunnelStep(
                step_name=step_name,
                sessions_entered=entered,
                sessions_dropped=dropped,
                dropoff_rate=round(dropoff_rate, 3),
            )
        )
        entered = max(entered - dropped, 10)

    return funnel


# ---------------------------------------------------------------------------
# Session recording summary generator
# ---------------------------------------------------------------------------

def generate_session_summary(
    page_name: str,
    problems: List[Dict[str, Any]],
    rng: random.Random,
) -> str:
    if not problems:
        return rng.choice(_SUMMARY_TEMPLATES_NORMAL)

    # Pick the most severe non-red-herring problem for the narrative
    real_probs = [p for p in problems if not p.get("red_herring")]
    if not real_probs:
        # All are red herrings — use generic
        return rng.choice(_SUMMARY_TEMPLATES_NORMAL) + " Some metrics may look anomalous but are within expected ranges for this page's purpose."

    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    real_probs.sort(key=lambda p: severity_order.get(p["severity"], 4))
    primary = real_probs[0]

    summary = _pick_summary(primary["problem_type"], primary["affected_element"], rng)
    if len(real_probs) > 1:
        summary += f" Additionally, secondary patterns observed around '{real_probs[1]['affected_element']}'."
    return summary


# ---------------------------------------------------------------------------
# Page data generator
# ---------------------------------------------------------------------------

def generate_page_data(
    page_name: str,
    problems: List[Dict[str, Any]],
    rng: random.Random,
) -> PageAnalyticsData:
    """Generate realistic analytics data for one page, embedding the given problems."""

    # Base metrics — realistic e-commerce ranges with noise
    total_sessions = rng.randint(1500, 12000)
    avg_duration = round(rng.uniform(60, 300), 1)
    bounce_rate = round(rng.uniform(0.25, 0.45), 3)
    scroll_p50 = round(rng.uniform(40, 65), 1)
    scroll_p80 = round(rng.uniform(65, 85), 1)
    mobile_pct = round(rng.uniform(0.55, 0.75), 2)
    mobile_bounce = round(rng.uniform(0.28, 0.42), 3)
    desktop_bounce = round(rng.uniform(0.20, 0.35), 3)

    behavioral_signals: List[BehavioralSignal] = []

    for problem in problems:
        signal_data = problem["synthetic_signal"]

        if problem.get("red_herring"):
            rate = signal_data.get(
                "bounce_rate",
                signal_data.get("rate", signal_data.get("quickback_rate", 0.0)),
            )
            signal = BehavioralSignal(
                signal_type=problem["problem_type"],
                affected_element=problem["affected_element"],
                rate=round(rate, 3),
                session_count=int(total_sessions * rng.uniform(0.7, 0.95)),
            )
        else:
            rate = (
                signal_data.get("rage_click_rate")
                or signal_data.get("dead_click_rate")
                or signal_data.get("dropoff_rate")
                or signal_data.get("quickback_rate")
                or signal_data.get("abandonment_rate")
                or signal_data.get("no_results_rate")
                or signal_data.get("bounce_rate")
                or signal_data.get("click_rate")
                or 0.0
            )
            signal = BehavioralSignal(
                signal_type=problem["problem_type"],
                affected_element=problem["affected_element"],
                rate=round(rate, 3),
                session_count=signal_data.get("session_count", total_sessions),
            )

            # Override page-level metrics when problem specifies them
            if "mobile_bounce_rate" in signal_data:
                mobile_bounce = signal_data["mobile_bounce_rate"]
                desktop_bounce = signal_data.get("desktop_bounce_rate", desktop_bounce)
                mobile_pct = signal_data.get("mobile_sessions_pct", mobile_pct)
            if "scroll_depth_p50" in signal_data:
                scroll_p50 = signal_data["scroll_depth_p50"]
                scroll_p80 = signal_data.get("scroll_depth_p80", scroll_p80)
            if "bounce_rate" in signal_data:
                bounce_rate = signal_data["bounce_rate"]

        behavioral_signals.append(signal)

    # Add 1-3 normal noise signals so the agent can't assume every signal is a problem
    noise_count = rng.randint(1, 3)
    noise_types = ["normal_scroll", "normal_click", "standard_engagement"]
    noise_elements = ["page body", "navigation links", "content area"]
    for i in range(noise_count):
        behavioral_signals.append(
            BehavioralSignal(
                signal_type=rng.choice(noise_types),
                affected_element=rng.choice(noise_elements),
                rate=round(rng.uniform(0.01, 0.10), 3),
                session_count=rng.randint(100, 500),
            )
        )

    # Generate funnel for checkout/cart
    funnel = None
    if page_name in ("checkout", "cart"):
        funnel = generate_funnel_data(page_name, problems, rng)

    recording_summary = generate_session_summary(page_name, problems, rng)

    return PageAnalyticsData(
        page_name=page_name,
        page_url_pattern=PAGE_URL_PATTERNS.get(page_name, f"/{page_name}"),
        total_sessions=total_sessions,
        avg_session_duration_seconds=avg_duration,
        bounce_rate=round(bounce_rate, 3),
        scroll_depth_p50=round(scroll_p50, 1),
        scroll_depth_p80=round(scroll_p80, 1),
        mobile_sessions_pct=round(mobile_pct, 2),
        mobile_bounce_rate=round(mobile_bounce, 3),
        desktop_bounce_rate=round(desktop_bounce, 3),
        heatmap_zones=generate_heatmap_zones(page_name, problems, rng),
        behavioral_signals=behavioral_signals,
        funnel_steps=funnel,
        session_recording_summary=recording_summary,
    )


# ---------------------------------------------------------------------------
# Episode data generator (main entry point)
# ---------------------------------------------------------------------------

def generate_episode_data(
    seed: int,
    task_id: str,
) -> Tuple[List[PageAnalyticsData], List[Dict[str, Any]]]:
    """
    Deterministically generate one episode's worth of analytics data.

    Returns
    -------
    pages_data : List[PageAnalyticsData]
        One PageAnalyticsData per step. The agent reviews them in order.
    embedded_problems : List[dict]
        The full problem templates that were embedded (for the grader).
    """
    rng = random.Random(seed)
    expected_steps = {"easy": 1, "medium": 3, "hard": 6}.get(task_id, 1)

    real_problems = [p for p in PROBLEM_TEMPLATES if not p.get("red_herring")]
    red_herrings = [p for p in PROBLEM_TEMPLATES if p.get("red_herring")]

    def _unique_pages(problems: List[Dict[str, Any]]) -> List[str]:
        pages = list({p["affected_page"] for p in problems})
        rng.shuffle(pages)
        return pages

    def _sample_one_per_page(
        candidates: List[Dict[str, Any]],
        count: int,
        excluded_pages: set[str] | None = None,
    ) -> List[Dict[str, Any]]:
        excluded_pages = excluded_pages or set()
        selected: List[Dict[str, Any]] = []
        for page in _unique_pages(candidates):
            if len(selected) >= count:
                break
            if page in excluded_pages:
                continue
            page_candidates = [p for p in candidates if p["affected_page"] == page]
            selected.append(rng.choice(page_candidates))
        return selected

    if task_id == "easy":
        # Easy episodes should contain one obvious, high-signal problem.
        easy_candidates = [
            p for p in real_problems
            if p["severity"] in ("critical", "high")
            and p["problem_type"] in ("rage_click", "dead_click")
        ]
        selected_problems = [rng.choice(easy_candidates or real_problems)]
        selected_red_herrings: List[Dict[str, Any]] = []
        pages_needed = [selected_problems[0]["affected_page"]]

    elif task_id == "medium":
        # Three pages, one real issue per page, biased toward a severity mix.
        selected_problems = []
        used_pages: set[str] = set()
        for severity in ("critical", "high", "medium"):
            candidates = [
                p for p in real_problems
                if p["severity"] == severity and p["affected_page"] not in used_pages
            ]
            if candidates:
                chosen = rng.choice(candidates)
                selected_problems.append(chosen)
                used_pages.add(chosen["affected_page"])
        while len(selected_problems) < expected_steps:
            remaining = [p for p in real_problems if p["affected_page"] not in used_pages]
            if not remaining:
                break
            chosen = rng.choice(remaining)
            selected_problems.append(chosen)
            used_pages.add(chosen["affected_page"])
        selected_red_herrings = []
        pages_needed = [p["affected_page"] for p in selected_problems]

    else:
        # Hard episodes: six pages containing six real issues and two red herrings.
        # Keep all embedded ground truth on pages the agent actually sees.
        selected_red_herrings = _sample_one_per_page(red_herrings, 2)
        pages_needed = [p["affected_page"] for p in selected_red_herrings]

        problem_pages = [p for p in _unique_pages(real_problems) if p not in pages_needed]
        while len(pages_needed) < expected_steps and problem_pages:
            pages_needed.append(problem_pages.pop())

        real_pool = [p for p in real_problems if p["affected_page"] in pages_needed]
        selected_problems = []
        for page in pages_needed:
            page_candidates = [p for p in real_pool if p["affected_page"] == page]
            if page_candidates:
                selected_problems.append(rng.choice(page_candidates))
        remaining_pool = [p for p in real_pool if p not in selected_problems]
        rng.shuffle(remaining_pool)
        while len(selected_problems) < 6 and remaining_pool:
            selected_problems.append(remaining_pool.pop())

    all_embedded = selected_problems + selected_red_herrings

    while len(pages_needed) < expected_steps:
        available = [p for p in ALL_PAGES if p not in pages_needed]
        if not available:
            break
        pages_needed.append(rng.choice(available))

    pages_needed = pages_needed[:expected_steps]
    all_embedded = [p for p in all_embedded if p["affected_page"] in pages_needed]
    rng.shuffle(pages_needed)

    # Generate data per page
    pages_data: List[PageAnalyticsData] = []
    for page_name in pages_needed:
        problems_on_page = [p for p in all_embedded if p["affected_page"] == page_name]
        page_data = generate_page_data(page_name, problems_on_page, rng)
        pages_data.append(page_data)

    return pages_data, all_embedded
