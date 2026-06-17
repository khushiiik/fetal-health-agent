import datetime
import json
import os
import uuid
import streamlit as st
import httpx

st.set_page_config(
    page_title="Fetal Health Multi-Agent Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize session states
if "history" not in st.session_state:
    st.session_state.history = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "current_report" not in st.session_state:
    st.session_state.current_report = None
if "current_report_markdown" not in st.session_state:
    st.session_state.current_report_markdown = None
if "current_logs" not in st.session_state:
    st.session_state.current_logs = []
if "current_fetus_id" not in st.session_state:
    st.session_state.current_fetus_id = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pipeline_states" not in st.session_state:
    st.session_state.pipeline_states = {
        "Orchestrator": "Idle",
        "SQL Agent": "Idle",
        "Research Agent": "Idle"
    }

# Backend URL Setup (Moved to main UI page, under settings expander)
default_backend = os.environ.get("BACKEND_API_URL", "http://localhost:8000/api")
if "backend_url" not in st.session_state:
    st.session_state.backend_url = default_backend

# High-fidelity theme CSS styling
theme_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* Global Reset and Font */
html, body, [class*="css"], .stApp {
    font-family: 'Outfit', sans-serif !important;
    background: linear-gradient(135deg, #070b13 0%, #0d1527 100%) !important;
    color: #cbd5e1 !important;
}

/* Hide Streamlit components */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
[data-testid="collapsedSidebarCodegen"] {
    display: none !important;
}
[data-testid="stSidebar"] {
    display: none !important;
}

/* Card layout container */
div.card-container {
    background: rgba(17, 25, 40, 0.55) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    padding: 1.5rem;
    border-radius: 16px !important;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37) !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
    margin-bottom: 1.2rem;
}

/* Titles and Headers */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: -0.02em !important;
    color: #ffffff !important;
}

.title-text {
    background: linear-gradient(90deg, #60a5fa 0%, #3b82f6 50%, #1d4ed8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.8rem !important;
    font-weight: 800 !important;
    margin-bottom: 0.2rem !important;
    letter-spacing: -0.03em !important;
}

.subtitle-text {
    font-size: 1.1rem;
    color: #94a3b8;
    margin-bottom: 1.5rem;
    font-weight: 300;
}

/* Form inputs styling */
input, select, textarea, [data-baseweb="input"], [data-baseweb="select"] {
    color: #ffffff !important;
    background-color: rgba(15, 23, 42, 0.8) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 10px !important;
    padding: 0.5rem 0.8rem !important;
    transition: all 0.3s ease !important;
}

input:focus, select:focus, textarea:focus {
    border-color: #3b82f6 !important;
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.25) !important;
}

