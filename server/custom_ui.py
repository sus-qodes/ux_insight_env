import json
import gradio as gr
from openenv.core.env_server.gradio_ui import _readme_section, get_gradio_display_title, _format_observation

ux_theme = gr.themes.Base(
    primary_hue=gr.themes.colors.zinc,
    secondary_hue=gr.themes.colors.zinc,
    neutral_hue=gr.themes.colors.zinc,
    font=["system-ui", "-apple-system", "Segoe UI", "sans-serif"],
).set(
    body_background_fill="#09090b",
    body_background_fill_dark="#09090b",
    background_fill_primary="#09090b",
    background_fill_primary_dark="#09090b",
    background_fill_secondary="#111113",
    background_fill_secondary_dark="#111113",
    block_background_fill="#111113",
    block_background_fill_dark="#111113",
    block_border_color="#27272a",
    block_border_color_dark="#27272a",
    block_label_text_color="#a1a1aa",
    block_label_text_color_dark="#a1a1aa",
    block_title_text_color="#fff",
    block_title_text_color_dark="#fff",
    border_color_primary="#27272a",
    border_color_primary_dark="#27272a",
    input_background_fill="#18181b",
    input_background_fill_dark="#18181b",
    input_border_color="#27272a",
    input_border_color_dark="#27272a",
    button_primary_background_fill="#fff",
    button_primary_background_fill_dark="#fff",
    button_primary_text_color="#09090b",
    button_primary_text_color_dark="#09090b",
    button_secondary_background_fill="#18181b",
    button_secondary_background_fill_dark="#18181b",
    button_secondary_text_color="#d4d4d8",
    button_secondary_text_color_dark="#d4d4d8",
    button_secondary_border_color="#27272a",
    button_secondary_border_color_dark="#27272a",
    body_text_color="#a1a1aa",
    body_text_color_dark="#a1a1aa",
)

