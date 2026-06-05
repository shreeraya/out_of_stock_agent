import os
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.utils.excel_handler import ExcelHandler
from src.agents.demand_agent import DemandForecasterAgent
from src.agents.inventory_agent import InventorySimulationAgent
from src.agents.rca_agent import RootCauseAnalyzerAgent
from src.agents.mitigation_agent import MitigationAdvisorAgent
from src.agents.forecasting_agent import ForecastingAuditorAgent
from src.agents.inventory_optimizer_agent import InventoryOptimizerAgent
from src.agents.base_agent import BaseAgent

app = FastAPI(
    title="Supply Chain Sentinel API",
    description="Backend coordinator exposing multi-agent forecasting, inventory optimization, and stockout diagnostics.",
    version="3.0.0"
)

# CORS middleware for stream UI connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)

# Centralized DB Paths
DB_PATH = os.path.join("data", "supply_chain_db.xlsx")
REPORT_PATH = "oos_analysis_report.xlsx"

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage]
    context: Dict[str, Any]

# In-Memory Cache for Audited Supply Chain Reports
PIPELINE_CACHE = None

def get_pipeline_data():
    """Warms up or returns the pre-cached pipeline results."""
    global PIPELINE_CACHE
    if PIPELINE_CACHE is not None:
        return PIPELINE_CACHE
        
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database template not found at {DB_PATH}. Please run generator first.")
        
    print("[INFO] Cache empty. Executing full supply chain pipeline run in background...")
    handler = ExcelHandler(DB_PATH)
    inputs = handler.load_inputs()
    
    df_sku = inputs["SKU_Metadata"]
    df_inventory = inputs["Inventory_Status"]
    df_demand = inputs["Demand_Forecast"]
    df_pipeline = inputs["Supply_Pipeline"]
    df_history = inputs["Historical_Sales"]
    
    # 1. Demand Forecast Auditing
    demand_agent = DemandForecasterAgent()
    df_adjusted_demand = demand_agent.forecast_weekly_demand(df_demand)
    
    # 2. Run Inventory Simulation (OOS Risks)
    sim_agent = InventorySimulationAgent()
    oos_risks, simulation_traces = sim_agent.simulate_inventory(
        df_sku, df_inventory, df_adjusted_demand, df_pipeline
    )
    
    # 3. OOS Diagnostics (RCA & Mitigations)
    rca_agent = RootCauseAnalyzerAgent()
    mit_agent = MitigationAdvisorAgent()
    rca_results = []
    mitigation_results = []
    
    for risk in oos_risks:
        sku = risk["SKU"]
        dc = risk["DC"]
        trace = simulation_traces.get((sku, dc))
        sku_meta = df_sku[df_sku["SKU"] == sku].to_dict(orient="records")[0]
        inv_status = df_inventory[(df_inventory["SKU"] == sku) & (df_inventory["DC"] == dc)].to_dict(orient="records")[0]
        pipeline_orders = df_pipeline[(df_pipeline["SKU"] == sku) & (df_pipeline["DC"] == dc)].to_dict(orient="records") if not df_pipeline.empty else []
        
        rca_rep = rca_agent.diagnose_stockout(risk, trace, sku_meta, inv_status, pipeline_orders)
        rca_results.append(rca_rep)
        
        mit_rep = mit_agent.formulate_mitigation(rca_rep, df_inventory, df_sku, pipeline_orders)
        mitigation_results.append(mit_rep)
        
    # 4. Forecasting Audit (MAPE & Bias calculation)
    forecasting_agent = ForecastingAuditorAgent()
    audit_data = forecasting_agent.audit_forecasts(df_history)
    forecast_audit_results = []
    for (sku, dc), audit in audit_data.items():
        audit_narrative = forecasting_agent.generate_forecast_narrative(sku, dc, audit_data, df_history)
        forecast_audit_results.append(audit_narrative)
        
    # 5. Inventory Parameter Optimization (Optimal safety stocks & EOQ)
    optimizer_agent = InventoryOptimizerAgent()
    opt_data = optimizer_agent.optimize_inventory(df_sku, df_inventory, df_history, service_level=0.95)
    inventory_optimization_results = []
    for (sku, dc), opt in opt_data.items():
        opt_narrative = optimizer_agent.generate_optimization_narrative(sku, dc, opt_data)
        inventory_optimization_results.append(opt_narrative)
        
    # 6. Write consolidated styled excel report
    handler.write_analysis_report(
        REPORT_PATH,
        inputs,
        oos_risks,
        rca_results,
        mitigation_results,
        forecast_audit_results,
        inventory_optimization_results
    )
    
    PIPELINE_CACHE = {
        "oos_risks": oos_risks,
        "rca_results": rca_results,
        "mitigation_results": mitigation_results,
        "forecast_audit_results": forecast_audit_results,
        "inventory_optimization_results": inventory_optimization_results
    }
    print("[INFO] Pipeline run completed. Operational data cached.")
    return PIPELINE_CACHE

