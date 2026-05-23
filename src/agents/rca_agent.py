import json
import pandas as pd
from src.agents.base_agent import BaseAgent

class RootCauseAnalyzerAgent(BaseAgent):
    """Cognitive agent that audits inventory simulation traces and supply parameters to diagnose the primary and secondary causes of stockouts."""
    
    def __init__(self):
        super().__init__(name="RootCauseAnalyzer", role="Supply Chain Root Cause Diagnostics Expert")
        
    def diagnose_stockout(self, oos_incident: dict, trace: pd.DataFrame, sku_meta: dict, inventory_status: dict, pipeline_orders: list) -> dict:
        """Diagnoses the root cause of an OOS event using LLM reasoning (with robust deterministic fallback if offline)."""
        sku = oos_incident["SKU"]
        dc = oos_incident["DC"]
        date_of_oos = oos_incident["Date_of_OOS"]
        days_until_oos = oos_incident["Days_Until_OOS"]
        
        # 1. Fallback Logic (Deterministic heuristics when OpenAI is offline)
        fallback_rca = self._get_deterministic_fallback(oos_incident, trace, sku_meta, inventory_status, pipeline_orders)
        
        if not self.is_available():
            return fallback_rca
            
        # 2. Cognitive LLM Logic
        system_prompt = (
            "You are a master Supply Chain RCA (Root Cause Analysis) Consultant.\n"
            "Your job is to analyze an upcoming Out-of-Stock (OOS) event and diagnose exactly why it is happening.\n"
            "You must categorize the primary root cause and provide a high-level narrative explanation that mentions key numbers (stock levels, dates, demands, lead times).\n"
            "Choose a primary root cause from one of these standard categories:\n"
            "- 'Promotional Demand Spike' (demand surged dramatically above average sales)\n"
            "- 'Supplier Lead-Time Delay' (outstanding PO is delayed or expected delivery date is too late)\n"
            "- 'Severe Initial Understocking' (stock was critically low/empty at the start of the horizon)\n"
            "- 'Low Reorder Point Parameter' (reorder point was set too low, triggering orders too late)\n"
            "- 'Under-ordering / Small Batch' (reorder quantity was insufficient to cover lead time demand)\n"
            "Respond ONLY with a JSON object containing:\n"
            "{\n"
            "  \"Primary_Root_Cause\": \"<category>\",\n"
            "  \"Secondary_Factors\": \"<short description of minor contributing factors>\",\n"
            "  \"Narrative_Reasoning\": \"<detailed expert narrative explaining how the numbers play out>\"\n"
            "}\n"
            "Respond in valid JSON only."
        )
        
        # Format input details for LLM
        timeline_str = trace[["Date", "Starting_Stock", "Demand", "Receipts", "Ending_Stock", "Trigger_Reorder"]].to_string(index=False)
        
        user_prompt = (
            f"DIAGNOSTIC CASE SHEET:\n"
            f"SKU: {sku} ({sku_meta.get('Description', 'N/A')})\n"
            f"DC: {dc}\n"
            f"Predicted OOS Date: {date_of_oos} (in {days_until_oos} days)\n"
            f"Current Stock: {inventory_status.get('Current_Stock_Units', 0)} units\n"
            f"Safety Stock: {inventory_status.get('Safety_Stock_Units', 0)} units\n"
            f"Reorder Point: {inventory_status.get('Reorder_Point_Units', 0)} units\n"
            f"Reorder Qty: {inventory_status.get('Reorder_Quantity_Units', 0)} units\n"
            f"Supplier Lead Time: {sku_meta.get('Lead_Time_Days', 0)} days\n"
            f"Outstanding Pipeline Orders: {json.dumps(pipeline_orders, indent=2)}\n\n"
            f"Daily Inventory Simulation Trace:\n"
            f"{timeline_str}\n\n"
            f"Based on this trace and parameters, please analyze the interaction of demand, lead time, safety stock, and pipeline receipts. "
            f"Identify why the inventory went negative and generate the diagnosis JSON."
        )
        
        try:
            raw_response = self.call_llm(system_prompt, user_prompt, json_mode=True)
            parsed = self.parse_json_response(raw_response)
            
            # Ensure correct format keys are present
            result = {
                "SKU": sku,
                "DC": dc,
                "Date_of_OOS": date_of_oos,
                "Days_Until_OOS": days_until_oos,
                "Primary_Root_Cause": parsed.get("Primary_Root_Cause", fallback_rca["Primary_Root_Cause"]),
                "Secondary_Factors": parsed.get("Secondary_Factors", fallback_rca["Secondary_Factors"]),
                "Narrative_Reasoning": parsed.get("Narrative_Reasoning", fallback_rca["Narrative_Reasoning"])
            }
            return result
        except Exception as e:
            print(f"[WARNING] LLM diagnosis failed for {sku} at {dc}. Using deterministic fallback. Error: {e}")
            return fallback_rca
            
    def _get_deterministic_fallback(self, oos_incident: dict, trace: pd.DataFrame, sku_meta: dict, inventory_status: dict, pipeline_orders: list) -> dict:
        """Deterministic heuristic fallback when LLM is unavailable."""
        sku = oos_incident["SKU"]
        dc = oos_incident["DC"]
        date_of_oos = oos_incident["Date_of_OOS"]
        days_until_oos = oos_incident["Days_Until_OOS"]
        
        curr_stock = int(inventory_status.get("Current_Stock_Units", 0))
        safety_stock = int(inventory_status.get("Safety_Stock_Units", 0))
        reorder_point = int(inventory_status.get("Reorder_Point_Units", 0))
        lead_time = int(sku_meta.get("Lead_Time_Days", 0))
        
        # Calculate daily averages
        avg_demand = trace["Demand"].mean()
        max_demand = trace["Demand"].max()
        
        # Check for delays
        delayed_po = False
        active_pipeline = False
        for po in pipeline_orders:
            if po.get("Status") == "Delayed":
                delayed_po = True
            if po.get("Status") in ["In Transit", "Placed", "Delayed"]:
                active_pipeline = True
                
        # Heuristics
        if days_until_oos <= 3 and curr_stock < safety_stock:
            primary = "Severe Initial Understocking"
            secondary = "Current stock was already critically below safety stock prior to simulation start."
            narrative = f"Inventory runs out immediately on Day {days_until_oos} because starting inventory ({curr_stock} units) is already critically below the safety stock threshold ({safety_stock} units) with no incoming shipments scheduled early enough."
            
        elif max_demand > 2.5 * avg_demand:
            primary = "Promotional Demand Spike"
            secondary = f"Daily demand peaked at {max_demand} units, which is {max_demand/avg_demand:.1f}x the baseline average."
            narrative = f"A significant spike in demand (peaking at {max_demand} units/day) depleted the inventory on {date_of_oos}. The standard reorder buffer was insufficient to absorb this unexpected promotional volume."
            
        elif delayed_po:
            primary = "Supplier Lead-Time Delay"
            secondary = "An outstanding Purchase Order is marked with a Delayed status in the supply pipeline."
            narrative = f"Stock runs out on {date_of_oos} due to supply delivery disruptions. Outstanding purchase orders are delayed at the supplier level, causing the replenishment arrival to fall behind the stockout date."
            
        elif not active_pipeline and curr_stock < reorder_point:
            primary = "Low Reorder Point Parameter"
            secondary = "No active PO exists in the pipeline despite current stock being below reorder point."
            narrative = f"Inventory runs dry on {date_of_oos} because no replenishment orders are active in the pipeline, even though inventory levels are below the required reorder point ({reorder_point} units)."
            
        else:
            primary = "Low Reorder Point Parameter"
            secondary = "Reorder parameters are out of sync with current supplier lead times and demand rates."
            narrative = f"The stockout predicted on {date_of_oos} occurs because the reorder point ({reorder_point} units) is set too low relative to the supplier's lead time of {lead_time} days and average demand of {avg_demand:.1f} units/day."
            
        return {
            "SKU": sku,
            "DC": dc,
            "Date_of_OOS": date_of_oos,
            "Days_Until_OOS": days_until_oos,
            "Primary_Root_Cause": primary,
            "Secondary_Factors": secondary,
            "Narrative_Reasoning": narrative
        }
