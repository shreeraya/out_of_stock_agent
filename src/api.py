import os
import shutil
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.orchestrator import StockSentinelOrchestrator
from src.agents.base_agent import BaseAgent
from src.config import OPENAI_API_KEY

app = FastAPI(
    title="StockSentinel API",
    description="Decoupled API Backend for multi-agent supply chain OOS prediction and chatbot assistance.",
    version="1.0.0"
)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_headers=["*"],
    allow_methods=["*"],
)

# Paths for temporary analysis files
TEMP_INPUT_PATH = "temp_input.xlsx"
TEMP_OUTPUT_PATH = "temp_output.xlsx"

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage]
    context: Dict[str, Any]

class ChatCopilotAgent(BaseAgent):
    """Specialized chatbot copilot that leverages BaseAgent to answer user queries using pipeline results."""
    def __init__(self):
        super().__init__(name="ChatCopilot", role="Interactive Supply Chain Planner Assistant")

    def get_chat_response(self, request: ChatRequest) -> str:
        """Generates a contextual chat response using the LLM (or fallback offline heuristics)."""
        # Format the context details
        oos_risks = request.context.get("oos_risks", [])
        rca_results = request.context.get("rca_results", [])
        mitigation_results = request.context.get("mitigation_results", [])
        
        # 1. Fallback Offline Logic if LLM is unavailable
        if not self.is_available():
            return self._get_offline_chat_fallback(request.message, oos_risks, rca_results, mitigation_results)
            
        # 2. Cognitive LLM Logic
        system_prompt = (
            "You are StockSentinel Copilot, an expert AI Supply Chain consultant and Logistics Director.\n"
            "Your goal is to help Supply Planners understand simulated inventory traces, root causes of predicted out-of-stocks, and carry out mitigation instructions.\n\n"
            "You have access to the current simulation's data context:\n"
            f"- Predicted OOS Risks: {oos_risks}\n"
            f"- Root Cause Analysis (RCA): {rca_results}\n"
            f"- Recommended Mitigations: {mitigation_results}\n\n"
            "INSTRUCTIONS:\n"
            "1. Be direct, professional, and actionable. Avoid excessive pleasantries.\n"
            "2. Refer to specific SKU codes, DC locations, OOS Weeks, costs, and ERP transaction names (e.g. SAP ME21N, ME22N, MB1B, MM02) when giving answers based on the context.\n"
            "3. If the user asks about a SKU or data not in the current context, explain that it is not present in the current simulation, but guide them using general supply chain planning principles.\n"
            "4. Keep your answers formatting clean and readable using standard markdown checklist task-lists, bullet points, or tables where appropriate."
        )
        
        # Build chat history context
        history_msgs = []
        for msg in request.history[-5:]: # Keep last 5 messages for conversation context
            history_msgs.append(f"{msg.role.upper()}: {msg.content}")
        history_str = "\n".join(history_msgs)
        
        user_prompt = (
            f"CONVERSATION HISTORY:\n{history_str}\n\n"
            f"USER QUERY: {request.message}\n\n"
            "Please analyze the query with respect to the supply chain context above, and draft your expert response:"
        )
        
        try:
            # Call LLM in text mode (json_mode=False)
            response = self.call_llm(system_prompt, user_prompt, json_mode=False)
            return response
        except Exception as e:
            return f"I encountered an error trying to process your request via OpenAI: {e}. However, based on the local simulation, I detected {len(oos_risks)} out-of-stock risk(s) in the horizon."

    def _get_offline_chat_fallback(self, query: str, oos_risks: list, rca_results: list, mitigation_results: list) -> str:
        """Local rule-based response generator when offline."""
        q = query.lower()
        
        # Summarize general status
        if "summary" in q or "status" in q or "risk" in q or "hello" in q or "hi" in q:
            if not oos_risks:
                return "👋 Hello! Running in **Offline Fallback Mode**. No out-of-stock risks were detected in the simulation. Your inventory is healthy."
            
            summary = f"👋 Hello! Running in **Offline Fallback Mode** (OpenAI API key missing).\n\n"
            summary += f"I have detected **{len(oos_risks)} out-of-stock risk(s)** in the 12-week horizon:\n"
            for risk in oos_risks:
                summary += f"- **{risk['SKU']}** at **{risk['DC']}** during week **{risk['Week_of_OOS']}** (Severity: **{risk['Severity_Level']}**)\n"
            summary += "\nAsk me about a specific SKU (e.g. 'tell me about SKU-003') to see root causes and action steps!"
            return summary
            
        # SKU Specific query
        for sku in ["sku-001", "sku-002", "sku-003", "sku-004", "sku-005"]:
            if sku in q:
                sku_upper = sku.upper()
                rca = next((r for r in rca_results if r["SKU"] == sku_upper), None)
                mit = next((m for m in mitigation_results if m["SKU"] == sku_upper), None)
                
                if not rca:
                    return f"No stockout risk was detected for SKU **{sku_upper}** in the simulation."
                
                response = f"### Diagnostics for {sku_upper} ({rca.get('DC', 'N/A')}):\n"
                response += f"- **Week of OOS**: {rca.get('Week_of_OOS', 'N/A')} (in {rca.get('Weeks_Until_OOS', 0)} weeks)\n"
                response += f"- **Primary Root Cause**: {rca.get('Primary_Root_Cause', 'N/A')}\n"
                response += f"- **Secondary Factors**: {rca.get('Secondary_Factors', 'N/A')}\n\n"
                
                if mit:
                    response += f"### Mitigation Recommendations:\n"
                    response += f"- **Action Plan**: {mit.get('Recommended_Action', 'N/A')}\n"
                    response += f"- **Estimated Cost**: ${mit.get('Estimated_Cost_USD', 0.0):,.2f}\n"
                    response += f"- **Inventory Impact**: {mit.get('Inventory_Impact_Units', 0)} units\n\n"
                    response += f"**Action Steps to Execute:**\n{mit.get('Action_Steps', 'N/A')}"
                return response
                
        return "I am currently running in **Offline Fallback Mode**. You can ask me to 'summarize' risks, or request diagnostics on a specific SKU (e.g. 'tell me about SKU-003')."

