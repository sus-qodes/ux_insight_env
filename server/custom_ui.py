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
.col-left { padding: 16px !important; }
.col-right { padding: 16px !important; }
.prose, .markdown-text, .md { color: #a1a1aa !important; }
.prose h1, .prose h2, .prose h3 { color: #ffffff !important; }
#playground-examples { margin-top: 16px; }
"""

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
            html = '''<div style="background-color: #064e3b; border: 1px solid #10b981; padding: 12px; border-radius: 6px; color: #a7f3d0; font-family: sans-serif;">
                <b>[SYSTEM OK]</b> Environment Reset Successful. Ready for a new page analysis.
            </div>'''
            return (html, json.dumps(data, indent=2), data)
        except Exception as e:
            html = f'''<div style="background-color: #7f1d1d; border: 1px solid #ef4444; padding: 12px; border-radius: 6px; color: #fecaca; font-family: sans-serif;">
                <b>[ERROR]</b> {e}
            </div>'''
            return (html, "", {})

    def _step_with_action(action_data):
        async def _run():
            try:
                data = await web_manager.step_environment(action_data)
                reward = data.get("reward", 0.0)
                done = data.get("done", False)
                obs = data.get("observation", {})
                
                feedback = obs.get("grader_feedback", "")
                if not feedback and isinstance(obs, dict):
                    feedback = json.dumps(obs, indent=2)[:500] + "..."
                
                reward_color = "#064e3b" if reward > 0.5 else ("#451a03" if reward > 0 else "#7f1d1d")
                reward_border = "#10b981" if reward > 0.5 else ("#f59e0b" if reward > 0 else "#ef4444")
                done_color = "#1e3a8a" if done else "#374151"
                done_border = "#3b82f6" if done else "#6b7280"
                
                html = f'''
                <div style="border-left: 4px solid #8b5cf6; padding: 15px; background-color: #2e1065; margin-bottom: 12px; border-radius: 6px; font-family: sans-serif;">
                  <h4 style="margin-top: 0; color: #ddd6fe; margin-bottom: 8px;">Evaluator Feedback</h4>
                  <p style="color: #f5f3ff; margin: 0; line-height: 1.5;">{feedback}</p>
                </div>
                <div style="display: flex; gap: 12px; font-family: sans-serif;">
                  <div style="background-color: {reward_color}; border: 1px solid {reward_border}; padding: 10px 20px; border-radius: 6px; color: white;">
                    <b>Reward Score:</b> {reward}
                  </div>
                  <div style="background-color: {done_color}; border: 1px solid {done_border}; padding: 10px 20px; border-radius: 6px; color: white;">
                    <b>Episode Done:</b> {done}
                  </div>
                </div>
                '''
                return (html, json.dumps(data, indent=2), data)
            except Exception as e:
                html = f'''<div style="background-color: #7f1d1d; border: 1px solid #ef4444; padding: 12px; border-radius: 6px; color: #fecaca; font-family: sans-serif;">
                    <b>[ERROR]</b> Step execution failed: {e}
                </div>'''
                return (html, "", {})
        return _run

    def get_state_sync():
        try:
            data = web_manager.get_state()
            return (json.dumps(data, indent=2), data)
        except Exception as e:
            return (f"Error: {e}", {})

    with gr.Blocks(title=display_title, theme=ux_theme, css=css) as demo:
        gr.Markdown(f"# {title}")
        
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### Action Form")
                
                default_scenario = [
                    "issue", "Flash Sale banner image", "dead_click", "high",
                    "Make the Flash Sale banner image clickable and link it directly to the active flash sale page so users who tap the promotional banner reach the expected deals instead of waiting after a dead click.",
                    "fix_broken_link", "Expected 20-30% reduction in dead clicks.", 0.9
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

            with gr.Column(scale=1):
                gr.Markdown("### Quick Fill: Magic Assistant")
                gr.Markdown("Don't know the answer for this step? Use the Magic Assistant to peek at the active environment's hidden ground-truth and automatically perfectly populate the form according to the real backend criteria.")
                
                auto_fill_btn = gr.Button("✨ Auto-Fill Correct Answer", variant="secondary")
                
                gr.Markdown("<br/>")
                submit_btn = gr.Button("Submit Finding", variant="primary", size="lg")
                reset_btn = gr.Button("Reset Environment", variant="secondary")

                gr.Markdown("<br/>---<br/>")
                gr.Markdown("### Evaluation Results")
                result_html = gr.HTML("<div style='color: #a1a1aa; padding: 10px;'>Waiting for submission...</div>")

        with gr.Row():
            with gr.Accordion("Advanced: Raw Payload & Docs", open=False):
                gr.Markdown("### Internal Payload Data")
                state_btn = gr.Button("Fetch Current State", variant="secondary")
                with gr.Tabs():
                    with gr.Tab("Preview (Tree)"):
                        raw_json_ui = gr.JSON(label="State Object Preview")
                    with gr.Tab("Raw JSON"):
                        raw_json_code = gr.Code(label="Raw JSON String", language="json", interactive=False)
                
                gr.Markdown("<br/>---<br/>")
                gr.Markdown("### Documentation")
                if quick_start_md:
                    with gr.Accordion("Quick Start", open=False):
                        gr.Markdown(quick_start_md)
                gr.Markdown(readme_content)

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

        auto_fill_btn.click(
            fn=fetch_ground_truth,
            outputs=step_inputs
        )

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
            return await _step_with_action(action_data)()

        # Wire up actions
        demo.load(fn=reset_env, outputs=[result_html, raw_json_code, raw_json_ui])
        reset_btn.click(fn=reset_env, outputs=[result_html, raw_json_code, raw_json_ui])
        submit_btn.click(fn=step_form, inputs=step_inputs, outputs=[result_html, raw_json_code, raw_json_ui])
        state_btn.click(fn=get_state_sync, outputs=[raw_json_code, raw_json_ui])

    return demo
