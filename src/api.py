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
from src.config import OPENAI_API_KEY

app = FastAPI(
    title="StockSentinel - Decoupled Multi-Agent Supply Chain Server",
    description="Backend microservice that exposes inventory simulation, forecasting error audits, and replenishment optimizations.",
    version="2.0.0"
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

class SupplyChainCopilotAgent(BaseAgent):
    """Primary chat interface routing queries to OOS, Forecasting, and Inventory sub-specialists."""
    
    def __init__(self):
        super().__init__(name="SupplyChainCopilot", role="Generic Supply Chain Management Expert & Coordinator")
        
    def get_copilot_response(self, request: ChatRequest) -> str:
        """Processes user message by reviewing complete multi-agent operational records."""
        oos_risks = request.context.get("oos_risks", [])
        rca_results = request.context.get("rca_results", [])
        mitigation_results = request.context.get("mitigation_results", [])
        forecast_audit = request.context.get("forecast_audit_results", [])
        inventory_opt = request.context.get("inventory_optimization_results", [])
        
        # 1. Deterministic Fallback if LLM is offline
        if not self.is_available():
            return self._get_offline_copilot_fallback(request.message, oos_risks, rca_results, mitigation_results, forecast_audit, inventory_opt)
            
        # 2. Cognitive LLM prompt containing all operational data views
        system_prompt = (
            "You are StockSentinel Copilot, a master supply chain director and expert consultant.\n"
            "You help planning managers optimize stock levels, evaluate forecasting accuracy, diagnose stockouts, and implement parameters.\n\n"
            "Here is the current operational data from the multi-agent supply chain team:\n\n"
            f"1. PREDICTED OUT-OF-STOCK (OOS) INCIDENTS:\n{oos_risks}\n"
            f"   Root Causes (RCA): {rca_results}\n"
            f"   Planner Mitigations: {mitigation_results}\n\n"
            f"2. FORECASTING AUDIT DATA (MAPE/Bias):\n{forecast_audit}\n\n"
            f"3. INVENTORY PARAMETERS OPTIMIZATION (Safety Stock/ROP/EOQ/Turns):\n{inventory_opt}\n\n"
            "INSTRUCTIONS:\n"
            "- You can answer questions on OOS, Forecasting, Safety Stock, EOQ, Inventory Turnover, and master parameters.\n"
            "- Be concise, direct, and data-driven. Reference specific values, SKU codes, and weeks from the context.\n"
            "- Specify direct ERP transaction codes (e.g. SAP MM02 for updating parameters, ME21N for placing POs, ME22N for changes, MB1B for STO stock transfers) where applicable.\n"
            "- If the question is about something not in the context, guide the planner using best-practice supply chain modeling principles.\n"
            "- Format your response using clean Markdown headers, bullet points, checklists, or tables."
        )
        
        history_msgs = []
        for msg in request.history[-5:]:
            history_msgs.append(f"{msg.role.upper()}: {msg.content}")
        history_str = "\n".join(history_msgs)
        
        user_prompt = (
            f"CONVERSATION HISTORY:\n{history_str}\n\n"
            f"USER QUERY: {request.message}\n\n"
            "Please generate your professional supply chain consultant response:"
        )
        
        try:
            return self.call_llm(system_prompt, user_prompt, json_mode=False)
        except Exception as e:
            return f"I ran into an error communicating with OpenAI: {e}. However, the background simulation completed successfully."

    def _get_offline_copilot_fallback(self, query: str, oos_risks: list, rca_results: list, mitigation_results: list, forecast_audit: list, inventory_opt: list) -> str:
        """Structured text generator when backend is offline."""
        q = query.lower()
        
        # General Status
        if "summary" in q or "status" in q or "risk" in q or "hello" in q or "hi" in q:
            summary = (
                "👋 Hello! Running in **Offline Heuristic Mode**.\n\n"
                "Here is an overview of your supply chain parameters:\n"
            )
            summary += f"- **OOS Risks**: {len(oos_risks)} incidents flagged.\n"
            
            # Avg MAPE
            if forecast_audit:
                mapes = [float(f["MAPE"].replace("%", "")) for f in forecast_audit]
                avg_mape = sum(mapes) / len(mapes)
                summary += f"- **Forecast Quality**: Average MAPE is **{avg_mape:.1f}%**.\n"
                
            # Avg Turns
            if inventory_opt:
                turns = [float(i["Stock_Turn_Rate"]) for i in inventory_opt]
                avg_turns = sum(turns) / len(turns)
                summary += f"- **Inventory Turnover**: Average Turn Rate is **{avg_turns:.2f} turns/year**.\n"
                
            summary += "\nAsk me about a specific SKU (e.g., 'tell me about SKU-001') to see deep audit results for OOS, Forecasting, and Safety Stock!"
            return summary
            
        # SKU Drill-down
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

# Instantiate copilot agent
copilot_agent = SupplyChainCopilotAgent()

@app.get("/api/health")
def health_check():
    """Checks the database file existence and LLM API connectivity."""
    db_exists = os.path.exists(DB_PATH)
    return {
        "status": "healthy" if db_exists else "degraded",
        "database_online": db_exists,
        "llm_online": copilot_agent.is_available(),
        "model": copilot_agent.model
    }

@app.post("/api/run-pipeline")
def run_pipeline():
    """Reads background supply chain database, executes multi-agent simulation and audit loops, and saves styled excel report."""
    if not os.path.exists(DB_PATH):
        raise HTTPException(
            status_code=404, 
            detail=f"Supply chain database not found at '{DB_PATH}'. Please run python data/generate_database.py first."
        )
        
    try:
        # 1. Load inputs
        handler = ExcelHandler(DB_PATH)
        inputs = handler.load_inputs()
        
        df_sku = inputs["SKU_Metadata"]
        df_inventory = inputs["Inventory_Status"]
        df_demand = inputs["Demand_Forecast"]
        df_pipeline = inputs["Supply_Pipeline"]
        df_history = inputs["Historical_Sales"]
        
        # 2. Demand Forecast Auditing
        demand_agent = DemandForecasterAgent()
        df_adjusted_demand = demand_agent.forecast_weekly_demand(df_demand)
        
        # 3. Run Inventory Simulation (OOS Risks)
        sim_agent = InventorySimulationAgent()
        oos_risks, simulation_traces = sim_agent.simulate_inventory(
            df_sku, df_inventory, df_adjusted_demand, df_pipeline
        )
        
        # 4. OOS Risk Diagnostics
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
            
        # 5. Forecasting Audit (MAPE & Bias calculation)
        forecasting_agent = ForecastingAuditorAgent()
        audit_data = forecasting_agent.audit_forecasts(df_history)
        
        forecast_audit_results = []
        for (sku, dc), audit in audit_data.items():
            audit_narrative = forecasting_agent.generate_forecast_narrative(sku, dc, audit_data, df_history)
            forecast_audit_results.append(audit_narrative)
            
        # 6. Inventory Optimization (Optimal safety stocks & EOQ)
        optimizer_agent = InventoryOptimizerAgent()
        opt_data = optimizer_agent.optimize_inventory(df_sku, df_inventory, df_history, service_level=0.95)
        
        inventory_optimization_results = []
        for (sku, dc), opt in opt_data.items():
            opt_narrative = optimizer_agent.generate_optimization_narrative(sku, dc, opt_data)
            inventory_optimization_results.append(opt_narrative)
            
        # 7. Write consolidated styled excel report
        handler.write_analysis_report(
            REPORT_PATH,
            inputs,
            oos_risks,
            rca_results,
            mitigation_results,
            forecast_audit_results,
            inventory_optimization_results
        )
        
        return {
            "success": True,
            "oos_risks": oos_risks,
            "rca_results": rca_results,
            "mitigation_results": mitigation_results,
            "forecast_audit_results": forecast_audit_results,
            "inventory_optimization_results": inventory_optimization_results
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Pipeline execution error: {str(e)}")

@app.get("/api/download")
def download_report():
    """Serves the generated oos_analysis_report.xlsx report spreadsheet."""
    if not os.path.exists(REPORT_PATH):
        raise HTTPException(status_code=404, detail="No report has been compiled yet. Please run the pipeline first.")
    return FileResponse(
        path=REPORT_PATH,
        filename="oos_analysis_report.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.post("/api/chat")
def chat_copilot(request: ChatRequest):
    """Queries the SupplyChainCopilotAgent to get interactive recommendations and diagnostics."""
    try:
        response = copilot_agent.get_copilot_response(request)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")
