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
/* ===== CUSTOM UI CSS ===== */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

* { 
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important; 
}

h1, h2, h3, h4, h5, h6, .bold-heading { 
    font-family: 'Outfit', system-ui, sans-serif !important; 
    font-weight: 700 !important; 
    letter-spacing: -0.02em;
}

#page-title {
    text-align: center;
    font-size: 2.5rem;
    margin-bottom: 2rem;
    background: linear-gradient(90deg, #ffffff, #a1a1aa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* ===== MODULAR LAYOUT ===== */
.main-container {
    gap: 24px;
    margin-bottom: 24px;
}

.bento-card {
    background: rgba(17, 17, 19, 0.6) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid #27272a !important;
    border-radius: 16px !important;
    padding: 24px !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
    margin-bottom: 24px;
}

.bento-card-side {
    margin-bottom: 16px;
}

.bento-card:hover {
    border-color: #3f3f46 !important;
    box-shadow: 0 8px 32px rgba(139, 92, 246, 0.1);
}

.bold-heading {
    margin: 0 0 20px 0 !important;
    color: #ffffff !important;
    font-size: 1.25rem !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 1px solid #27272a;
    padding-bottom: 12px;
}

/* ===== INTERACTIVE ELEMENTS ===== */
button, [role="button"] {
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
}

button:hover:not(:disabled) {
    transform: translateY(-2px) !important;
}

button:active:not(:disabled) {
    transform: translateY(0) !important;
}

.primary-btn {
    background: linear-gradient(135deg, #8b5cf6, #6d28d9) !important;
    border: none !important;
    color: white !important;
    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3) !important;
}

.primary-btn:hover {
    box-shadow: 0 6px 16px rgba(139, 92, 246, 0.5) !important;
}

.empty-state {
    padding: 24px;
    color: #a1a1aa;
    text-align: center;
    background: #18181b;
    border-radius: 8px;
    border: 1px dashed #3f3f46;
    font-style: italic;
}

/* ===== OVERRIDES FOR GRADIO INPUTS ===== */
input, textarea, .dropdown {
    background: #18181b !important;
    border-color: #27272a !important;
    transition: border-color 0.2s !important;
}

input:focus, textarea:focus {
    border-color: #8b5cf6 !important;
    box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.2) !important;
}