/* Primary buttons styling */
button[kind="primary"] {
    background: linear-gradient(90deg, #2563eb, #1d4ed8) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.6rem 1.8rem !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 14px 0 rgba(37, 99, 235, 0.3) !important;
    transition: all 0.3s ease !important;
    width: 100% !important;
}

button[kind="primary"]:hover {
    background: linear-gradient(90deg, #3b82f6, #2563eb) !important;
    box-shadow: 0 6px 20px 0 rgba(37, 99, 235, 0.5) !important;
    transform: translateY(-1px) !important;
}

/* Secondary/Standard buttons */
button[kind="secondary"] {
    background: rgba(255, 255, 255, 0.03) !important;
    color: #94a3b8 !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 10px !important;
    padding: 0.6rem 1rem !important;
    transition: all 0.2s ease !important;
    font-size: 0.85rem !important;
    text-align: left !important;
    width: 100% !important;
}

button[kind="secondary"]:hover {
    background: rgba(255, 255, 255, 0.07) !important;
    color: #ffffff !important;
    border-color: rgba(255, 255, 255, 0.2) !important;
}

/* Custom styling for Expanders */
.streamlit-expanderHeader {
    background-color: rgba(17, 25, 40, 0.45) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 10px !important;
    color: #ffffff !important;
}

div.stStatus {
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    background-color: rgba(17, 25, 40, 0.45) !important;
    border-radius: 10px !important;
}

div.stStatus div {
    color: #cbd5e1 !important;
}

/* Custom markdown rendering */
.stMarkdown p, .stMarkdown li {
    font-size: 0.95rem;
    line-height: 1.6;
    color: #cbd5e1 !important;
}

/* Divider styling */
hr {
    border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
}
</style>
"""
st.markdown(theme_css, unsafe_allow_html=True)

# Main Header Design
st.markdown('<div class="title-text">Fetal Health Multi-Agent Monitor</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle-text">Real-time pipeline monitoring and clinical diagnostic reporting powered by AI</div>', unsafe_allow_html=True)

# Helper functions for rendering status and logs
def render_status(placeholder, states):
    with placeholder.container():
        st.markdown("### ⚡ Pipeline Status")
        icons = {
            "Idle": "⚪",
            "Running": "🟡",
            "Completed": "🟢",
            "Failed": "🔴"
        }
        st.markdown(
            f"""
            <div class="card-container">
                <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>🧠 <b>Orchestrator</b></span>
                        <span style="background-color: rgba(255,255,255,0.05); padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.85rem;">
                            {icons[states['Orchestrator']]} {states['Orchestrator']}
                        </span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>🗄️ <b>SQL Agent</b></span>
                        <span style="background-color: rgba(255,255,255,0.05); padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.85rem;">
                            {icons[states['SQL Agent']]} {states['SQL Agent']}
                        </span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>📚 <b>Research Agent</b></span>
                        <span style="background-color: rgba(255,255,255,0.05); padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.85rem;">
                            {icons[states['Research Agent']]} {states['Research Agent']}
                        </span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

def render_logs(placeholder, logs):
    with placeholder.container():
        st.markdown("### 🖥️ Console & Execution Log")
        if not logs:
            st.markdown(
                """
                <div class="card-container" style="background-color: rgba(9, 13, 22, 0.4) !important; border-style: dashed !important; text-align: center; padding: 3rem 1rem; color: #64748b;">
                    No log outputs active. Enter a Fetus ID and click 'Analyze' to spin up the pipeline.
                </div>
                """,
                unsafe_allow_html=True
            )
            return
            
        with st.container(height=480):
            for log in logs:
                if log.get("type") == "backend_log":
                    msg = log['message']
                    # Color code borders based on level
                    if " | ERROR " in msg or " | CRITICAL " in msg:
                        border_color = "#ef4444"  # Red
                    elif " | WARNING " in msg:
                        border_color = "#f59e0b"  # Amber
                    else:
                        border_color = "#10b981"  # Emerald/Green
                    
                    st.markdown(
                        f"""
                        <div class="card-container" style="border-left: 4px solid {border_color}; margin-bottom: 0.6rem; padding: 0.6rem 0.9rem; font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; background-color: rgba(9, 13, 22, 0.8) !important;">
                            {msg}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f"""
                        <div class="card-container" style="border-left: 4px solid #3b82f6; margin-bottom: 0.6rem; padding: 0.75rem 1rem; background-color: rgba(17, 25, 40, 0.45) !important;">
                            <span style="font-size: 0.75rem; color: #64748b;">[{log['timestamp']}]</span><br>
                            <span style="font-size: 0.85rem; color: #94a3b8;">🤖 <b>Agent:</b> {log['agent']}</span><br>
                            <span style="font-size: 0.85rem; color: #94a3b8;">🔧 <b>Tool:</b> <code style="color: #f43f5e; background-color: rgba(244, 63, 94, 0.1); padding: 0.1rem 0.3rem; border-radius: 4px; font-family: 'JetBrains Mono', monospace;">{log['tool']}</code></span><br>
                            <span style="font-size: 0.85rem; color: #94a3b8;">📥 <b>Input:</b> <code style="color: #cbd5e1; font-family: 'JetBrains Mono', monospace;">{log['input']}</code></span><br>
                            <span style="font-size: 0.85rem; color: #94a3b8;">📤 <b>Output:</b> <span style="color: #60a5fa;">{log['output']}</span></span>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

# Layout columns: Left for control & progress, Right for logs
col1, col2 = st.columns([4, 6])

with col1:
    st.markdown("### 🎛️ Analysis Controls")
    with st.container():
        st.markdown('<div class="card-container">', unsafe_allow_html=True)
        fetus_id = st.text_input("Fetus ID", value="FET-1005", help="Enter a fetus identifier to query the database (e.g., FET-1005)")
        analyze_clicked = st.button("Start Diagnostics Pipeline", type="primary")
        
        # Connection Settings inside an expander
        with st.expander("⚙️ Connection Settings"):
            backend_url = st.text_input("Backend API URL", value=st.session_state.backend_url)
            st.session_state.backend_url = backend_url
        st.markdown('</div>', unsafe_allow_html=True)
        
    status_placeholder = st.empty()
    
    # Render session history log
    if st.session_state.history:
        st.markdown("### 📋 Recent Analyses")
        for idx, item in enumerate(st.session_state.history):
            time_str = item["timestamp"]
            classification = item['classification'].upper()
            
            # Colored dot for classification status
            dot = "🟢"
            if classification == "ABNORMAL" or classification == "PATHOLOGICAL":
                dot = "🔴"
            elif classification == "SUSPECT" or classification == "BORDERLINE":
                dot = "🟡"
                
            label = f"{dot} {item['fetus_id']} - {classification} ({time_str})"
            if st.button(label, key=f"hist_{idx}_{item['session_id']}", use_container_width=True):
                st.session_state.session_id = item["session_id"]
                st.session_state.current_report = item["report"]
                st.session_state.current_report_markdown = item["report_markdown"]
                st.session_state.current_logs = item["logs"]
                st.session_state.current_fetus_id = item["fetus_id"]
                st.session_state.chat_history = item.get("chat_history", [])
                st.session_state.pipeline_states = {
                    "Orchestrator": "Completed",
                    "SQL Agent": "Completed",
                    "Research Agent": "Completed"
                }
                st.rerun()

with col2:
    logs_placeholder = st.empty()

# Always render current status at page load
render_status(status_placeholder, st.session_state.pipeline_states)

# Render logs if they exist or if currently running
if st.session_state.current_logs or st.session_state.pipeline_states["Orchestrator"] == "Running":
    render_logs(logs_placeholder, st.session_state.current_logs)
else:
    render_logs(logs_placeholder, [])

if analyze_clicked:
    if not fetus_id.strip():
        st.error("Please enter a valid Fetus ID")
    else:
        # Reset states for a new analysis run
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.current_report = None
        st.session_state.current_report_markdown = None
        st.session_state.current_logs = []
        st.session_state.current_fetus_id = fetus_id.strip()
        st.session_state.chat_history = []
        st.session_state.pipeline_states = {
            "Orchestrator": "Running",
            "SQL Agent": "Idle",
            "Research Agent": "Idle"
        }
        
        # Perform stream request
        try:
            render_status(status_placeholder, st.session_state.pipeline_states)
            render_logs(logs_placeholder, st.session_state.current_logs)
            
            with httpx.stream(
                "POST",
                f"{st.session_state.backend_url}/chat/stream",
                json={"message": f"Analyze fetus {fetus_id.strip()}", "session_id": st.session_state.session_id},
                timeout=60.0
            ) as r:
                for line in r.iter_lines():
                    if not line:
                        continue
                    event = json.loads(line)
                    event_type = event.get("type")
                    
                    if event_type == "error":
                        st.session_state.pipeline_states["Orchestrator"] = "Failed"
                        for k, v in st.session_state.pipeline_states.items():
                            if v == "Running":
                                st.session_state.pipeline_states[k] = "Failed"
                        render_status(status_placeholder, st.session_state.pipeline_states)
                        st.error(f"Backend execution failed: {event.get('error')}")
                        break
                        
                    elif event_type == "event":
                        data = event.get("data", {})
                        author = data.get("author", "")
                        node_name = data.get("node_info", {}).get("name") if data.get("node_info") else author
                        
                        # Update pipeline visual states based on active node
                        if node_name == "sql_agent":
                            st.session_state.pipeline_states["Orchestrator"] = "Running"
                            st.session_state.pipeline_states["SQL Agent"] = "Running"
                        elif node_name == "research_agent":
                            st.session_state.pipeline_states["SQL Agent"] = "Completed"
                            st.session_state.pipeline_states["Research Agent"] = "Running"
                        
                        render_status(status_placeholder, st.session_state.pipeline_states)
                        
                        # Parse tool executions
                        parts = data.get("content", {}).get("parts", []) if data.get("content") else []
                        for part in parts:
                            if part.get("function_call"):
                                fc = part["function_call"]
                                st.session_state.current_logs.append({
                                    "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                                    "agent": "SQL Agent" if node_name == "sql_agent" else "Research Agent",
                                    "tool": fc.get("name", "unknown"),
                                    "input": json.dumps(fc.get("args", {})),
                                    "output": "Running..."
                                })
                                render_logs(logs_placeholder, st.session_state.current_logs)
                                
                            elif part.get("function_response"):
                                fr = part["function_response"]
                                tool_name = fr.get("name", "")
                                raw_resp = fr.get("response")
                                
                                # Output summarizer
                                summary_text = "Completed"
                                if tool_name == "fetch_fetal_record":
                                    if isinstance(raw_resp, dict) and "patient_id" in raw_resp:
                                        summary_text = f"Record Found (Patient: {raw_resp['patient_id']})"
                                    elif isinstance(raw_resp, dict) and "error" in raw_resp:
                                        summary_text = f"Fetus not found: {raw_resp.get('error')}"
                                    else:
                                        summary_text = "Fetus not found"
                                elif tool_name == "analyse_vitals":
                                    if isinstance(raw_resp, list):
                                        abnormal = sum(1 for x in raw_resp if x.get("status") == "abnormal")
                                        borderline = sum(1 for x in raw_resp if x.get("status") == "borderline")
                                        summary_text = f"Analyzed vitals. Abnormal findings: {abnormal}, Borderline: {borderline}"
                                elif tool_name == "format_report" or tool_name == "run_fetal_analysis":
                                    summary_text = "Diagnostic report generated"
                                
                                # Match tool response to tool call log
                                updated = False
                                for log in reversed(st.session_state.current_logs):
                                    if log.get("tool") == tool_name and log.get("output") == "Running...":
                                        log["output"] = summary_text
                                        updated = True
                                        break
                                if not updated:
                                    st.session_state.current_logs.append({
                                        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                                        "agent": "SQL Agent" if node_name == "sql_agent" else "Research Agent",
                                        "tool": tool_name,
                                        "input": "N/A",
                                        "output": summary_text
                                    })
                                render_logs(logs_placeholder, st.session_state.current_logs)
                                
                    elif event_type == "log":
                        st.session_state.current_logs.append({
                            "type": "backend_log",
                            "message": event.get("message", "")
                        })
                        render_logs(logs_placeholder, st.session_state.current_logs)
                        
                    elif event_type == "complete":
                        st.session_state.pipeline_states = {
                            "Orchestrator": "Completed",
                            "SQL Agent": "Completed",
                            "Research Agent": "Completed"
                        }
                        render_status(status_placeholder, st.session_state.pipeline_states)
                        
                        st.session_state.current_report = event.get("report")
                        st.session_state.current_report_markdown = event.get("report_markdown")
                        
                        # Classification for history log
                        classification = "healthy"
                        if st.session_state.current_report:
                            analysis = st.session_state.current_report.get("analysis", {})
                            classification = analysis.get("overall_classification", "healthy")
                        
                        # Add to Session History
                        st.session_state.history.append({
                            "session_id": st.session_state.session_id,
                            "fetus_id": st.session_state.current_fetus_id,
                            "classification": classification,
                            "timestamp": datetime.datetime.now().strftime("%I:%M %p"),
                            "report": st.session_state.current_report,
                            "report_markdown": st.session_state.current_report_markdown,
                            "logs": st.session_state.current_logs,
                            "chat_history": []
                        })
                        st.success("Analysis complete!")
                        st.rerun()
        except Exception as ex:
            st.error(f"Failed to communicate with backend: {str(ex)}")

# Report output panel (Diagnostic Report & Chat side by side at bottom)
if st.session_state.current_report:
    st.markdown("---")
    
    rep_col, chat_col = st.columns([6, 4])
    
    with rep_col:
        st.markdown("### 📋 Diagnostic Report")
        with st.container():
            st.markdown('<div class="card-container">', unsafe_allow_html=True)
            # Markdown output rendering
            st.markdown(st.session_state.current_report_markdown)
            st.markdown('</div>', unsafe_allow_html=True)
            
        # Raw JSON expander
        with st.expander("🔍 Raw JSON Report"):
            st.json(st.session_state.current_report)
            
    with chat_col:
        st.markdown("### 💬 Clinical Follow-Up Chat")
        with st.container():
            st.markdown('<div class="card-container">', unsafe_allow_html=True)
            
            # Chat history inside a scrollable container
            with st.container(height=380):
                if not st.session_state.chat_history:
                    st.caption("Query the assistant for clarifications, vital checks, or general clinical follow-ups.")
                for chat_msg in st.session_state.chat_history:
                    with st.chat_message(chat_msg["role"]):
                        st.markdown(chat_msg["content"])
                        
            user_q = st.chat_input("Ask a follow-up question...")
            if user_q:
                st.session_state.chat_history.append({"role": "user", "content": user_q})
                with st.chat_message("user"):
                    st.markdown(user_q)
                    
                with st.chat_message("assistant"):
                    message_placeholder = st.empty()
                    full_response = ""
                    try:
                        with httpx.stream(
                            "POST",
                            f"{st.session_state.backend_url}/chat/stream",
                            json={"message": user_q, "session_id": st.session_state.session_id},
                            timeout=60.0
                        ) as r:
                            for line in r.iter_lines():
                                if not line:
                                    continue
                                event = json.loads(line)
                                event_type = event.get("type")
                                if event_type == "follow_up_chunk":
                                    chunk = event.get("chunk", "")
                                    full_response += chunk
                                    message_placeholder.markdown(full_response + "▌")
                                elif event_type == "follow_up_complete":
                                    full_response = event.get("answer", full_response)
                                    message_placeholder.markdown(full_response)
                                    
                        st.session_state.chat_history.append({"role": "assistant", "content": full_response})
                        
                        # Sync history state
                        for hist_item in st.session_state.history:
                            if hist_item["session_id"] == st.session_state.session_id:
                                hist_item["chat_history"] = st.session_state.chat_history
                                break
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Error communicating with backend: {str(ex)}")
            st.markdown('</div>', unsafe_allow_html=True)
