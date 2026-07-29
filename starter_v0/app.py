import streamlit as st
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from env_loader import load_lab_env
from providers import make_provider
from providers.base import ToolCall
from tools import TOOL_FUNCTIONS, load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version
from chat import safe_slug, now_iso, trim_history, execute_tool_call, assistant_tool_message, tool_results_message, write_transcript, run_model_tool_loop

# Page configuration with premium layout
st.set_page_config(
    page_title="AI Research Agent Studio",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment
ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
load_lab_env(ROOT)

# Professional & Sleek Custom CSS injection
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

    * {
        font-family: 'IBM Plex Sans', sans-serif;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Nền giấy sáng, hoạ tiết chấm mờ kiểu giấy kẻ ô phòng lab */
    .stApp {
        background-color: #F6F7F5;
        background-image: radial-gradient(#D9DDD9 1px, transparent 1px);
        background-size: 22px 22px;
        color: #161B22;
    }

    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E3E6E1;
    }

    /* Header — thẻ tiêu đề kiểu label mẫu vật trong phòng thí nghiệm */
    .studio-header {
        background: #FFFFFF;
        padding: 24px 32px;
        border-radius: 12px;
        border: 1px solid #E3E6E1;
        border-left: 5px solid #0F766E;
        margin-bottom: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 1px 3px rgba(22, 27, 34, 0.06);
    }
    .studio-title-group h1 {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #161B22;
        margin: 0;
        letter-spacing: -0.02em;
    }
    .studio-title-group p {
        font-size: 0.9rem;
        color: #5B6472;
        margin: 4px 0 0 0;
    }

    .metric-badge {
        background: #F1F4F1;
        border: 1px solid #D9DDD9;
        border-radius: 6px;
        padding: 6px 12px;
        font-size: 0.82rem;
        font-weight: 600;
        color: #14532D;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-family: 'IBM Plex Mono', monospace;
    }

    /* Chat bubbles */
    .chat-bubble-user {
        background-color: #0F766E;
        color: white;
        padding: 14px 18px;
        border-radius: 14px 14px 2px 14px;
        margin: 12px 0 12px auto;
        max-width: 75%;
        font-size: 0.95rem;
        line-height: 1.55;
        box-shadow: 0 2px 6px rgba(15, 118, 110, 0.25);
    }
    .chat-bubble-agent {
        background-color: #FFFFFF;
        color: #161B22;
        padding: 16px 20px;
        border-radius: 14px 14px 14px 2px;
        margin: 12px auto 12px 0;
        max-width: 85%;
        font-size: 0.95rem;
        line-height: 1.55;
        border: 1px solid #E3E6E1;
        box-shadow: 0 1px 4px rgba(22, 27, 34, 0.05);
    }

    /* Bảng điều khiển tool trace — kiểu "dải mẫu vật" phòng lab */
    .dev-console-header {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.8rem;
        color: #5B6472;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 16px;
        margin-bottom: 10px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .timeline-item {
        border-left: 2px dashed #C7CCC6;
        margin-left: 8px;
        padding-left: 20px;
        position: relative;
        padding-bottom: 16px;
    }
    .timeline-item::before {
        content: '';
        position: absolute;
        left: -6px;
        top: 4px;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: #0F766E;
        border: 2px solid #F6F7F5;
    }
    .timeline-item.error::before {
        background-color: #DC2626;
    }
    .tool-box {
        background: #FFFFFF;
        border: 1px solid #E3E6E1;
        border-radius: 10px;
        padding: 14px 18px;
    }
    .tool-meta {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.83rem;
        color: #0F766E;
        font-weight: 600;
        display: flex;
        justify-content: space-between;
    }
    .tool-meta-error {
        color: #DC2626 !important;
    }

    pre, code {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.83rem !important;
        background-color: #F1F4F1 !important;
        border-radius: 6px !important;
        border: 1px solid #E3E6E1 !important;
        color: #14532D !important;
    }
</style>
""", unsafe_allow_html=True)
# ----------------- SIDEBAR CONFIGURATIONS -----------------
st.sidebar.markdown("<div style='padding: 10px 0;'><h2 style='color:#6366F1; font-weight:800; margin:0;'>AGENT STUDIO</h2><p style='color:#6B7280; font-size:0.8rem; margin:0;'>Version Control & Hyperparameters</p></div>", unsafe_allow_html=True)

st.sidebar.divider()

# Version Section
st.sidebar.markdown("### 🏷️ Target Version")
version_label = st.sidebar.text_input("Artifact Version Label", value="v0", help="Label for version log mapping.")

# Provider Section
st.sidebar.markdown("### 🔌 LLM Provider")
provider_name = st.sidebar.selectbox(
    "Provider",
    ["openrouter", "openai", "anthropic", "gemini"],
    index=0
)

# Selectable models depending on provider
model_options = {
    "openrouter": [None, "google/gemini-2.5-flash", "meta-llama/llama-3.3-70b-instruct"],
    "openai": [None, "gpt-4o-mini", "gpt-4o"],
    "anthropic": [None, "claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"],
    "gemini": [None, "gemini-2.5-flash", "gemini-2.5-pro"]
}
selected_model = st.sidebar.selectbox("Model Overwrite", model_options[provider_name], format_func=lambda x: "Default model" if x is None else x)

# Hyperparams Section
st.sidebar.markdown("### ⚙️ Parameters")
max_tool_rounds = st.sidebar.slider("Max Tool Rounds", min_value=1, max_value=8, value=4)
history_window = st.sidebar.slider("History Window (Turns)", min_value=1, max_value=10, value=5)

st.sidebar.divider()

# Active Config Details
st.sidebar.caption(f"📂 **System Prompt:** `artifacts/system_prompt.md`")
st.sidebar.caption(f"🔧 **Tools Schema:** `artifacts/tools.yaml`")

# ----------------- SESSION MANAGEMENT -----------------
if "history" not in st.session_state:
    st.session_state.history = []
if "transcript" not in st.session_state:
    st.session_state.transcript = None
if "transcript_path" not in st.session_state:
    st.session_state.transcript_path = None
if "turn_index" not in st.session_state:
    st.session_state.turn_index = 0

def reset_session():
    st.session_state.history = []
    st.session_state.turn_index = 0
    
    system_prompt = system_prompt_path.read_text(encoding="utf-8")
    tool_declarations = load_tool_declarations(tools_path)
    openai_tools = to_openai_tools(tool_declarations)
    provider = make_provider(provider_name)
    real_model = selected_model or getattr(provider, "default_model", None)
    artifact_version = build_artifact_version(version_label, system_prompt_path, tools_path)
    
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = "_".join([
        safe_slug(version_label),
        safe_slug(provider_name),
        timestamp,
    ])
    st.session_state.transcript_path = ROOT / "transcripts" / f"{transcript_id}.transcript.json"
    st.session_state.transcript = {
        "transcript_id": transcript_id,
        **artifact_version_dict(artifact_version),
        "provider": provider_name,
        "model": real_model,
        "system_prompt": str(system_prompt_path),
        "tools": str(tools_path),
        "history_window": history_window,
        "max_tool_rounds": max_tool_rounds,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }
    st.toast("New session initiated successfully!", icon="✨")

st.sidebar.markdown("<br>", unsafe_allow_html=True)
st.sidebar.button("🔄 Reset Chat Session", on_click=reset_session, use_container_width=True)

# ----------------- MAIN APP HEADER -----------------
system_prompt_path = ARTIFACTS_DIR / "system_prompt.md"
tools_path = ARTIFACTS_DIR / "tools.yaml"

if st.session_state.transcript is None:
    reset_session()

# Render Modern Header Banner
model_display = st.session_state.transcript.get("model") or "Default"
if "/" in model_display:
    model_display = model_display.split("/")[-1]

st.markdown(f"""
<div class='studio-header'>
    <div class='studio-title-group'>
        <h1>Research Agent Studio</h1>
        <p>Evidence-driven reasoning & dynamic tool execution logs</p>
    </div>
    <div style='display: flex; gap: 12px;'>
        <div class='metric-badge'>🏷️ Version: {version_label}</div>
        <div class='metric-badge'>🧠 Model: {model_display}</div>
        <div class='metric-badge'>🔌 Provider: {provider_name.upper()}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ----------------- CHAT HISTORY WINDOW -----------------
chat_container = st.container()

with chat_container:
    for msg in st.session_state.history:
        if msg["role"] == "user":
            st.markdown(f"<div class='chat-bubble-user'>{msg['content']}</div>", unsafe_allow_html=True)
        elif msg["role"] == "assistant":
            # Display Agent Text
            st.markdown(f"<div class='chat-bubble-agent'>{msg['content']}</div>", unsafe_allow_html=True)
            
            # Display Tool Traces inside Chat Timeline
            if "tool_events" in msg and msg["tool_events"]:
                st.markdown("<div class='dev-console-header'>🛠️ Developer Execution Console</div>", unsafe_allow_html=True)
                for ev in msg["tool_events"]:
                    res = ev.get('result', {})
                    is_error = 'error' in res and res['error'] is not None
                    error_class = "error" if is_error else ""
                    
                    st.markdown(f"""
                    <div class='timeline-item {error_class}'>
                        <div class='tool-box'>
                            <div class='tool-meta {"tool-meta-error" if is_error else ""}'>
                                <span>▶ TOOL CALL: {ev['tool']}()</span>
                                <span>STATUS: {"ERROR ❌" if is_error else "SUCCESS ✅"}</span>
                            </div>
                            <div style='margin-top: 8px;'>
                                <strong style='font-size: 0.8rem; color: #9CA3AF;'>Arguments:</strong>
                                <pre><code>{json.dumps(ev['args'], indent=2, ensure_ascii=False)}</code></pre>
                            </div>
                            <div style='margin-top: 8px;'>
                                <strong style='font-size: 0.8rem; color: #9CA3AF;'>Output Result:</strong>
                                <pre><code>{json.dumps(res, indent=2, ensure_ascii=False)}</code></pre>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

# ----------------- CHAT INPUT FIELD -----------------
user_input = st.chat_input("Hỏi AI Research Agent hoặc yêu cầu tìm kiếm...")

if user_input:
    # Render user input bubble immediately
    st.markdown(f"<div class='chat-bubble-user'>{user_input}</div>", unsafe_allow_html=True)
    st.session_state.history.append({"role": "user", "content": user_input})
    
    st.session_state.turn_index += 1
    turn_record = {
        "turn_index": st.session_state.turn_index,
        "started_at": now_iso(),
        "user": user_input,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }
    
    # Load settings
    system_prompt = system_prompt_path.read_text(encoding="utf-8")
    tool_declarations = load_tool_declarations(tools_path)
    openai_tools = to_openai_tools(tool_declarations)
    provider = make_provider(provider_name)
    
    # Assemble past history context
    messages = [
        {"role": "system", "content": system_prompt},
        *trim_history(st.session_state.history[:-1], history_window),
        {"role": "user", "content": user_input},
    ]
    
    # Run Agent Loop with live UI status container
    with st.chat_message("assistant"):
        status_placeholder = st.status("Thinking & calling tools...", expanded=True)
        try:
            result = run_model_tool_loop(
                provider=provider,
                messages=messages,
                tools=openai_tools,
                model=selected_model,
                max_tool_rounds=max_tool_rounds,
            )
            
            turn_record.update(result)
            assistant_text = result["assistant_text"]
            
            status_placeholder.update(label="Reasoning complete", state="complete", expanded=False)
            
            # Print final response
            st.markdown(f"<div class='chat-bubble-agent'>{assistant_text}</div>", unsafe_allow_html=True)
            
            # Print live tool traces beautifully
            tool_events = result.get("tool_events", [])
            if tool_events:
                st.markdown("<div class='dev-console-header'>🛠️ Developer Execution Console</div>", unsafe_allow_html=True)
                for ev in tool_events:
                    res = ev.get('result', {})
                    is_error = 'error' in res and res['error'] is not None
                    error_class = "error" if is_error else ""
                    
                    st.markdown(f"""
                    <div class='timeline-item {error_class}'>
                        <div class='tool-box'>
                            <div class='tool-meta {"tool-meta-error" if is_error else ""}'>
                                <span>▶ TOOL CALL: {ev['tool']}()</span>
                                <span>STATUS: {"ERROR ❌" if is_error else "SUCCESS ✅"}</span>
                            </div>
                            <div style='margin-top: 8px;'>
                                <strong style='font-size: 0.8rem; color: #9CA3AF;'>Arguments:</strong>
                                <pre><code>{json.dumps(ev['args'], indent=2, ensure_ascii=False)}</code></pre>
                            </div>
                            <div style='margin-top: 8px;'>
                                <strong style='font-size: 0.8rem; color: #9CA3AF;'>Output Result:</strong>
                                <pre><code>{json.dumps(res, indent=2, ensure_ascii=False)}</code></pre>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Save to state
            st.session_state.history.append({
                "role": "assistant",
                "content": assistant_text,
                "tool_events": tool_events
            })
            
        except Exception as exc:
            status_placeholder.update(label="Provider Error", state="error")
            error_msg = f"{type(exc).__name__}: {str(exc)}"
            st.error(error_msg)
            turn_record.update({
                "status": "provider_error",
                "error": error_msg,
            })
            st.session_state.history.append({"role": "assistant", "content": f"⚠️ Error: {error_msg}"})
            
        turn_record["ended_at"] = now_iso()
        st.session_state.transcript["turns"].append(turn_record)
        write_transcript(st.session_state.transcript_path, st.session_state.transcript)
        st.toast("Transcript saved to local disk!", icon="💾")
        st.rerun()
