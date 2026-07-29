import streamlit as st
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from env_loader import load_lab_env
from providers import make_provider
from providers.base import ToolCall
from tools import TOOL_FUNCTIONS, load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version
from chat import safe_slug, now_iso, trim_history, execute_tool_call, assistant_tool_message, tool_results_message, write_transcript, run_model_tool_loop

# Page configuration
st.set_page_config(
    page_title="AI Research Agent Studio",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
RUNS_DIR = ROOT / "runs"
load_lab_env(ROOT)

# ----------------- STYLE -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

    * { font-family: 'IBM Plex Sans', sans-serif; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

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

    .intent-box {
        background: #F1F4F1;
        border: 1px dashed #0F766E;
        border-radius: 10px;
        padding: 10px 16px;
        margin: 8px auto 8px 0;
        max-width: 85%;
        font-size: 0.85rem;
        color: #14532D;
        font-family: 'IBM Plex Mono', monospace;
    }

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
    .timeline-item.error::before { background-color: #DC2626; }
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
    .tool-meta-error { color: #DC2626 !important; }

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


# ----------------- VERSION-AWARE FILE LOADING -----------------
def get_prompt_path(version: str) -> Path:
    versioned = ARTIFACTS_DIR / f"system_prompt_{version}.md"
    return versioned if versioned.exists() else ARTIFACTS_DIR / "system_prompt.md"


def get_tools_path(version: str) -> Path:
    versioned = ARTIFACTS_DIR / f"tools_{version}.yaml"
    return versioned if versioned.exists() else ARTIFACTS_DIR / "tools.yaml"


def discover_versions():
    """Tìm các version có file riêng (system_prompt_v0.md, v1, v2...); fallback v0-v3."""
    found = set()
    for f in ARTIFACTS_DIR.glob("system_prompt_*.md"):
        found.add(f.stem.replace("system_prompt_", ""))
    if not found:
        return ["v0", "v1", "v2", "v3"]
    return sorted(found)


# ----------------- STREAMING HELPER (hiệu ứng gõ chữ) -----------------
def stream_words(text: str, delay: float = 0.03):
    for word in text.split(" "):
        yield word + " "
        time.sleep(delay)


# ----------------- SIDEBAR -----------------
st.sidebar.markdown(
    "<div style='padding: 10px 0;'><h2 style='color:#0F766E; font-weight:800; margin:0;'>AGENT STUDIO</h2>"
    "<p style='color:#5B6472; font-size:0.8rem; margin:0;'>Version Control & Hyperparameters</p></div>",
    unsafe_allow_html=True,
)
st.sidebar.divider()

st.sidebar.markdown("### 🏷️ Target Version")
available_versions = discover_versions()
version_label = st.sidebar.selectbox(
    "Artifact Version",
    available_versions,
    index=len(available_versions) - 1,
    help="Chọn version — tự đọc artifacts/system_prompt_<version>.md nếu có, ngược lại dùng bản mặc định.",
)

st.sidebar.markdown("### 🧠 Reasoning")
enable_intent_analysis = st.sidebar.checkbox(
    "Phân tích ý định trước khi trả lời",
    value=False,
    help="Gọi 1 bước phân tích intent trước, hiển thị riêng, rồi mới chạy tool loop chính.",
)
enable_typing_effect = st.sidebar.checkbox("Hiệu ứng gõ chữ (typing effect)", value=True)

st.sidebar.markdown("### 🔌 LLM Provider")
provider_name = st.sidebar.selectbox("Provider", ["openrouter", "openai", "anthropic", "gemini"], index=0)

model_options = {
    "openrouter": [None, "google/gemini-2.5-flash", "meta-llama/llama-3.3-70b-instruct"],
    "openai": [None, "gpt-4o-mini", "gpt-4o"],
    "anthropic": [None, "claude-3-5-sonnet-latest", "claude-3-5-haiku-latest"],
    "gemini": [None, "gemini-2.5-flash", "gemini-2.5-pro"],
}
selected_model = st.sidebar.selectbox(
    "Model Overwrite", model_options[provider_name],
    format_func=lambda x: "Default model" if x is None else x
)

st.sidebar.markdown("### ⚙️ Parameters")
max_tool_rounds = st.sidebar.slider("Max Tool Rounds", min_value=1, max_value=8, value=4)
history_window = st.sidebar.slider("History Window (Turns)", min_value=1, max_value=10, value=5)

st.sidebar.divider()
st.sidebar.caption(f"📂 **System Prompt:** `{get_prompt_path(version_label).name}`")
st.sidebar.caption(f"🔧 **Tools Schema:** `{get_tools_path(version_label).name}`")


# ----------------- SESSION STATE -----------------
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

    system_prompt_path = get_prompt_path(version_label)
    tools_path = get_tools_path(version_label)

    system_prompt = system_prompt_path.read_text(encoding="utf-8")
    tool_declarations = load_tool_declarations(tools_path)
    to_openai_tools(tool_declarations)  # validate declarations load OK
    provider = make_provider(provider_name)
    real_model = selected_model or getattr(provider, "default_model", None)
    artifact_version = build_artifact_version(version_label, system_prompt_path, tools_path)

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = "_".join([safe_slug(version_label), safe_slug(provider_name), timestamp])
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

if st.session_state.transcript is None:
    reset_session()


# ----------------- HEADER -----------------
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


# ----------------- TABS -----------------
tab_chat, tab_compare = st.tabs(["💬 Live Chat", "📊 Compare Versions"])


# ============================================================
# TAB 1 — LIVE CHAT
# ============================================================
with tab_chat:
    chat_container = st.container()

    with chat_container:
        for msg in st.session_state.history:
            if msg["role"] == "user":
                st.markdown(f"<div class='chat-bubble-user'>{msg['content']}</div>", unsafe_allow_html=True)
            elif msg["role"] == "assistant":
                if msg.get("intent_analysis"):
                    st.markdown(
                        f"<div class='intent-box'>🔎 Ý định: {msg['intent_analysis']}</div>",
                        unsafe_allow_html=True,
                    )
                st.markdown(f"<div class='chat-bubble-agent'>{msg['content']}</div>", unsafe_allow_html=True)

                if msg.get("tool_events"):
                    st.markdown("<div class='dev-console-header'>🛠️ Developer Execution Console</div>", unsafe_allow_html=True)
                    for ev in msg["tool_events"]:
                        res = ev.get("result", {})
                        is_error = "error" in res and res["error"] is not None
                        error_class = "error" if is_error else ""
                        st.markdown(f"""
                        <div class='timeline-item {error_class}'>
                            <div class='tool-box'>
                                <div class='tool-meta {"tool-meta-error" if is_error else ""}'>
                                    <span>▶ TOOL CALL: {ev['tool']}()</span>
                                    <span>STATUS: {"ERROR ❌" if is_error else "SUCCESS ✅"}</span>
                                </div>
                                <div style='margin-top: 8px;'>
                                    <strong style='font-size: 0.8rem; color: #5B6472;'>Arguments:</strong>
                                    <pre><code>{json.dumps(ev['args'], indent=2, ensure_ascii=False)}</code></pre>
                                </div>
                                <div style='margin-top: 8px;'>
                                    <strong style='font-size: 0.8rem; color: #5B6472;'>Output Result:</strong>
                                    <pre><code>{json.dumps(res, indent=2, ensure_ascii=False)}</code></pre>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

    user_input = st.chat_input("Hỏi AI Research Agent hoặc yêu cầu tìm kiếm...")

    if user_input:
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

        system_prompt_path = get_prompt_path(version_label)
        tools_path = get_tools_path(version_label)

        system_prompt = system_prompt_path.read_text(encoding="utf-8")
        tool_declarations = load_tool_declarations(tools_path)
        openai_tools = to_openai_tools(tool_declarations)
        provider = make_provider(provider_name)

        with st.chat_message("assistant"):
            status_placeholder = st.status("Thinking & calling tools...", expanded=True)
            intent_text = None
            try:
                # ---- Bước phân tích ý định (tuỳ chọn) ----
                if enable_intent_analysis:
                    status_placeholder.write("🔎 Đang phân tích yêu cầu...")
                    intent_messages = [
                        {
                            "role": "system",
                            "content": (
                                "Bạn là bước phân tích ý định. Đọc yêu cầu người dùng và trả về "
                                "1 câu ngắn gọn (dưới 20 từ) mô tả: loại yêu cầu (tìm kiếm / đọc URL / "
                                "hỏi lại / hành động nhạy cảm / khác) và ý định chính. "
                                "KHÔNG trả lời câu hỏi, chỉ phân tích."
                            ),
                        },
                        {"role": "user", "content": user_input},
                    ]
                    intent_result = run_model_tool_loop(
                        provider=provider,
                        messages=intent_messages,
                        tools=[],
                        model=selected_model,
                        max_tool_rounds=1,
                    )
                    intent_text = intent_result.get("assistant_text", "").strip()
                    if intent_text:
                        st.markdown(f"<div class='intent-box'>🔎 Ý định: {intent_text}</div>", unsafe_allow_html=True)

                # ---- Vòng chính: xây messages đầy đủ ----
                messages = [
                    {"role": "system", "content": system_prompt},
                    *trim_history(st.session_state.history[:-1], history_window),
                    {"role": "user", "content": user_input},
                ]

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

                # ---- Hiển thị câu trả lời, có/không hiệu ứng gõ chữ ----
                if enable_typing_effect:
                    placeholder = st.empty()
                    displayed = ""
                    for chunk in stream_words(assistant_text):
                        displayed += chunk
                        placeholder.markdown(
                            f"<div class='chat-bubble-agent'>{displayed}▌</div>",
                            unsafe_allow_html=True,
                        )
                    placeholder.markdown(f"<div class='chat-bubble-agent'>{assistant_text}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='chat-bubble-agent'>{assistant_text}</div>", unsafe_allow_html=True)

                tool_events = result.get("tool_events", [])
                if tool_events:
                    st.markdown("<div class='dev-console-header'>🛠️ Developer Execution Console</div>", unsafe_allow_html=True)
                    for ev in tool_events:
                        res = ev.get("result", {})
                        is_error = "error" in res and res["error"] is not None
                        error_class = "error" if is_error else ""
                        st.markdown(f"""
                        <div class='timeline-item {error_class}'>
                            <div class='tool-box'>
                                <div class='tool-meta {"tool-meta-error" if is_error else ""}'>
                                    <span>▶ TOOL CALL: {ev['tool']}()</span>
                                    <span>STATUS: {"ERROR ❌" if is_error else "SUCCESS ✅"}</span>
                                </div>
                                <div style='margin-top: 8px;'>
                                    <strong style='font-size: 0.8rem; color: #5B6472;'>Arguments:</strong>
                                    <pre><code>{json.dumps(ev['args'], indent=2, ensure_ascii=False)}</code></pre>
                                </div>
                                <div style='margin-top: 8px;'>
                                    <strong style='font-size: 0.8rem; color: #5B6472;'>Output Result:</strong>
                                    <pre><code>{json.dumps(res, indent=2, ensure_ascii=False)}</code></pre>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                st.session_state.history.append({
                    "role": "assistant",
                    "content": assistant_text,
                    "tool_events": tool_events,
                    "intent_analysis": intent_text,
                })

            except Exception as exc:
                status_placeholder.update(label="Provider Error", state="error")
                error_msg = f"{type(exc).__name__}: {str(exc)}"
                st.error(error_msg)
                turn_record.update({"status": "provider_error", "error": error_msg})
                st.session_state.history.append({"role": "assistant", "content": f"⚠️ Error: {error_msg}"})

            turn_record["ended_at"] = now_iso()
            st.session_state.transcript["turns"].append(turn_record)
            write_transcript(st.session_state.transcript_path, st.session_state.transcript)
            st.toast("Transcript saved to local disk!", icon="💾")
            st.rerun()


# ============================================================
# TAB 2 — COMPARE VERSIONS
# ============================================================
def load_all_runs():
    if not RUNS_DIR.exists():
        return []
    entries = []
    for f in sorted(RUNS_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        av = data.get("artifact_version")
        label = av.get("version") if isinstance(av, dict) else (data.get("version") or f.stem.split("_")[0])
        entries.append({"label": label or f.stem, "path": f, "data": data})
    return entries


def render_metric_row(summary: dict):
    metrics = [
        ("Case Accuracy", "case_accuracy"),
        ("Tool Routing Accuracy", "tool_routing_accuracy"),
        ("Argument Accuracy", "argument_accuracy"),
        ("Multi-turn Accuracy", "multiturn_accuracy"),
        ("Provider Errors", "provider_error_cases"),
        ("Measured Cases", "measured_cases"),
    ]
    for name, key in metrics:
        val = summary.get(key, "N/A")
        if isinstance(val, float) and key.endswith("accuracy"):
            val = f"{val:.2%}"
        st.markdown(
            f"<div class='metric-badge' style='display:block; margin-bottom:8px;'>{name}: <b>{val}</b></div>",
            unsafe_allow_html=True,
        )


def render_version_comparison():
    runs = load_all_runs()
    if not runs:
        st.info("Chưa có run JSON nào trong `runs/`. Chạy `run_eval.py` trước để có dữ liệu so sánh.")
        return

    labels = [r["label"] for r in runs]
    col1, col2 = st.columns(2)
    with col1:
        left_label = st.selectbox("Version A", labels, index=0, key="cmp_left")
    with col2:
        right_label = st.selectbox("Version B", labels, index=len(labels) - 1, key="cmp_right")

    left_run = next(r for r in runs if r["label"] == left_label)
    right_run = next(r for r in runs if r["label"] == right_label)

    st.markdown("<div class='dev-console-header'>📈 Metric Summary</div>", unsafe_allow_html=True)
    mcol1, mcol2 = st.columns(2)
    with mcol1:
        st.markdown(f"**{left_label}**")
        render_metric_row(left_run["data"].get("summary", {}))
    with mcol2:
        st.markdown(f"**{right_label}**")
        render_metric_row(right_run["data"].get("summary", {}))

    st.markdown("<div class='dev-console-header'>🔍 So sánh từng case</div>", unsafe_allow_html=True)

    def index_by_id(run):
        results = run["data"].get("results", [])
        return {r.get("id", r.get("case_id", str(i))): r for i, r in enumerate(results)}

    left_cases = index_by_id(left_run)
    right_cases = index_by_id(right_run)
    common_ids = sorted(set(left_cases) & set(right_cases))

    if not common_ids:
        st.warning("Không tìm thấy case chung giữa 2 version để so sánh (kiểm tra field `id` trong run JSON).")
        return

    for case_id in common_ids:
        lr = left_cases[case_id]
        rr = right_cases[case_id]
        l_pass = not lr.get("result", {}).get("failures")
        r_pass = not rr.get("result", {}).get("failures")

        if l_pass and not r_pass:
            tag, color = "⚠️ REGRESSION", "#DC2626"
        elif not l_pass and r_pass:
            tag, color = "✅ IMPROVED", "#0F766E"
        elif l_pass and r_pass:
            tag, color = "✅ Ổn định (pass)", "#5B6472"
        else:
            tag, color = "❌ Vẫn fail", "#DC2626"

        with st.expander(f"{case_id} — {tag}"):
            st.markdown(f"<span style='color:{color}; font-weight:600;'>{tag}</span>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.caption(f"{left_label}")
                st.json(lr.get("result", {}))
            with c2:
                st.caption(f"{right_label}")
                st.json(rr.get("result", {}))


with tab_compare:
    render_version_comparison()