class SupplyChainSentinelCopilot(BaseAgent):
    """Primary routing copilot coordinating inquiries to specific specialized supply chain agents."""
    
    def __init__(self):
        super().__init__(name="SupplyChainSentinel", role="Generic Supply Chain Specialist & Coordinator")
        
    def get_copilot_response(self, request: ChatRequest) -> dict:
        """Determines query intent and triggers corresponding agent context."""
        message = request.message.lower()
        
        # Pull pre-cached diagnostics
        data = get_pipeline_data()
        oos_risks = data["oos_risks"]
        rca_results = data["rca_results"]
        mitigation_results = data["mitigation_results"]
        forecast_audit = data["forecast_audit_results"]
        inventory_opt = data["inventory_optimization_results"]
        
        # 1. Semantic router checks
        category = "general"
        if any(w in message for w in ["oos", "stockout", "out of stock", "run dry", "empty", "deplet", "mitigat", "expedite", "transfer", "po-"]):
            category = "oos"
        elif any(w in message for w in ["forecast", "mape", "bias", "accuracy", "error", "predict", "sale", "actual"]):
            category = "forecasting"
        elif any(w in message for w in ["safety stock", "rop", "reorder point", "turns", "turnover", "eoq", "parameter", "sap", "mm02"]):
            category = "inventory"
            
        print(f"[INFO] Semantic Router: User query '{request.message}' routed to '{category}' category.")
        
        # 2. Offline fallback mode check
        if not self.is_available():
            reply = self._get_offline_copilot_fallback(request.message, oos_risks, rca_results, mitigation_results, forecast_audit, inventory_opt)
            return {"response": reply, "agent_triggered": category}
            
        # 3. Create context-specific agent system prompts
        if category == "oos":
            print("[INFO] Triggering OOS Guard Agent Team...")
            system_prompt = (
                "You are the OOS Guard Agent of Supply Chain Sentinel.\n"
                "Your role is to answer user queries about predicted out-of-stock (OOS) risks, root causes of stockouts, and mitigation actions (such as expediting POs or transferring stock).\n\n"
                "Here is the context pulled by the OOS Guard Agent:\n"
                f"- OOS Risks: {oos_risks}\n"
                f"- Root Causes (RCA): {rca_results}\n"
                f"- Mitigations: {mitigation_results}\n\n"
                "Provide direct, concise answers. Cite specific dates, SKU codes, DC names, costs, and ERP transaction checklists (SAP ME22N, ME21N, MB1B)."
            )
        elif category == "forecasting":
            print("[INFO] Triggering ForecastingAuditorAgent...")
            system_prompt = (
                "You are the Forecasting Auditor Agent of Supply Chain Sentinel.\n"
                "Your role is to answer user queries about demand forecasting accuracy, Mean Absolute Percentage Error (MAPE), forecast Bias, and demand adjustments.\n\n"
                "Here is the context pulled by the Forecasting Auditor Agent:\n"
                f"- Forecast Audits: {forecast_audit}\n\n"
                "Analyze the accuracy. Explain MAPE and Bias clearly. Suggest planning revisions and forecast baseline modifications."
            )
        elif category == "inventory":
            print("[INFO] Triggering InventoryOptimizerAgent...")
            system_prompt = (
                "You are the Inventory Optimizer Agent of Supply Chain Sentinel.\n"
                "Your role is to answer user queries about safety stock, Economic Order Quantity (EOQ), reorder points (ROP), stock turns, and ERP parameters.\n\n"
                "Here is the context pulled by the Inventory Optimizer Agent:\n"
                f"- Optimized Parameters: {inventory_opt}\n\n"
                "Provide detailed parametric recommendations. Reference optimal Safety Stock, optimal ROP, EOQ, and Stock turns. Outline exact ERP SAP MM02 transaction instructions."
            )
        else:
            print("[INFO] Triggering general Coordinator Copilot...")
            system_prompt = (
                "You are the Supply Chain Sentinel Coordinator Copilot.\n"
                "Your role is to answer general supply chain questions and summarize the status across OOS, Forecasting, and Inventory pillars.\n\n"
                "Here is the summary context pulled from all agents:\n"
                f"- OOS Risks: {oos_risks}\n"
                f"- Forecast Audits: {forecast_audit}\n"
                f"- Inventory Optimizations: {inventory_opt}\n\n"
                "Provide a balanced, professional summary of the overall supply chain health."
            )
            
        history_msgs = []
        for msg in request.history[-5:]:
            history_msgs.append(f"{msg.role.upper()}: {msg.content}")
        history_str = "\n".join(history_msgs)
        
        user_prompt = (
            f"CONVERSATION HISTORY:\n{history_str}\n\n"
            f"USER QUERY: {request.message}\n\n"
            "Generate your expert response:"
        )
        
        try:
            reply = self.call_llm(system_prompt, user_prompt, json_mode=False)
            return {"response": reply, "agent_triggered": category}
        except Exception as e:
            return {"response": f"Error calling OpenAI API: {e}", "agent_triggered": category}

    def _get_offline_copilot_fallback(self, query: str, oos_risks: list, rca_results: list, mitigation_results: list, forecast_audit: list, inventory_opt: list) -> str:
        """Structured text generator when backend is offline."""
        q = query.lower()
        
        if "summary" in q or "status" in q or "risk" in q or "hello" in q or "hi" in q:
            summary = (
                "👋 Hello! Welcome to **Supply Chain Sentinel** (Running in Offline Heuristic Mode).\n\n"
                "Here is a quick overview of your current metrics:\n"
            )
            summary += f"- **OOS Risks**: {len(oos_risks)} incidents flagged.\n"
            
            if forecast_audit:
                mapes = [float(f["MAPE"].replace("%", "")) for f in forecast_audit]
                avg_mape = sum(mapes) / len(mapes)
                summary += f"- **Forecast Quality**: Average MAPE is **{avg_mape:.1f}%**.\n"
                
            if inventory_opt:
                turns = [float(i["Stock_Turn_Rate"]) for i in inventory_opt]
                avg_turns = sum(turns) / len(turns)
                summary += f"- **Inventory Turnover**: Average Turn Rate is **{avg_turns:.2f} turns/year**.\n"
                
            summary += "\nAsk me about a specific SKU (e.g., 'tell me about SKU-003') to see detailed parameters and diagnostics!"
            return summary
            
        for sku in ["sku-001", "sku-002", "sku-003", "sku-004", "sku-005"]:
            if sku in q:
                sku_upper = sku.upper()
                rca = next((r for r in rca_results if r["SKU"] == sku_upper), None)
                mit = next((m for m in mitigation_results if m["SKU"] == sku_upper), None)
                fa = next((f for f in forecast_audit if f["SKU"] == sku_upper), None)
                io = next((i for i in inventory_opt if i["SKU"] == sku_upper), None)
                
                response = f"### Supply Chain Audit for {sku_upper}:\n\n"
                
                if rca:
                    response += f"**1. Out-of-Stock (OOS) Risk:**\n"
                    response += f"- Flagged Week: {rca.get('Week_of_OOS')}\n"
                    response += f"- Primary Diagnosis: {rca.get('Primary_Root_Cause')}\n"
                    if mit:
                        response += f"- Mitigation Action: {mit.get('Recommended_Action')} (${mit.get('Estimated_Cost_USD'):.2f})\n\n"
                else:
                    response += f"**1. Out-of-Stock (OOS) Risk:** No risks detected in the 12-week horizon.\n\n"
                    
                if fa:
                    response += f"**2. Forecast Performance:**\n"
                    response += f"- MAPE: {fa.get('MAPE')} | Bias: {fa.get('Bias')}\n"
                    response += f"- Status: {fa.get('Forecast_Status')}\n"
                    response += f"- Suggested Planning Revision: {fa.get('Suggested_Action')}\n\n"
                    
                if io:
                    response += f"**3. Inventory Optimization:**\n"
                    response += f"- Optimal Safety Stock: {io.get('Optimal_Safety_Stock')} units (vs current {io.get('Current_Safety_Stock')})\n"
                    response += f"- Optimal Reorder Point: {io.get('Optimal_Reorder_Point')} units (vs current {io.get('Current_Reorder_Point')})\n"
                    response += f"- Turnover: {io.get('Stock_Turn_Rate')} turns/year\n\n"
                    response += f"**SAP Master Data Update (MM02):**\n"
                    response += f"1. In MRP 1 view, change Reorder Point to **{io.get('Optimal_Reorder_Point')}** units.\n"
                    response += f"2. In MRP 2 view, change Safety Stock to **{io.get('Optimal_Safety_Stock')}** units."
                    
                return response
                
        return "I am running in **Offline Mode**. Ask me to 'summarize' metrics, or request diagnostics on a specific SKU (e.g., 'safety stock for SKU-001')."

# Instantiate copilot
copilot = SupplyChainSentinelCopilot()

# Pre-caching will occur lazily on the first health check or chat query to avoid blocking Uvicorn startup.

@app.get("/api/health")
def health_check():
    """Checks the database file existence and LLM API connectivity."""
    db_exists = os.path.exists(DB_PATH)
    return {
        "status": "healthy" if db_exists else "degraded",
        "database_online": db_exists,
        "llm_online": copilot.is_available(),
        "model": copilot.model
    }

@app.post("/api/run-pipeline")
def run_pipeline():
    """Triggers and returns the cached/fresh supply chain audit results."""
    try:
        data = get_pipeline_data()
        return {
            "success": True,
            **data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/download")
def download_report():
    """Serves the generated oos_analysis_report.xlsx report spreadsheet."""
    if not os.path.exists(REPORT_PATH):
        raise HTTPException(status_code=404, detail="No report has been compiled yet.")
    return FileResponse(
        path=REPORT_PATH,
        filename="oos_analysis_report.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.post("/api/chat")
def chat_copilot(request: ChatRequest):
    """Routes and queries the appropriate specialized agent based on query intent."""
    try:
        res = copilot.get_copilot_response(request)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
