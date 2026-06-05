import os
import streamlit as st
import requests
import pandas as pd
import json

# Setup page layout
st.set_page_config(
    page_title="StockSentinel - Multi-Agent Supply Chain Copilot",
    page_icon="🛡️",
    layout="wide",
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
        background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
        color: white;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
        position: relative;
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
    
    /* Metric Cards */
    .metric-card {
        background-color: white;
        border-radius: 10px;
        padding: 1.25rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        border-top: 4px solid #2c3e50;
        text-align: center;
        transition: transform 0.2s;
        margin-bottom: 1rem;
    }
    .metric-card:hover {
        transform: translateY(-2px);
    }
    .metric-label {
        font-size: 0.8rem;
        font-weight: 600;
        color: #718096;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.35rem;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #2C3E50;
    }
    
    /* Custom severity tags */
    .badge {
        padding: 4px 10px;
        border-radius: 15px;
        font-weight: 600;
        font-size: 0.8rem;
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
        border-left: 4px solid #2980b9;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 1rem;
        font-size: 0.95rem;
        color: #2c3e50;
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
st.sidebar.markdown("<h2 style='text-align: center; color: #2c3e50;'>StockSentinel 🛡️</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='text-align: center; font-style: italic; font-size: 0.85rem;'>Multi-Agent Supply Chain Copilot</p>", unsafe_allow_html=True)
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

st.sidebar.divider()

# Automated Pipeline Trigger
st.sidebar.subheader("Integrated Data Actions")
st.sidebar.write("Data is loaded automatically in the background from the central supply chain database.")

run_btn = st.sidebar.button("Execute Supply Chain Audits", use_container_width=True, disabled=(health is None))

st.sidebar.divider()
st.sidebar.markdown(
    "<div style='font-size: 0.8rem; color:#718096; text-align: center;'>"
    "StockSentinel Engine v2.0 • Decoupled Microservices"
    "</div>", 
    unsafe_allow_html=True
)

# Header Banner
st.markdown("""
<div class="title-banner">
    <h1>StockSentinel 🛡️</h1>
    <p>Multi-Agent Supply Chain Copilot analyzing stockout risks, demand forecasts, and safety stock levels.</p>
</div>
""", unsafe_allow_html=True)

# Initialize Session State
if "pipeline_results" not in st.session_state:
    st.session_state.pipeline_results = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Triggers pipeline run
if run_btn:
    with st.spinner("Loading background database, executing simulations, and auditing KPIs..."):
        try:
            response = requests.post(f"{API_BASE_URL}/api/run-pipeline")
            if response.status_code == 200:
                res_data = response.json()
                st.session_state.pipeline_results = res_data
                st.success("Supply chain audits and simulations executed successfully!")
                
                # Auto-initialize Chatbot introduction message
                oos_count = len(res_data.get("oos_risks", []))
                init_msg = (
                    f"Hi! I am the StockSentinel Supply Chain Copilot. I have completed the audits.\n\n"
                    f"- I detected **{oos_count} out-of-stock risk(s)** in the upcoming 12 weeks.\n"
                    f"- I calculated forecast error rates (MAPE & Bias) for all items.\n"
                    f"- I optimized safety stocks and replenishment parameters (EOQ) based on actual sales variability.\n\n"
                    "How can I assist you with demand forecasting, safety stock parameters, or stockout mitigations today?"
                )
                st.session_state.chat_history = [{"role": "assistant", "content": init_msg}]
            else:
                st.error(f"Error from API backend: {response.text}")
        except Exception as e:
            st.error(f"Failed to connect to API backend: {e}")

# Application Main Tabs
tab_oos, tab_forecast, tab_inventory, tab_chat = st.tabs([
    "🚨 OOS Risks & Actions", 
    "📈 Demand Forecast Auditor", 
    "⚙️ Inventory Optimization", 
    "💬 Interactive Chat Copilot"
])

# If pipeline has not been executed, display intro messages
if not st.session_state.pipeline_results:
    intro_text = "👈 Please click 'Execute Supply Chain Audits' in the sidebar to load database parameters and analyze metrics."
    with tab_oos: st.info(intro_text)
    with tab_forecast: st.info(intro_text)
    with tab_inventory: st.info(intro_text)
    with tab_chat: st.info(intro_text)
else:
    results = st.session_state.pipeline_results
    oos_risks = results.get("oos_risks", [])
    rca_results = results.get("rca_results", [])
    mitigation_results = results.get("mitigation_results", [])
    forecast_audit = results.get("forecast_audit_results", [])
    inventory_opt = results.get("inventory_optimization_results", [])
    
    # ------------------ TAB 1: OOS RISKS ------------------
    with tab_oos:
        st.subheader("OOS Risks Dashboard")
        
        # OOS summary metrics
        high_severity = sum(1 for r in oos_risks if r.get("Severity_Level") == "High")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>OOS Risks Detected</div><div class='metric-value'>{len(oos_risks)}</div></div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>High Severity Risks</div><div class='metric-value' style='color: #9B2C2C;'>{high_severity}</div></div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Mitigation Cost Impact</div><div class='metric-value'>${sum(m.get('Estimated_Cost_USD', 0.0) for m in mitigation_results):,.2f}</div></div>", unsafe_allow_html=True)
            
        if not oos_risks:
            st.success("No stockout risks detected in the horizon!")
        else:
            df_risks = pd.DataFrame(oos_risks)
            df_risks["Stockout_Probability"] = df_risks["Stockout_Probability"].map(lambda x: f"{x * 100:.1f}%")
            st.dataframe(df_risks[["SKU", "DC", "Week_of_OOS", "Weeks_Until_OOS", "Current_Stock", "Projected_Stock_on_OOS_Date", "Stockout_Probability", "Severity_Level"]], use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("🔍 Deep-Dive Diagnostics & Mitigation Plans")
            sku_sel = st.selectbox("Select SKU to Review Diagnostics", df_risks["SKU"].unique(), key="oos_sku_select")
            
            rca_rep = next((r for r in rca_results if r["SKU"] == sku_sel), None)
            mit_rep = next((m for m in mitigation_results if m["SKU"] == sku_sel), None)
            
            c1, c2 = st.columns(2)
            with c1:
                if rca_rep:
                    st.markdown("#### 🏷️ Root Cause Analysis (RCA)")
                    st.write(f"**Primary Cause:** `{rca_rep.get('Primary_Root_Cause')}`")
                    st.write(f"**Secondary Factors:** *{rca_rep.get('Secondary_Factors')}*")
                    st.markdown("##### Expert Narrative Reason:")
                    st.markdown(f"<div class='detail-card'>{rca_rep.get('Narrative_Reasoning')}</div>", unsafe_allow_html=True)
            with c2:
                if mit_rep:
                    st.markdown("#### 🛠️ Planner Mitigation Directive")
                    st.write(f"**Action Plan:** `{mit_rep.get('Recommended_Action')}`")
                    st.write(f"**Estimated Cost:** `${mit_rep.get('Estimated_Cost_USD'):,.2f}` | **Units Impacted:** `{mit_rep.get('Inventory_Impact_Units'):,}`")
                    st.markdown("##### ERP Planner Checklist:")
                    st.markdown(mit_rep.get('Action_Steps'))

    # ------------------ TAB 2: FORECAST AUDITING ------------------
    with tab_forecast:
        st.subheader("Demand Forecasting Accuracy Audit")
        
        # Compute average MAPE
        df_fa = pd.DataFrame(forecast_audit)
        df_fa_clean = df_fa.copy()
        df_fa_clean["MAPE_Float"] = df_fa_clean["MAPE"].str.replace("%", "").astype(float)
        avg_mape = df_fa_clean["MAPE_Float"].mean()
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Avg Forecast Error (MAPE)</div><div class='metric-value'>{avg_mape:.1f}%</div></div>", unsafe_allow_html=True)
        with c2:
            under_fore = sum(1 for f in forecast_audit if f.get("Forecast_Status") == "Under-forecasting")
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Under-forecasting Items</div><div class='metric-value' style='color: #9C4221;'>{under_fore}</div></div>", unsafe_allow_html=True)
        with c3:
            over_fore = sum(1 for f in forecast_audit if f.get("Forecast_Status") == "Over-forecasting")
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Over-forecasting Items</div><div class='metric-value'>{over_fore}</div></div>", unsafe_allow_html=True)
            
        st.dataframe(df_fa[["SKU", "DC", "MAPE", "Bias", "Forecast_Status"]], use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("🔍 Statistical Error Analysis")
        sku_fa_sel = st.selectbox("Select SKU to Review Forecast Audit", df_fa["SKU"].unique(), key="fa_sku_select")
        fa_rep = next((f for f in forecast_audit if f["SKU"] == sku_fa_sel), None)
        
        if fa_rep:
            cf1, cf2 = st.columns(2)
            with cf1:
                st.markdown("#### 📏 Error Analysis")
                st.markdown(f"##### Mean Absolute Percentage Error (MAPE):")
                st.markdown(f"<div class='detail-card'>{fa_rep.get('MAPE_Analysis')}</div>", unsafe_allow_html=True)
                st.markdown(f"##### Forecast Bias:")
                st.markdown(f"<div class='detail-card'>{fa_rep.get('Bias_Analysis')}</div>", unsafe_allow_html=True)
            with cf2:
                st.markdown("#### 💡 Suggested Forecast Revision")
                st.markdown(f"**Recommended Adjustments:**")
                st.markdown(f"<div class='detail-card' style='border-left-color: #27ae60;'>{fa_rep.get('Suggested_Action')}</div>", unsafe_allow_html=True)

    # ------------------ TAB 3: INVENTORY OPTIMIZATION ------------------
    with tab_inventory:
        st.subheader("Safety Stock & Parameter Optimization")
        
        df_io = pd.DataFrame(inventory_opt)
        df_io_clean = df_io.copy()
        df_io_clean["Turns_Float"] = df_io_clean["Stock_Turn_Rate"].astype(float)
        avg_turns = df_io_clean["Turns_Float"].mean()
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Avg Stock Turn Rate</div><div class='metric-value'>{avg_turns:.2f} turns/yr</div></div>", unsafe_allow_html=True)
        with c2:
            curr_ss_total = df_io_clean["Current_Safety_Stock"].sum()
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Current Safety Stock (Total)</div><div class='metric-value'>{curr_ss_total:,} units</div></div>", unsafe_allow_html=True)
        with c3:
            opt_ss_total = df_io_clean["Optimal_Safety_Stock"].sum()
            st.markdown(f"<div class='metric-card'><div class='metric-label'>Optimal Safety Stock (Total)</div><div class='metric-value' style='color:#27ae60;'>{opt_ss_total:,} units</div></div>", unsafe_allow_html=True)
            
        st.dataframe(df_io[["SKU", "DC", "Current_Safety_Stock", "Optimal_Safety_Stock", "Current_Reorder_Point", "Optimal_Reorder_Point", "Optimal_EOQ", "Stock_Turn_Rate"]], use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("🔍 Parametric Master Data Optimizations")
        sku_io_sel = st.selectbox("Select SKU to Review Parameters", df_io["SKU"].unique(), key="io_sku_select")
        io_rep = next((i for i in inventory_opt if i["SKU"] == sku_io_sel), None)
        
        if io_rep:
            cio1, cio2 = st.columns(2)
            with cio1:
                st.markdown("#### 📐 Statistical Modeling Analysis")
                st.markdown(f"##### Safety Stock & Volatility Buffer:")
                st.markdown(f"<div class='detail-card'>{io_rep.get('Safety_Stock_Analysis')}</div>", unsafe_allow_html=True)
                st.markdown(f"##### Replenishment Cycle & EOQ Analysis:")
                st.markdown(f"<div class='detail-card'>{io_rep.get('Replenishment_Analysis')}</div>", unsafe_allow_html=True)
                st.markdown(f"##### Inventory Turnover Evaluation:")
                st.markdown(f"<div class='detail-card'>{io_rep.get('Stock_Turn_Analysis')}</div>", unsafe_allow_html=True)
            with cio2:
                st.markdown("#### ⚙️ ERP Parameter Update Instructions")
                st.markdown("**Instructions to apply adjustments (SAP MM02):**")
                st.markdown(io_rep.get('ERP_Directives'))
                
        # Consolidated Excel Download button
        st.divider()
        st.subheader("📥 Download Analysis Excel Sheet")
        try:
            r = requests.get(f"{API_BASE_URL}/api/download")
            if r.status_code == 200:
                st.download_button(
                    label="Download oos_analysis_report.xlsx",
                    data=r.content,
                    file_name="oos_analysis_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        except Exception:
            pass

    # ------------------ TAB 4: CHAT COPILOT ------------------
    with tab_chat:
        st.write("### 💬 StockSentinel Supply Chain Copilot")
        st.write("Ask questions about MAPE forecast errors, optimal safety stocks, supplier lead times, or stockout resolutions.")
        st.divider()
        
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])
                
        if user_prompt := st.chat_input("Ask the supply chain copilot..."):
            st.session_state.chat_history.append({"role": "user", "content": user_prompt})
            
            with st.chat_message("user"):
                st.write(user_prompt)
                
            with st.chat_message("assistant"):
                with st.spinner("Querying backend copilot team..."):
                    try:
                        api_context = {
                            "oos_risks": oos_risks,
                            "rca_results": rca_results,
                            "mitigation_results": mitigation_results,
                            "forecast_audit_results": forecast_audit,
                            "inventory_optimization_results": inventory_opt
                        }
                        
                        history_payload = []
                        for m in st.session_state.chat_history[:-1]:
                            history_payload.append({"role": m["role"], "content": m["content"]})
                            
                        payload = {
                            "message": user_prompt,
                            "history": history_payload,
                            "context": api_context
                        }
                        
                        r = requests.post(f"{API_BASE_URL}/api/chat", json=payload)
                        if r.status_code == 200:
                            reply = r.json().get("response", "Could not calculate response.")
                            st.write(reply)
                            st.session_state.chat_history.append({"role": "assistant", "content": reply})
                        else:
                            st.error(f"Error from API backend: {r.text}")
                    except Exception as e:
                        st.error(f"Failed to query backend API: {e}")
