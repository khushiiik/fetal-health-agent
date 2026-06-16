import datetime
import json
import uuid
import streamlit as st
import httpx

st.set_page_config(
    page_title="Fetal Health Multi-Agent Dashboard",
    layout="wide"
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
# Sidebar
st.sidebar.title("Settings")

# Backend URL Setup
backend_url = st.sidebar.text_input("Backend API URL", value="http://localhost:8000/api")
st.session_state.backend_url = backend_url

# Theme Styling Application
bg_color = "#000000"
text_color = "#ffffff"
border_color = "#333333"
card_bg = "#1e1e1e"
sidebar_bg = "#121212"

theme_css = f"""
<style>
.stApp {{
    background-color: {bg_color};
    color: {text_color};
}}
[data-testid="stSidebar"] {{
    background-color: {sidebar_bg} !important;
    border-right: 1px solid {border_color};
}}
.stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp span, .stApp label, .stApp li {{
    color: {text_color} !important;
}}
div.card-container {{
    background-color: {card_bg};
    border: 1px solid {border_color};
    padding: 1.2rem;
    border-radius: 8px;
    color: {text_color};
    margin-bottom: 1rem;
}}
input, select, textarea, [data-baseweb="input"] {{
    color: {text_color} !important;
    background-color: {card_bg} !important;
    border-color: {border_color} !important;
}}
div.stStatus {{
    border: 1px solid {border_color} !important;
    background-color: {card_bg} !important;
}}
div.stStatus div {{
    color: {text_color} !important;
}}
</style>
"""
st.markdown(theme_css, unsafe_allow_html=True)

# Main Header
st.title("Fetal Health Multi-Agent Monitoring Dashboard")
st.markdown("Monitor the execution of the fetal health agent pipeline and view generated diagnostic reports.")
st.markdown("---")

# Helper functions for rendering status and logs
def render_status(placeholder, states):
    with placeholder.container():
        st.subheader("Pipeline Status")
        icons = {
            "Idle": "⚪",
            "Running": "🟡",
            "Completed": "✅",
            "Failed": "❌"
        }
        st.markdown(
            f"""
            <div class="card-container">
                <p>{icons[states['Orchestrator']]} <b>Orchestrator</b>: {states['Orchestrator']}</p>
                <p>{icons[states['SQL Agent']]} <b>SQL Agent</b>: {states['SQL Agent']}</p>
                <p>{icons[states['Research Agent']]} <b>Research Agent</b>: {states['Research Agent']}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

def render_logs(placeholder, logs):
    with placeholder.container():
        st.subheader("Tool Execution Log")
        if not logs:
            st.write("No execution logs yet...")
            return
        for log in logs:
            st.markdown(
                f"""
                <div class="card-container" style="border-left: 4px solid #0066cc;">
                    <span style="font-size: 0.8rem; color: #888;">[{log['timestamp']}]</span><br>
                    <b>Agent:</b> {log['agent']}<br>
                    <b>Tool:</b> <code style="color: #d63384;">{log['tool']}</code><br>
                    <b>Input:</b> <code>{log['input']}</code><br>
                    <b>Output:</b> {log['output']}<br>
                </div>
                """,
                unsafe_allow_html=True
            )

# Layout columns: Left for control & progress, Right for logs
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Input Section")
    fetus_id = st.text_input("Enter Fetus ID", value="FET-1005")
    analyze_clicked = st.button("Analyze", type="primary")
    st.markdown("---")
    status_placeholder = st.empty()

with col2:
    logs_placeholder = st.empty()

# Always render current status at page load
render_status(status_placeholder, st.session_state.pipeline_states)

# Render logs if they exist or if currently running
if st.session_state.current_logs or st.session_state.pipeline_states["Orchestrator"] == "Running":
    render_logs(logs_placeholder, st.session_state.current_logs)

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
                f"{backend_url}/chat/stream",
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
                                    if log["tool"] == tool_name and log["output"] == "Running...":
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
                            "timestamp": datetime.datetime.now().strftime("%H:%M %p"),
                            "report": st.session_state.current_report,
                            "report_markdown": st.session_state.current_report_markdown,
                            "logs": st.session_state.current_logs,
                            "chat_history": []
                        })
                        st.success("Analysis complete!")
                        st.rerun()
        except Exception as ex:
            st.error(f"Failed to communicate with backend: {str(ex)}")

# Report output panel
if st.session_state.current_report:
    st.markdown("---")
    st.header("Diagnostic Report")
    
    # Markdown output rendering
    st.markdown(st.session_state.current_report_markdown)
    
    # Raw JSON expander
    with st.expander("Raw JSON Report"):
        st.json(st.session_state.current_report)
        
    # Follow-up questions panel
    st.markdown("---")
    st.header("Follow-Up Questions")
    
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
                    f"{backend_url}/chat/stream",
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
            except Exception as ex:
                st.error(f"Error communicating with backend: {str(ex)}")

# Sidebar analysis history rendering
if st.session_state.history:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Analysis History")
    for idx, item in enumerate(st.session_state.history):
        time_str = item["timestamp"]
        label = f"{item['fetus_id']} - {item['classification'].upper()} ({time_str})"
        if st.sidebar.button(label, key=f"hist_{idx}_{item['session_id']}"):
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