css = """
* { font-family: system-ui, -apple-system, 'Segoe UI', Helvetica, sans-serif !important; }

/* ===== MICRO-ANIMATIONS ===== */
@keyframes slideInUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes slideInDown {
    from { opacity: 0; transform: translateY(-20px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes scaleIn {
    from { transform: scale(0.95); opacity: 0; }
    to { transform: scale(1); opacity: 1; }
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

@keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

@keyframes progressFill {
    from { width: 0%; }
    to { width: var(--progress-width, 100%); }
}

/* ===== INTERACTIVE ELEMENTS ===== */
button, [role="button"] {
    transition: all 200ms cubic-bezier(0.4, 0, 0.2, 1) !important;
}

button:hover:not(:disabled) {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 16px rgba(139, 92, 246, 0.15) !important;
}

button:active:not(:disabled) {
    transform: translateY(0) !important;
}

button:disabled {
    opacity: 0.5 !important;
    cursor: not-allowed !important;
}

/* ===== BENTO GRID ===== */
.bento-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
    animation: slideInUp 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.bento-card {
    background: #111113;
    border: 1px solid #27272a;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
    transition: all 300ms cubic-bezier(0.4, 0, 0.2, 1);
    animation: slideInUp 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.bento-card:hover {
    border-color: #3f3f46;
    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.1);
}

.bento-card h3 {
    margin: 0 0 16px 0;
    color: #ffffff;
    font-size: 14px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.bento-card h4 {
    margin: 0 0 8px 0;
    color: #ddd6fe;
    font-size: 13px;
}

/* Card size variants */
.bento-form { grid-column: span 2; grid-row: span 2; }
.bento-difficulty { grid-column: span 1; grid-row: span 1; }
.bento-metrics { grid-column: span 2; grid-row: span 2; }
.bento-progress { grid-column: span 1; grid-row: span 2; }
.bento-page-status { grid-column: span 1; grid-row: span 1; }
.bento-chart { grid-column: span 2; grid-row: span 2; }

@media (max-width: 1024px) {
    .bento-form, .bento-metrics, .bento-progress, .bento-chart {
        grid-column: span 1 !important;
        grid-row: span auto !important;
    }
}

/* ===== DIFFICULTY SELECTOR ===== */
.difficulty-buttons {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.difficulty-btn {
    padding: 10px 12px;
    border-radius: 8px;
    border: 1.5px solid #27272a;
    background: #18181b;
    color: #a1a1aa;
    font-weight: 500;
    font-size: 13px;
    cursor: pointer;
    transition: all 200ms cubic-bezier(0.4, 0, 0.2, 1);
}

.difficulty-btn:hover:not(.selected) {
    border-color: #8b5cf6;
    background: #1e1e23;
}

.difficulty-btn.selected {
    background: #ffffff !important;
    color: #09090b !important;
    border-color: #ffffff !important;
    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3) !important;
}

/* ===== SCORE METRICS ===== */
.metric-value {
    font-size: 32px;
    font-weight: 700;
    color: #ffffff;
    margin: 8px 0;
}

.metric-label {
    font-size: 12px;
    color: #a1a1aa;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
}

.metric-row {
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid #27272a;
}

.metric-row:last-child {
    border-bottom: none;
    margin-bottom: 0;
    padding-bottom: 0;
}

.metric-color-good { color: #10b981; }
.metric-color-warn { color: #f59e0b; }
.metric-color-bad { color: #ef4444; }

/* ===== PROGRESS BAR ===== */
.progress-container {
    margin-bottom: 20px;
}

.progress-header {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
    font-size: 13px;
    color: #a1a1aa;
}

.progress-bar-container {
    width: 100%;
    height: 8px;
    background: #18181b;
    border-radius: 4px;
    overflow: hidden;
    border: 1px solid #27272a;
}

.progress-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #8b5cf6, #a78bfa);
    animation: progressFill 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    width: var(--progress-width, 0%);
    transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ===== PAGE STATUS ===== */
.page-dots {
    display: flex;
    gap: 6px;
    margin-top: 12px;
}

.page-dot {
    width: 20px;
    height: 20px;
    border-radius: 3px;
    background: #27272a;
    transition: all 200ms cubic-bezier(0.4, 0, 0.2, 1);
}

.page-dot.current {
    background: #8b5cf6;
    animation: pulse 1.5s ease-in-out infinite;
}

.page-dot.completed {
    background: #10b981;
}

/* ===== FEEDBACK CARDS ===== */
.feedback-card {
    background: #2e1065;
    border-left: 4px solid #8b5cf6;
    padding: 16px;
    border-radius: 8px;
    margin-bottom: 12px;
    animation: slideInUp 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.feedback-icon {
    display: inline-block;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    margin-right: 12px;
    animation: scaleIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

/* ===== CHART ===== */
.chart-container {
    width: 100%;
    height: 250px;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    background: #0f0f12;
    border-radius: 8px;
    padding: 20px;
    box-sizing: border-box;
}

svg {
    filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.2));
}

/* ===== UTILITY ===== */
.text-muted { color: #71717a; }
.text-secondary { color: #a1a1aa; }
.text-primary { color: #ffffff; }
.gap-4 { gap: 16px !important; }
.gap-3 { gap: 12px !important; }
.mb-2 { margin-bottom: 8px !important; }
.mb-4 { margin-bottom: 16px !important; }
"""

def _get_feather_icon(icon_type):
    """Return Feather icon SVG for display."""
    icons = {
        "success": '''<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2.5">
            <polyline points="20 6 9 17 4 12"></polyline>
        </svg>''',
        "warning": '''<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.5">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3.05h16.94a2 2 0 0 0 1.71-3.05L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
        </svg>''',
        "error": '''<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="15" y1="9" x2="9" y2="15"></line>
            <line x1="9" y1="9" x2="15" y2="15"></line>
        </svg>''',
        "info": '''<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#3b82f6" stroke-width="2.5">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="16" x2="12" y2="12"></line>
            <line x1="12" y1="8" x2="12.01" y2="8"></line>
        </svg>'''
    }
    return icons.get(icon_type, icons["info"])