/* Base Animations */
@keyframes slideInUp {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.feedback-card {
    background: #2e1065;
    border-left: 4px solid #8b5cf6;
    padding: 16px;
    border-radius: 8px;
    margin-bottom: 16px;
    animation: slideInUp 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
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
    }
    return icons.get(icon_type, icons["error"])

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
            total_steps = obs.get("total_steps", 1)

            html = f'''<div style="background-color: #064e3b; border: 1px solid #10b981; padding: 12px; border-radius: 8px; color: #a7f3d0; font-family: sans-serif; font-size: 14px;">
                <b>Ready.</b> {task_id.upper()} task with {total_steps} page(s).
            </div>'''
            return (html, task_id, 0, 0, f"0/{total_steps}", "—", '—')
        except Exception as e:
            return (f"Error: {e}", "easy", 0, 0, "0/0", "—", '—')

    async def reset_with_difficulty(difficulty):
        """Reset with specific difficulty."""
        try:
            data = await web_manager.reset_environment(task_id=difficulty)
            obs = data.get("observation", {})
            total_steps = obs.get("total_steps", 1)

            html = f'''<div style="background-color: #064e3b; border: 1px solid #10b981; padding: 12px; border-radius: 8px; color: #a7f3d0; font-family: sans-serif; font-size: 14px;">
                <b>{difficulty.upper()}</b> — {total_steps} page(s) to analyze.
            </div>'''
            return (html, difficulty, 0, 0, f"0/{total_steps}", "—", '—')
        except Exception as e:
            return (f"Error: {e}", difficulty, 0, 0, "0/0", "—", '—')

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

    def _step_with_action(action_data):
        async def _run():
            try:
                data = await web_manager.step_environment(action_data)
                reward = data.get("reward", 0.0)
                done = data.get("done", False)
                obs = data.get("observation", {})

                feedback = obs.get("grader_feedback", "")
                cumulative = obs.get("cumulative_score", 0.0)
                current_step = obs.get("current_step", 0)
                total_steps = obs.get("total_steps", 1)
                current_page = obs.get("current_page_data", {}).get("page_name", "—")

                # Determine color
                if reward > 0.5:
                    icon = _get_feather_icon("success")
                    bg_color = "#064e3b"
                    border_color = "#10b981"
                    reward_text_color = "#10b981"
                elif reward > 0:
                    icon = _get_feather_icon("warning")
                    bg_color = "#451a03"
                    border_color = "#f59e0b"
                    reward_text_color = "#f59e0b"
                else:
                    icon = _get_feather_icon("error")
                    bg_color = "#7f1d1d"
                    border_color = "#ef4444"
                    reward_text_color = "#ef4444"

                html = f'''
                <div class="feedback-card" style="background-color: {bg_color}; border-color: {border_color};">
                    <div style="display: flex; align-items: flex-start; gap: 12px;">
                        <div>{icon}</div>
                        <div>
                            <h4 style="color: #ddd6fe; margin: 0 0 4px 0; font-size: 13px;">Feedback</h4>
                            <p style="color: #f5f3ff; margin: 0; line-height: 1.6; font-size: 14px;">{feedback}</p>
                        </div>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 12px;">
                    <div style="background: #18181b; border: 1px solid #27272a; padding: 12px; border-radius: 8px;">
                        <div class="metric-label">Reward</div>
                        <div class="metric-value" style="color: {reward_text_color};">{reward:.2f}</div>
                    </div>
                    <div style="background: #18181b; border: 1px solid #27272a; padding: 12px; border-radius: 8px;">
                        <div class="metric-label">Cumulative</div>
                        <div class="metric-value" style="color: #10b981;">{cumulative:.2f}</div>
                    </div>
                </div>
                <div style="padding: 12px; background: {'#1e3a8a' if done else '#374151'}; border: 1px solid {'#3b82f6' if done else '#6b7280'}; border-radius: 8px; color: {'#bfdbfe' if done else '#d1d5db'}; font-size: 13px; text-align: center;">
                    {'Episode Complete' if done else f'Step {current_step}/{total_steps}'}
                </div>
                '''
                return (html, reward, cumulative, f"{current_step}/{total_steps}", current_page, json.dumps({"reward": reward, "done": done}))
            except Exception as e:
                html = f'<div style="background: #7f1d1d; border: 1px solid #ef4444; padding: 12px; border-radius: 8px; color: #fecaca;">Error: {str(e)[:100]}</div>'
                return (html, 0, 0, "—/—", "—", "")
        return _run

    with gr.Blocks(title=display_title, theme=ux_theme, css=css) as demo:
        gr.Markdown(f"# {title}", elem_id="page-title")

        with gr.Row(elem_classes="main-container"):
            # LEFT COLUMN: Form and Actions
            with gr.Column(scale=2, min_width=400, elem_classes="bento-card"):
                gr.Markdown("### 🔍 Find Issue", elem_classes="bold-heading")

                default_scenario = [
                    "no_issue", "N/A", "normal_behavior", "none",
                    "Page metrics within expected ranges.",
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

                gr.Markdown("---")
                with gr.Row():
                    submit_btn = gr.Button("Submit Finding", variant="primary", size="lg", elem_classes="primary-btn")
                    auto_fill_btn = gr.Button("Auto-Fill", variant="secondary")

            # RIGHT COLUMN: Stats & Controls
            with gr.Column(scale=1, min_width=300):
                with gr.Group(elem_classes="bento-card bento-card-side"):
                    gr.Markdown("### ⚙️ Environment Control", elem_classes="bold-heading")
                    with gr.Row():
                        difficulty_easy_btn = gr.Button("Easy", variant="secondary")
                        difficulty_med_btn = gr.Button("Medium", variant="secondary")
                        difficulty_hard_btn = gr.Button("Hard", variant="secondary")
                    reset_btn = gr.Button("Reset Environment", variant="secondary")

                with gr.Group(elem_classes="bento-card bento-card-side"):
                    gr.Markdown("### 📊 Metrics & Status", elem_classes="bold-heading")
                    with gr.Row():
                        step_reward = gr.Number(value=0.0, interactive=False, label="Reward")
                        cumulative = gr.Number(value=0.0, interactive=False, label="Cumulative")
                    with gr.Row():
                        episode_text = gr.Textbox(value="0/0", interactive=False, label="Step")
                        page_name = gr.Textbox(value="—", interactive=False, label="Active Page")
                    status_text = gr.Textbox(value="Ready to start", interactive=False, label="Status")

        # Result display
        with gr.Group(elem_classes="bento-card"):
            gr.Markdown("### 📝 Latest Feedback", elem_classes="bold-heading")
            result_html = gr.HTML('<div class="empty-state">Submit a finding to see results</div>')
            result_json = gr.Code(value="", language="json", interactive=False, visible=False)

        # README full width
        with gr.Group(elem_classes="bento-card"):
            gr.Markdown("## Setup & Documentation", elem_classes="bold-heading")
            gr.Markdown(readme_content)

        # Callbacks
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

            result = await _step_with_action(action_data)()
            return result + ("",)  # Add empty code output

        submit_btn.click(
            fn=step_form,
            inputs=step_inputs,
            outputs=[result_html, step_reward, cumulative, episode_text, page_name, result_json]
        )

        auto_fill_btn.click(fn=fetch_ground_truth, outputs=step_inputs)

        reset_btn.click(
            fn=reset_env,
            outputs=[result_html, gr.State(), step_reward, cumulative, episode_text, page_name, status_text]
        )

        difficulty_easy_btn.click(
            fn=lambda: reset_with_difficulty("easy"),
            outputs=[result_html, gr.State(), step_reward, cumulative, episode_text, page_name, status_text]
        )

        difficulty_med_btn.click(
            fn=lambda: reset_with_difficulty("medium"),
            outputs=[result_html, gr.State(), step_reward, cumulative, episode_text, page_name, status_text]
        )

        difficulty_hard_btn.click(
            fn=lambda: reset_with_difficulty("hard"),
            outputs=[result_html, gr.State(), step_reward, cumulative, episode_text, page_name, status_text]
        )

        demo.load(fn=reset_env, outputs=[result_html, gr.State(), step_reward, cumulative, episode_text, page_name, status_text])

    return demo
