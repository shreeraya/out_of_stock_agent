import os
import streamlit as st
import requests

# Setup page layout
st.set_page_config(
    page_title="Supply Chain Sentinel",
    page_icon="🛡️",
    layout="centered", # Centered layout is perfect for a clean chatbot-only interface
    initial_sidebar_state="expanded"
)

# API Server Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

# Custom CSS styling for premium look & feel
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Elegant Title Banner */
    .title-banner {
        background: linear-gradient(135deg, #2c3e50 0%, #1e3c72 100%);
        color: white;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
        text-align: center;
    }
    .title-banner h1 {
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .title-banner p {
        margin: 0.5rem 0 0 0;
        font-size: 1rem;
        opacity: 0.9;
        font-weight: 300;
    }
    
    /* Agent Trigger Badge */
    .agent-badge {
        font-size: 0.8rem;
        font-weight: 600;
        color: #718096;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)

# Helper to check API status
def get_api_health():
    try:
        r = requests.get(f"{API_BASE_URL}/api/health", timeout=3)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

# Sidebar Content
st.sidebar.markdown("<h2 style='text-align: center; color: #1e3c72;'>SC Sentinel 🛡️</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='text-align: center; font-style: italic; font-size: 0.85rem;'>Supply Chain Conversational Copilot</p>", unsafe_allow_html=True)
st.sidebar.divider()

# Health Status Indicator
health = get_api_health()
if health:
    st.sidebar.success("● API BACKEND CONNECTED")
    if health.get("llm_online"):
        st.sidebar.info("● OpenAI Cognitive AI: ONLINE")
    else:
        st.sidebar.warning("● OpenAI Cognitive AI: OFFLINE")
else:
    st.sidebar.error("❌ API BACKEND DISCONNECTED")
    st.sidebar.info("Please start the backend API: `uvicorn src.api:app --reload`")

# Download Analysis Report Button in Sidebar
st.sidebar.divider()
st.sidebar.subheader("Audit Reports")
st.sidebar.write("Retrieve the generated styled spreadsheet containing forecasting error and safety stock parameters.")

try:
    r = requests.get(f"{API_BASE_URL}/api/download")
    if r.status_code == 200:
        st.sidebar.download_button(
            label="Download sc_audit_report.xlsx",
            data=r.content,
            file_name="sc_audit_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
except Exception:
    st.sidebar.info("Audit report Excel file will appear here once the first analysis is compiled.")

st.sidebar.divider()
st.sidebar.markdown(
    "<div style='font-size: 0.8rem; color:#718096; text-align: center;'>"
    "Supply Chain Sentinel v3.0 • Conversational UI"
    "</div>", 
    unsafe_allow_html=True
)

# Header Banner
st.markdown("""
<div class="title-banner">
    <h1>Supply Chain Sentinel 🛡️</h1>
    <p>Conversational Multi-Agent Copilot for OOS Risks, Forecasting, and Inventory Parameters.</p>
</div>
""", unsafe_allow_html=True)

# Initialize Session State
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    
# Automatically trigger pre-cache call on load
if health and not st.session_state.chat_history:
    with st.spinner("Initializing Supply Chain Sentinel cache..."):
        try:
            # Wake up cache
            requests.post(f"{API_BASE_URL}/api/run-pipeline")
            
            init_msg = (
                "Welcome to **Supply Chain Sentinel**.\n\n"
                "I am your central coordinator copilot. I have analyzed the background database and loaded the agent audits:\n"
                "- **OOS Risks Agent**: Evaluates simulated timelines and stockout parameters.\n"
                "- **Forecasting Auditor**: Analyzes historical actual sales to compute MAPE & Bias error rates.\n"
                "- **Inventory Optimizer**: Recommends optimal Safety Stock, EOQ, and Stock Turn rates.\n\n"
                "Ask me anything directly about stockout risks, forecasting accuracy, or safety stock optimizations!"
            )
            st.session_state.chat_history.append({"role": "assistant", "content": init_msg, "agent_triggered": "general"})
        except Exception as e:
            st.error(f"Failed to connect to API backend: {e}")

# Display chat history
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        # Show which agent was triggered for the response
        if msg["role"] == "assistant" and msg.get("agent_triggered"):
            agent_map = {
                "oos": "🚨 OOS Guard Agent Team",
                "forecasting": "📈 Forecasting Auditor Agent",
                "inventory": "⚙️ Inventory Optimizer Agent",
                "general": "🛡️ Coordinator Copilot"
            }
            agent_name = agent_map.get(msg["agent_triggered"], "Coordinator Copilot")
            st.markdown(f"<div class='agent-badge'>🤖 {agent_name}</div>", unsafe_allow_html=True)
        st.write(msg["content"])

# Capture user query
if user_prompt := st.chat_input("Query Supply Chain Sentinel...", disabled=(health is None)):
    # Append user prompt
    st.session_state.chat_history.append({"role": "user", "content": user_prompt})
    
    with st.chat_message("user"):
        st.write(user_prompt)
        
    with st.chat_message("assistant"):
        with st.spinner("Consulting Supply Chain Sentinel specialists..."):
            try:
                # Format payload
                history_payload = []
                for m in st.session_state.chat_history[:-1]:
                    history_payload.append({"role": m["role"], "content": m["content"]})
                    
                payload = {
                    "message": user_prompt,
                    "history": history_payload,
                    "context": {} # Backend holds the pre-cached pipeline context now!
                }
                
                # Call REST API chat endpoint
                r = requests.post(f"{API_BASE_URL}/api/chat", json=payload)
                if r.status_code == 200:
                    reply_data = r.json()
                    reply = reply_data.get("response", "No response could be computed.")
                    agent_triggered = reply_data.get("agent_triggered", "general")
                    
                    # Display response
                    agent_map = {
                        "oos": "🚨 OOS Guard Agent Team",
                        "forecasting": "📈 Forecasting Auditor Agent",
                        "inventory": "⚙️ Inventory Optimizer Agent",
                        "general": "🛡️ Coordinator Copilot"
                    }
                    agent_name = agent_map.get(agent_triggered, "Coordinator Copilot")
                    st.markdown(f"<div class='agent-badge'>🤖 {agent_name}</div>", unsafe_allow_html=True)
                    st.write(reply)
                    
                    # Save reply with agent tag
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": reply,
                        "agent_triggered": agent_triggered
                    })
                    
                    # Rerun to update the download report button status in sidebar (if compiled on this request)
                    st.rerun()
                else:
                    st.error(f"Error from API backend: {r.text}")
            except Exception as e:
                st.error(f"Failed to connect to API backend: {e}")