def _build_cumulative_trend_svg(episode_rewards, current_step, total_steps):
    """Build SVG line chart for cumulative trend (real data only)."""
    if not episode_rewards:
        return '''<svg viewBox="0 0 400 200" xmlns="http://www.w3.org/2000/svg">
            <rect width="400" height="200" fill="#0f0f12"/>
            <text x="200" y="100" text-anchor="middle" fill="#71717a" font-size="14">
                No data yet. Submit a finding to see trends.
            </text>
        </svg>'''

    # Prepare data
    scores = [sum(episode_rewards[:i+1]) / len(episode_rewards[:i+1]) for i in range(len(episode_rewards))]
    max_score = max(scores) if scores else 1.0
    min_score = min(scores) if scores else 0.0
    score_range = max(max_score - min_score, 0.1)

    # SVG dimensions
    width, height = 400, 200
    padding = 30
    plot_width = width - 2 * padding
    plot_height = height - 2 * padding

    # Calculate points
    points = []
    for i, score in enumerate(scores):
        x = padding + (i / max(len(scores) - 1, 1)) * plot_width
        y_norm = (score - min_score) / score_range
        y = padding + plot_height * (1 - y_norm)
        points.append((x, y, score))

    # Build SVG
    svg_lines = [f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">']
    svg_lines.append(f'<rect width="{width}" height="{height}" fill="#0f0f12"/>')

    # Grid lines
    for i in range(5):
        y = padding + (i / 4) * plot_height
        svg_lines.append(f'<line x1="{padding}" y1="{y}" x2="{width-padding}" y2="{y}" stroke="#27272a" stroke-width="0.5" opacity="0.5"/>')

    # Y-axis labels
    for i in range(5):
        val = min_score + (i / 4) * score_range
        y = padding + (4 - i) / 4 * plot_height
        svg_lines.append(f'<text x="{padding-5}" y="{y+4}" text-anchor="end" fill="#71717a" font-size="11">{val:.2f}</text>')

    # Line path
    if len(points) > 1:
        path_data = f"M {points[0][0]} {points[0][1]} "
        for i in range(1, len(points)):
            path_data += f"L {points[i][0]} {points[i][1]} "
        svg_lines.append(f'<path d="{path_data}" stroke="url(#grad)" stroke-width="2.5" fill="none" stroke-linecap="round"/>')

        # Gradient
        svg_lines.append('''<defs>
            <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" style="stop-color:#8b5cf6;stop-opacity:1" />
                <stop offset="100%" style="stop-color:#10b981;stop-opacity:1" />
            </linearGradient>
        </defs>''')

    # Data points
    for i, (x, y, score) in enumerate(points):
        svg_lines.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#a78bfa" stroke="#8b5cf6" stroke-width="2"/>')
        if i == len(points) - 1:
            svg_lines.append(f'<text x="{x}" y="{y-12}" text-anchor="middle" fill="#10b981" font-size="12" font-weight="bold">{score:.2f}</text>')

    # X-axis labels
    for i, (x, y, score) in enumerate(points):
        svg_lines.append(f'<text x="{x}" y="{height-10}" text-anchor="middle" fill="#71717a" font-size="11">S{i+1}</text>')

    # Axes
    svg_lines.append(f'<line x1="{padding}" y1="{padding}" x2="{padding}" y2="{height-padding}" stroke="#27272a" stroke-width="1"/>')
    svg_lines.append(f'<line x1="{padding}" y1="{height-padding}" x2="{width-padding}" y2="{height-padding}" stroke="#27272a" stroke-width="1"/>')

    svg_lines.append('</svg>')
    return '\n'.join(svg_lines)

def custom_gradio_builder(
    web_manager,
    action_fields,
    metadata,
    is_chat_env,
    title="UX Insight Playground",
    quick_start_md=None,
):
    readme_content = _readme_section(metadata)
    if readme_content.startswith('---'):
        parts = readme_content.split('---', 2)
        if len(parts) >= 3:
            readme_content = parts[2].strip()

    display_title = title

    async def reset_env():
        try:
            data = await web_manager.reset_environment()
            obs = data.get("observation", {})
            task_id = obs.get("task_id", "easy")
            html = f'''<div style="background-color: #064e3b; border: 1px solid #10b981; padding: 12px; border-radius: 8px; color: #a7f3d0; font-family: sans-serif; font-size: 14px;">
                <b>Environment Reset</b>. Ready to analyze <b>{task_id.upper()}</b> task.
            </div>'''
            return (html, task_id)
        except Exception as e:
            html = f'''<div style="background-color: #7f1d1d; border: 1px solid #ef4444; padding: 12px; border-radius: 8px; color: #fecaca; font-family: sans-serif;">
                <b>Error:</b> {e}
            </div>'''
            return (html, "easy")

    async def set_difficulty(difficulty):
        """Reset environment with selected difficulty."""
        data = await web_manager.reset_environment(task_id=difficulty)
        html = f'''<div style="background-color: #064e3b; border: 1px solid #10b981; padding: 12px; border-radius: 8px; color: #a7f3d0; font-family: sans-serif; font-size: 14px;">
            <b>Difficulty set to {difficulty.upper()}</b> - analyzing {1 if difficulty=='easy' else 3 if difficulty=='medium' else 6} page(s).
        </div>'''
        return [html, [int(d == difficulty) for d in ["easy", "medium", "hard"]]]

    def _step_with_action(action_data):
        async def _run():
            try:
                data = await web_manager.step_environment(action_data)
                reward = data.get("reward", 0.0)
                done = data.get("done", False)
                obs = data.get("observation", {})

                feedback = obs.get("grader_feedback", "")
                cumulative = obs.get("cumulative_score", 0.0)
                episode_rewards = obs.get("episode_rewards", [])
                current_step = obs.get("current_step", 0)
                total_steps = obs.get("total_steps", 1)

                # Determine icon and color
                if reward > 0.5:
                    icon = _get_feather_icon("success")
                    bg_color = "#064e3b"
                    border_color = "#10b981"
                    reward_color = "metric-color-good"
                elif reward > 0:
                    icon = _get_feather_icon("warning")
                    bg_color = "#451a03"
                    border_color = "#f59e0b"
                    reward_color = "metric-color-warn"
                else:
                    icon = _get_feather_icon("error")
                    bg_color = "#7f1d1d"
                    border_color = "#ef4444"
                    reward_color = "metric-color-bad"

                html = f'''
                <div class="feedback-card" style="background-color: {bg_color}; border-color: {border_color};">
                    <div style="display: flex; align-items: flex-start;">
                        <div class="feedback-icon">{icon}</div>
                        <div style="flex: 1;">
                            <h4 style="color: #ddd6fe; margin: 0 0 4px 0;">Evaluator Feedback</h4>
                            <p style="color: #f5f3ff; margin: 0; line-height: 1.6; font-size: 14px;">{feedback}</p>
                        </div>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                    <div style="background: #18181b; border: 1px solid #27272a; padding: 12px; border-radius: 8px;">
                        <div class="metric-label">Step Reward</div>
                        <div class="metric-value {reward_color}">{reward:.2f}</div>
                    </div>
                    <div style="background: #18181b; border: 1px solid #27272a; padding: 12px; border-radius: 8px;">
                        <div class="metric-label">Cumulative</div>
                        <div class="metric-value metric-color-good">{cumulative:.2f}</div>
                    </div>
                </div>
                <div style="margin-top: 12px; padding: 12px; background: {'#1e3a8a' if done else '#374151'}; border: 1px solid {'#3b82f6' if done else '#6b7280'}; border-radius: 8px; color: {'#bfdbfe' if done else '#d1d5db'}; font-size: 13px; text-align: center;">
                    Episode {'Complete' if done else f'In Progress (Step {current_step}/{total_steps})'}
                </div>
                '''
                return (html, json.dumps({"reward": reward, "cumulative": cumulative, "done": done}, indent=2))
            except Exception as e:
                html = f'''<div style="background-color: #7f1d1d; border: 1px solid #ef4444; padding: 12px; border-radius: 8px; color: #fecaca; font-family: sans-serif;">
                    <b>Error:</b> {str(e)[:200]}
                </div>'''
                return (html, "")
        return _run

    def fetch_ground_truth():
        try:
            env = web_manager.env
            current_idx = env._current_step
            if current_idx >= len(env._pages_data):
                return ["no_issue", "N/A", "normal_behavior", "none", "Episode complete.", "no_fix_needed", "N/A", 0.9]

            current_page = env._pages_data[current_idx].page_name
            problems = [p for p in env._embedded_problems if p["affected_page"] == current_page and not p.get("red_herring")]

            if problems:
                p = problems[0]
                return [
                    "issue",
                    p.get("affected_element", "Element"),
                    p.get("problem_type", "rage_click"),
                    p.get("severity", "medium"),
                    "An issue was dynamically generated based on simulated metrics.",
                    p.get("expected_fix_category", "redesign_element"),
                    "Expected positive impact on UX.",
                    0.95
                ]
            else:
                return ["no_issue", "N/A", "normal_behavior", "none", "All metrics for this page are within expected engagement levels. No fix required.", "no_fix_needed", "N/A", 0.95]
        except Exception as e:
            return ["issue", f"Error: {e}", "", "", "", "", "", 0.0]

    with gr.Blocks(title=display_title, theme=ux_theme, css=css) as demo:
        # ===== TOP NAVIGATION TABS =====
        with gr.Tabs(elem_classes="top-tabs"):
            with gr.Tab(label="Analyzer", elem_id="analyzer-tab"):
                # Bento grid container
                with gr.Group(elem_classes="bento-grid"):
                    # Card 1: Action Form
                    with gr.Group(elem_classes="bento-card bento-form"):
                        gr.Markdown("### Find the Issue", elem_classes="")

                        default_scenario = [
                            "no_issue", "N/A", "normal_behavior", "none",
                            "Page metrics are within expected ranges. No issue detected.",
                            "no_fix_needed", "N/A", 0.5
                        ]

                        step_inputs = []
                        for i, field in enumerate(action_fields):
                            name = field["name"]
                            field_type = field.get("type", "text")
                            label = name.replace("_", " ").title()
                            placeholder = field.get("placeholder", "")

                            default_val = default_scenario[i] if i < len(default_scenario) else None

                            if field_type == "checkbox":
                                inp = gr.Checkbox(label=label, value=bool(default_val) if default_val is None else default_val)
                            elif field_type == "number":
                                inp = gr.Number(label=label, value=default_val)
                            elif field_type == "select":
                                choices = field.get("choices") or []
                                inp = gr.Dropdown(choices=choices, label=label, allow_custom_value=False, value=default_val)
                            elif field_type in ("textarea", "tensor"):
                                inp = gr.Textbox(label=label, placeholder=placeholder, lines=3, value=default_val)
                            else:
                                inp = gr.Textbox(label=label, placeholder=placeholder, value=default_val)
                            step_inputs.append(inp)

                    # Card 2: Difficulty Selector
                    with gr.Group(elem_classes="bento-card bento-difficulty"):
                        gr.Markdown("### Pick Difficulty", elem_classes="")

                        with gr.Group(elem_classes="difficulty-buttons"):
                            difficulty_easy = gr.Button("Easy\n1 page", elem_classes="difficulty-btn", variant="secondary")
                            difficulty_med = gr.Button("Medium\n3 pages", elem_classes="difficulty-btn", variant="secondary")
                            difficulty_hard = gr.Button("Hard\n6 pages", elem_classes="difficulty-btn", variant="secondary")

                    # Card 3: Score Metrics
                    with gr.Group(elem_classes="bento-card bento-metrics"):
                        gr.Markdown("### Metrics", elem_classes="")

                        current_reward = gr.Number(value=0.0, interactive=False, label="Current Step Reward")
                        cumulative_score = gr.Number(value=0.0, interactive=False, label="Cumulative Score")
                        episode_status = gr.Textbox(value="Not Started", interactive=False, label="Episode Status")

                    # Card 4: Progress
                    with gr.Group(elem_classes="bento-card bento-progress"):
                        gr.Markdown("### Progress", elem_classes="")

                        progress_text = gr.Textbox(value="Step 0 of 0", interactive=False, label="", show_label=False)
                        progress_bar = gr.Slider(value=0, minimum=0, maximum=100, interactive=False, show_label=False)

                    # Card 5: Current Page
                    with gr.Group(elem_classes="bento-card bento-page-status"):
                        gr.Markdown("### Page", elem_classes="")

                        page_name = gr.Textbox(value="—", interactive=False, label="", show_label=False)

                    # Card 6: Cumulative Trend Chart
                    with gr.Group(elem_classes="bento-card bento-chart"):
                        gr.Markdown("### Trend", elem_classes="")

                        trend_chart = gr.HTML(value=_build_cumulative_trend_svg([], 0, 1))

                # Action buttons
                with gr.Group():
                    with gr.Row():
                        submit_btn = gr.Button("Submit Finding", variant="primary", size="lg")
                        auto_fill_btn = gr.Button("Auto-Fill Correct", variant="secondary")
                        reset_btn = gr.Button("Reset", variant="secondary")

                # Result display
                with gr.Group():
                    result_html = gr.HTML("<div style='color: #a1a1aa; padding: 16px; text-align: center;'>Submit a finding to see results</div>")
                    result_json = gr.Code(language="json", interactive=False)

                # README at bottom
                with gr.Group():
                    gr.Markdown("---")
                    gr.Markdown("## Setup & Documentation")
                    gr.Markdown(readme_content)

            # Tab 2: Guide
            with gr.Tab(label="Guide", elem_id="guide-tab"):
                gr.Markdown("""
## Getting Started with UX Insight Analyst

### 1. Select Difficulty
Choose a difficulty level in the Analyzer tab:
- **Easy**: Analyze 1 page
- **Medium**: Analyze 3 pages
- **Hard**: Analyze 6 pages

### 2. Analyze the Page
Look at the current page metrics and identify issues:
- Use **Auto-Fill** to peek at the ground truth for reference
- Or manually fill the form with your analysis
- Include specific, actionable recommendations

### 3. Submit & Receive Feedback
Get immediate scoring feedback:
- Step Reward: Score for this analysis
- Cumulative Score: Running average across episode
- Episode Status: Progress through all pages

### 4. Complete the Episode
Analyze all pages to complete the episode.
The cumulative trend chart shows your score progression.

### Tips
- Be specific in element identification
- Provide detailed recommendations
- Consider the severity of issues
- Look for real UX patterns in the data
                """)

            # Tab 3: API Docs
            with gr.Tab(label="API Docs", elem_id="api-docs-tab"):
                gr.Markdown("""
## API Reference

### Reset Endpoint
```bash
POST /reset
Content-Type: application/json

{
  "task_id": "easy",  # or "medium", "hard"
  "seed": 42          # Optional, for reproducibility
}
```

Response:
```json
{
  "observation": {
    "task_id": "easy",
    "current_step": 1,
    "total_steps": 1,
    "pages_to_analyze": ["homepage"],
    "current_page_data": {...}
  }
}
```

### Step Endpoint
```bash
POST /step
Content-Type: application/json

{
  "finding_type": "issue",
  "affected_element": "Add to Cart button",
  "issue_category": "rage_click",
  "severity": "critical",
  "recommendation": "Add loading state...",
  "fix_category": "add_loading_state",
  "impact_estimate": "Reduce cart abandonment...",
  "confidence": 0.85
}
```

Response:
```json
{
  "reward": 0.75,
  "done": false,
  "observation": {
    "cumulative_score": 0.75,
    "grader_feedback": "Good analysis..."
  }
}
```
                """)

            # Tab 4: Examples
            with gr.Tab(label="Examples", elem_id="examples-tab"):
                gr.Markdown("""
## Example Submissions

### Example 1: Good Analysis (Easy)
Identifying and fixing a rage click issue:

```json
{
  "finding_type": "issue",
  "affected_element": "Add to Cart Button",
  "issue_category": "rage_click",
  "severity": "critical",
  "recommendation": "Add visual loading feedback and disable button while processing to prevent multiple submissions",
  "fix_category": "add_loading_state",
  "impact_estimate": "Reduce cart abandonment by 15-20%",
  "confidence": 0.92
}
```

**Expected Score**: 0.75 - 0.85

### Example 2: Red Herring Detection (Medium)
Correctly identifying normal behavior as non-issue:

```json
{
  "finding_type": "no_issue",
  "affected_element": "N/A",
  "issue_category": "normal_behavior",
  "severity": "none",
  "recommendation": "High exit rate on order confirmation is expected after successful purchase",
  "fix_category": "no_fix_needed",
  "impact_estimate": "N/A",
  "confidence": 0.88
}
```

**Expected Score**: 0.80 - 0.95

### Example 3: Partial Analysis (Hard)
Finding some correct elements but missing depth:

```json
{
  "finding_type": "issue",
  "affected_element": "Checkout Form",
  "issue_category": "dead_click",
  "severity": "high",
  "recommendation": "Fix form validation issues",
  "fix_category": "improve_copy",
  "impact_estimate": "Better user experience",
  "confidence": 0.65
}
```

**Expected Score**: 0.45 - 0.60
                """)

        # ===== CALLBACKS =====
        async def step_form(*values):
            action_data = {}
            for i, field in enumerate(action_fields):
                if i >= len(values): break
                name = field["name"]
                val = values[i]
                if field.get("type") == "checkbox":
                    action_data[name] = bool(val)
                elif val is not None and val != "":
                    action_data[name] = val

            html, json_out = await _step_with_action(action_data)()

            # Update metrics display
            try:
                data = await web_manager.step_environment(action_data)
                obs = data.get("observation", {})
                reward = data.get("reward", 0.0)
                cumulative = obs.get("cumulative_score", 0.0)
                done = data.get("done", False)
                current_step = obs.get("current_step", 0)
                total_steps = obs.get("total_steps", 1)
                episode_rewards = obs.get("episode_rewards", [])
                current_page = obs.get("current_page_data", {}).get("page_name", "—")

                # Update cards
                progress_pct = int((current_step / total_steps) * 100) if total_steps > 0 else 0
                trend_svg = _build_cumulative_trend_svg(episode_rewards, current_step, total_steps)

                return (
                    html, json_out,
                    reward, cumulative,
                    f"{'Complete' if done else f'Step {current_step}/{total_steps}'}",
                    f"Step {current_step} of {total_steps}", progress_pct,
                    current_page,
                    trend_svg
                )
            except:
                return (html, json_out, 0, 0, "Error", "—", 0, "—", _build_cumulative_trend_svg([], 0, 1))

        # Wire up buttons
        submit_btn.click(
            fn=step_form,
            inputs=step_inputs,
            outputs=[result_html, result_json, current_reward, cumulative_score, episode_status, progress_text, progress_bar, page_name, trend_chart]
        )

        def auto_fill_and_submit(*_):
            values = fetch_ground_truth()
            return values + ["auto_fill"]

        auto_fill_btn.click(
            fn=fetch_ground_truth,
            outputs=step_inputs
        )

        async def on_reset():
            html, task = await reset_env()
            return (html, task, 0, 0, "Step 0 of 0", 0, "—", _build_cumulative_trend_svg([], 0, 1))

        reset_btn.click(
            fn=on_reset,
            outputs=[result_html, gr.State(), progress_text, progress_bar, page_name, trend_chart]
        )

        async def set_difficulty_easy():
            return await set_difficulty("easy")

        async def set_difficulty_medium():
            return await set_difficulty("medium")

        async def set_difficulty_hard():
            return await set_difficulty("hard")

        difficulty_easy.click(fn=set_difficulty_easy, outputs=[result_html, gr.State()])
        difficulty_med.click(fn=set_difficulty_medium, outputs=[result_html, gr.State()])
        difficulty_hard.click(fn=set_difficulty_hard, outputs=[result_html, gr.State()])

        # Initial load
        demo.load(fn=reset_env, outputs=[result_html, gr.State()])

    return demo
