import os
import streamlit as st
import requests
import pandas as pd
import json

# Setup page layout
st.set_page_config(
    page_title="StockSentinel - Supply Chain OOS Guard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Server Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

# Custom CSS styling for premium look & feel
st.markdown("""
<style>
    /* Executive Slate Theme custom typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Elegant Title Banner */
    .title-banner {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        padding: 2.5rem;
        border-radius: 12px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
        position: relative;
    }
    .title-banner h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .title-banner p {
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        opacity: 0.9;
        font-weight: 300;
    }
    
    /* Metric Cards */
    .metric-card {
        background-color: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        border-top: 5px solid #1e3c72;
        text-align: center;
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
    }
    .metric-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #718096;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.5rem;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1A365D;
    }
    
    /* Custom severity tags */
    .badge {
        padding: 6px 12px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        display: inline-block;
        text-align: center;
    }
    .badge-high {
        background-color: #FED7D7;
        color: #9B2C2C;
    }
    .badge-medium {
        background-color: #FEEBC8;
        color: #9C4221;
    }
    .badge-low {
        background-color: #C6F6D5;
        color: #22543D;
    }
    
    /* Interactive block wraps */
    .detail-card {
        background: #F8FAFC;
        border-left: 4px solid #3B82F6;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 1rem;
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
st.sidebar.markdown("<h2 style='text-align: center; color: #1e3c72;'>StockSentinel 🛡️</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='text-align: center; font-style: italic; font-size: 0.9rem;'>Weekly Multi-Agent OOS Guard</p>", unsafe_allow_html=True)
st.sidebar.divider()

# Health Status Indicator
health = get_api_health()
if health:
    if health.get("llm_online"):
        st.sidebar.success("● CONNECTED (Cognitive AI)")
    else:
        st.sidebar.warning("● CONNECTED (Offline Heuristics)")
else:
    st.sidebar.error("❌ DISCONNECTED (FastAPI Offline)")
    st.sidebar.info("Please start the backend API: `uvicorn src.api:app --reload`")

st.sidebar.divider()

# File Upload / Pipeline Actions
st.sidebar.subheader("Replenishment Pipeline Setup")
uploaded_file = st.sidebar.file_uploader("Upload ERP Input Sheet", type=["xlsx"])

use_mock = st.sidebar.checkbox("Load Sample Mock Scenarios")

run_btn = st.sidebar.button("Run Multi-Agent Analysis", use_container_width=True, disabled=(not uploaded_file and not use_mock))

st.sidebar.divider()
st.sidebar.markdown(
    "<div style='font-size: 0.85rem; color:#718096; text-align: center;'>"
    "StockSentinel Engine v1.0 • Decoupled Architecture"
    "</div>", 
    unsafe_allow_html=True
)

# Header Banner
st.markdown("""
<div class="title-banner">
    <h1>StockSentinel 🛡️</h1>
    <p>Predict supply chain out-of-stock events, diagnose volatility root causes, and formulate ERP directives.</p>
</div>
""", unsafe_allow_html=True)

# Initialize Session State
if "pipeline_results" not in st.session_state:
    st.session_state.pipeline_results = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Triggers pipeline run
if run_btn:
    with st.spinner("Executing week-by-week simulation and invoking diagnostic agents..."):
        try:
            # Determine which file payload to send
            if uploaded_file:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            elif use_mock:
                # Load the workspace template
                mock_path = "input_template.xlsx"
                if not os.path.exists(mock_path):
                    st.error("Mock file 'input_template.xlsx' not found. Please run python generate_template.py first.")
                    st.stop()
                with open(mock_path, "rb") as f:
                    files = {"file": ("input_template.xlsx", f.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            
            # Send file to FastAPI backend
            response = requests.post(f"{API_BASE_URL}/api/run-pipeline", files=files)
            if response.status_code == 200:
                res_data = response.json()
                st.session_state.pipeline_results = res_data
                st.success("Analysis pipeline executed successfully!")
                
                # Auto-initialize Chatbot introduction message
                oos_count = len(res_data.get("oos_risks", []))
                init_msg = (
                    f"Hi! I am the StockSentinel Copilot. I have reviewed the simulation results.\n\n"
                    f"I detected **{oos_count} out-of-stock risk(s)** in the upcoming 12-week horizon.\n"
                    "Ask me about any SKU (e.g., 'What is causing the stockout on SKU-003?') or general logistics mitigation suggestions!"
                )
                st.session_state.chat_history = [{"role": "assistant", "content": init_msg}]
            else:
                st.error(f"Error from API backend: {response.text}")
        except Exception as e:
            st.error(f"Failed to connect to API backend: {e}")

# Application Main Tabs
tab_dash, tab_chat = st.tabs(["📊 Executive Dashboard", "💬 Interactive Copilot Chat"])

# TAB 1: EXECUTIVE DASHBOARD
with tab_dash:
    if not st.session_state.pipeline_results:
        st.info("👈 Please load the mock scenarios or upload an Excel template in the sidebar, then click 'Run Multi-Agent Analysis' to explore the dashboard.")
    else:
        results = st.session_state.pipeline_results
        oos_risks = results.get("oos_risks", [])
        rca_results = results.get("rca_results", [])
        mitigation_results = results.get("mitigation_results", [])
        
        # Summary Metrics
        total_skus = 5  # Fixed mock size, can be calculated dynamically
        high_severity = sum(1 for r in oos_risks if r.get("Severity_Level") == "High")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total SKUs Tracked</div>
                <div class="metric-value">{total_skus}</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">OOS Risks Detected</div>
                <div class="metric-value">{len(oos_risks)}</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">High Severity Risks</div>
                <div class="metric-value" style="color: #9B2C2C;">{high_severity}</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.subheader("Simulated Stockout Incidents")
        if not oos_risks:
            st.success("No stockout risks detected. Inventory levels remain healthy!")
        else:
            # Build DataFrame for dashboard risk table
            df_risks = pd.DataFrame(oos_risks)
            
            # Format display
            df_risks["Stockout_Probability"] = df_risks["Stockout_Probability"].map(lambda x: f"{x * 100:.1f}%")
            df_risks_display = df_risks[["SKU", "DC", "Week_of_OOS", "Weeks_Until_OOS", "Current_Stock", "Projected_Stock_on_OOS_Date", "Stockout_Probability", "Severity_Level"]].copy()
            
            st.dataframe(df_risks_display, use_container_width=True, hide_index=True)
            
            # Detailed Drill Down Section
            st.divider()
            st.subheader("🔍 Deep-Dive Diagnostic & Action Plan")
            
            # Selection boxes
            sku_options = df_risks["SKU"].unique()
            sel_sku = st.selectbox("Select SKU to Auditing", sku_options)
            
            # Filter diagnostic and mitigation reports
            rca_rep = next((r for r in rca_results if r["SKU"] == sel_sku), None)
            mit_rep = next((m for m in mitigation_results if m["SKU"] == sel_sku), None)
            risk_rep = next((o for o in oos_risks if o["SKU"] == sel_sku), None)
            
            col_left, col_right = st.columns(2)
            
            with col_left:
                if rca_rep:
                    st.markdown(f"#### 🏷️ Root Cause Analysis (RCA)")
                    st.markdown(f"**Primary Diagnosis:** `{rca_rep.get('Primary_Root_Cause', 'N/A')}`")
                    st.markdown(f"**Secondary Factors:** *{rca_rep.get('Secondary_Factors', 'N/A')}*")
                    
                    st.markdown("##### Narrative Diagnostics Summary:")
                    st.markdown(f"<div class='detail-card'>{rca_rep.get('Narrative_Reasoning', 'N/A')}</div>", unsafe_allow_html=True)
            
            with col_right:
                if mit_rep:
                    st.markdown(f"#### 🛠️ Planner Mitigation Plan")
                    st.markdown(f"**Recommended Action:** `{mit_rep.get('Recommended_Action', 'N/A')}`")
                    
                    cost_val = mit_rep.get('Estimated_Cost_USD', 0.0)
                    st.markdown(f"**Estimated Costs (USD):** `${cost_val:,.2f}`")
                    st.markdown(f"**Net Inventory Impact:** `{mit_rep.get('Inventory_Impact_Units', 0):,}` units")
                    
                    st.markdown("##### ERP Execution Checklist:")
                    st.markdown(mit_rep.get('Action_Steps', 'N/A'))
            
            # Download compiled excel section
            st.divider()
            st.subheader("📥 Download Spreadsheet Report")
            st.write("Retrieve the professionally formatted corporate Excel report containing Zebra striping, color severity codes, and summary KPI charts.")
            
            try:
                report_download_url = f"{API_BASE_URL}/api/download"
                r = requests.get(report_download_url)
                if r.status_code == 200:
                    st.download_button(
                        label="Download oos_analysis_report.xlsx",
                        data=r.content,
                        file_name="oos_analysis_report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    st.error("Backend report file not compiled on the API disk.")
            except Exception as e:
                st.error(f"Failed to load download report from API: {e}")

# TAB 2: INTERACTIVE COPILOT CHATBOT
with tab_chat:
    if not st.session_state.pipeline_results:
        st.info("👈 Please load data and execute the simulation pipeline in the sidebar first to activate the chatbot context.")
    else:
        st.write("### 💬 StockSentinel Logistics Copilot")
        st.write("Ask follow-up questions about out-of-stock causes, trace data, or step-by-step SAP ME21N/ME22N instructions.")
        st.divider()
        
        # Display chat history
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
        # Handle new user input
        if user_prompt := st.chat_input("Enter your question..."):
            # Add to local state
            st.session_state.chat_history.append({"role": "user", "content": user_prompt})
            
            # Display immediately
            with st.chat_message("user"):
                st.write(user_prompt)
                
            # Send message to backend FastAPI `/api/chat`
            with st.chat_message("assistant"):
                with st.spinner("Consulting Supply Chain diagnostics..."):
                    try:
                        # Extract pipeline context for LLM grounding
                        api_context = {
                            "oos_risks": st.session_state.pipeline_results.get("oos_risks", []),
                            "rca_results": st.session_state.pipeline_results.get("rca_results", []),
                            "mitigation_results": st.session_state.pipeline_results.get("mitigation_results", [])
                        }
                        
                        # Format payload
                        history_payload = []
                        for m in st.session_state.chat_history[:-1]: # exclude current user prompt
                            history_payload.append({"role": m["role"], "content": m["content"]})
                            
                        payload = {
                            "message": user_prompt,
                            "history": history_payload,
                            "context": api_context
                        }
                        
                        r = requests.post(f"{API_BASE_URL}/api/chat", json=payload)
                        if r.status_code == 200:
                            reply = r.json().get("response", "I could not generate a response.")
                            st.write(reply)
                            # Save response to history
                            st.session_state.chat_history.append({"role": "assistant", "content": reply})
                        else:
                            st.error(f"Error from API backend: {r.text}")
                    except Exception as e:
                        st.error(f"Failed to query backend API: {e}")