# Instantiate chat copilot agent
chat_agent = ChatCopilotAgent()

@app.get("/api/health")
def health_check():
    """Checks the health and OpenAI API connectivity of the backend."""
    return {
        "status": "healthy",
        "llm_online": chat_agent.is_available(),
        "model_configured": chat_agent.model
    }

@app.post("/api/run-pipeline")
async def run_pipeline(file: UploadFile = File(...)):
    """Receives an uploaded Excel sheet, runs the StockSentinel pipeline, and returns JSON diagnostics."""
    try:
        # Save uploaded file
        with open(TEMP_INPUT_PATH, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Initialize Orchestrator and run pipeline
        orchestrator = StockSentinelOrchestrator(
            input_path=TEMP_INPUT_PATH,
            output_path=TEMP_OUTPUT_PATH
        )
        oos_risks, rca_results, mitigation_results = orchestrator.run_pipeline()
        
        return {
            "success": True,
            "oos_risks": oos_risks,
            "rca_results": rca_results,
            "mitigation_results": mitigation_results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution error: {str(e)}")

@app.get("/api/download")
def download_report():
    """Serves the generated oos_analysis_report.xlsx report spreadsheet."""
    if not os.path.exists(TEMP_OUTPUT_PATH):
        raise HTTPException(status_code=404, detail="No report has been compiled yet. Please run the pipeline first.")
    return FileResponse(
        path=TEMP_OUTPUT_PATH,
        filename="oos_analysis_report.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.post("/api/chat")
def chat_copilot(request: ChatRequest):
    """Queries the ChatCopilotAgent to get interactive recommendations and diagnostics."""
    try:
        response = chat_agent.get_chat_response(request)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")
