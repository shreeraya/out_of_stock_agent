import json
import pandas as pd
from src.agents.base_agent import BaseAgent

class MitigationAdvisorAgent(BaseAgent):
    """Cognitive agent that devises actionable, cost-efficient mitigation plans to prevent predicted out-of-stock events."""
    
    def __init__(self):
        super().__init__(name="MitigationAdvisor", role="Supply Chain Mitigation & Optimization Expert")
        
    def formulate_mitigation(self, rca_report: dict, df_inventory: pd.DataFrame, df_sku: pd.DataFrame, pipeline_orders: list) -> dict:
        """Formulates an actionable mitigation recommendation using LLM reasoning (with robust deterministic fallback if offline)."""
        sku = rca_report["SKU"]
        dc = rca_report["DC"]
        date_of_oos = rca_report["Date_of_OOS"]
        days_until_oos = rca_report["Days_Until_OOS"]
        root_cause = rca_report["Primary_Root_Cause"]
        
        # 1. Gather SKU metadata
        sku_meta = df_sku[df_sku["SKU"] == sku].to_dict(orient="records")
        sku_meta = sku_meta[0] if sku_meta else {}
        unit_cost = sku_meta.get("Unit_Cost_USD", 10.0)
        
        # 2. Identify potential transfer opportunities from other DCs
        transfer_sources = []
        other_dcs = df_inventory[(df_inventory["SKU"] == sku) & (df_inventory["DC"] != dc)]
        for _, row in other_dcs.iterrows():
            current_stock = row["Current_Stock_Units"]
            safety_stock = row["Safety_Stock_Units"]
            surplus = current_stock - safety_stock
            if surplus > 20: # Source must have a meaningful surplus above its safety stock
                transfer_sources.append({
                    "Source_DC": row["DC"],
                    "Available_Stock": current_stock,
                    "Safety_Stock": safety_stock,
                    "Transferable_Surplus": surplus
                })
                
        # 3. Fallback Logic (Deterministic heuristics when OpenAI is offline)
        fallback_mitigation = self._get_deterministic_fallback(rca_report, sku_meta, transfer_sources, pipeline_orders)
        
        if not self.is_available():
            return fallback_mitigation
            
        # 4. Cognitive LLM Logic
        system_prompt = (
            "You are a master Supply Chain Planner & Logistics Director.\n"
            "Your objective is to provide a highly practical, granular, and logistically actionable mitigation recommendation to prevent a predicted Out-of-Stock (OOS) event. "
            "These directives will be sent directly to corporate Supply Planners to execute in their day-to-day operations.\n\n"
            "CRITICAL DIRECTIVES FOR ACTIONABLE OUTPUTS:\n"
            "1. **Explicit Ownership & Steps**: Break down actions into sequential, step-by-step tasks (e.g., ERP transaction codes, supplier contacts, logistics bookings).\n"
            "2. **Specific IDs & Data**: Always refer to the exact SKU code, DC, Order_ID (PO-XXX), and supplier IDs provided. Do not use placeholders.\n"
            "3. **ERP Actions**: Detail what master data parameters should be adjusted (e.g., Safety Stock, Reorder Point) in their ERP system (SAP/Oracle/etc.) if relevant.\n"
            "4. **Concrete logistics**: Give clear freight directives (e.g., STO LTL, expedited air freight, carrier upgrade).\n"
            "5. **Priority and Value**: Assign realistic cost impacts and quantities based on the unit costs and deficits.\n\n"
            "Recommend one of the following core action types:\n"
            "- 'Inter-DC Stock Transfer' (if another DC has a transferable surplus above its safety stock)\n"
            "- 'Expedite Outstanding PO' (if an active order is delayed or scheduled to arrive too late)\n"
            "- 'Emergency Replenishment PO' (if no pipeline order exists, or existing order is insufficient)\n"
            "- 'Reorder Parametric Adjustment' (adjust reorder point/safety stock in ERP, and place order)\n"
            "Respond ONLY with a JSON object containing:\n"
            "{\n"
            "  \"Recommended_Action\": \"<action_type>\",\n"
            "  \"Action_Steps\": \"<numbered step-by-step logistics directives. Format as a professional bulleted checklist suitable for a planner's task list>\",\n"
            "  \"Inventory_Impact_Units\": <integer quantity to order/transfer>,\n"
            "  \"Estimated_Cost_USD\": <float cost of freight/handling>,\n"
            "  \"Priority_Level\": \"<High, Medium, or Low>\"\n"
            "}\n"
            "Respond in valid JSON only."
        )
        
        user_prompt = (
            f"MITIGATION ASSIGNMENT:\n"
            f"SKU: {sku} ({sku_meta.get('Description', 'N/A')})\n"
            f"DC: {dc}\n"
            f"Unit Cost: ${unit_cost:.2f}\n"
            f"Diagnosed Root Cause: {root_cause}\n"
            f"Reasoning: {rca_report['Narrative_Reasoning']}\n"
            f"OOS Predicted on: {date_of_oos} (in {days_until_oos} days)\n"
            f"Outstanding Supply Pipeline: {json.dumps(pipeline_orders, indent=2)}\n"
            f"Potential Transfer Sources (Surplus at Other DCs): {json.dumps(transfer_sources, indent=2)}\n\n"
            f"Please formulate the most cost-efficient, operational plan to prevent the stockout. "
            f"Draft highly granular action steps (e.g. naming specific ERP codes, supplier IDs, and transport booking instructions) that a Supply Planner can immediately execute. "
            f"Generate the final recommendations JSON."
        )
        
        try:
            raw_response = self.call_llm(system_prompt, user_prompt, json_mode=True)
            parsed = self.parse_json_response(raw_response)
            
            result = {
                "SKU": sku,
                "DC": dc,
                "Date_of_OOS": date_of_oos,
                "Recommended_Action": parsed.get("Recommended_Action", fallback_mitigation["Recommended_Action"]),
                "Action_Steps": parsed.get("Action_Steps", fallback_mitigation["Action_Steps"]),
                "Inventory_Impact_Units": int(parsed.get("Inventory_Impact_Units", fallback_mitigation["Inventory_Impact_Units"])),
                "Estimated_Cost_USD": float(parsed.get("Estimated_Cost_USD", fallback_mitigation["Estimated_Cost_USD"])),
                "Priority_Level": parsed.get("Priority_Level", fallback_mitigation["Priority_Level"])
            }
            return result
        except Exception as e:
            print(f"[WARNING] LLM mitigation failed for {sku} at {dc}. Using deterministic fallback. Error: {e}")
            return fallback_mitigation
            
    def _get_deterministic_fallback(self, rca_report: dict, sku_meta: dict, transfer_sources: list, pipeline_orders: list) -> dict:
        """Deterministic heuristic fallback when LLM is unavailable."""
        sku = rca_report["SKU"]
        dc = rca_report["DC"]
        date_of_oos = rca_report["Date_of_OOS"]
        days_until_oos = rca_report["Days_Until_OOS"]
        root_cause = rca_report["Primary_Root_Cause"]
        
        unit_cost = sku_meta.get("Unit_Cost_USD", 10.0)
        lead_time = sku_meta.get("Lead_Time_Days", 7)
        
        # Priority level
        if days_until_oos < 5:
            priority = "High"
        elif 5 <= days_until_oos <= 12:
            priority = "Medium"
        else:
            priority = "Low"
            
        # Case 1: Inter-DC Stock Transfer opportunity exists
        if transfer_sources:
            source = transfer_sources[0]
            transfer_qty = min(80, int(source["Transferable_Surplus"]))
            cost = 150.00 + (transfer_qty * 1.50) # Flat LTL + per unit handling
            steps = (
                f"1. Open ERP Stock Transfer Transaction (e.g., SAP MB1B / ME21N) and initiate a Stock Transport Order (STO) for {transfer_qty} units of {sku} from source plant {source['Source_DC']} to receiving plant {dc}.\n"
                f"2. Contact regional warehouse logistics lead at plant {source['Source_DC']} to expedite picking/packing and coordinate carrier booking.\n"
                f"3. Route via expedited Less-Than-Truckload (LTL) carrier. Expected transit time: 3 days. Track shipment status daily to ensure receipt prior to OOS date {date_of_oos}."
            )
            return {
                "SKU": sku,
                "DC": dc,
                "Date_of_OOS": date_of_oos,
                "Recommended_Action": "Inter-DC Stock Transfer",
                "Action_Steps": steps,
                "Inventory_Impact_Units": transfer_qty,
                "Estimated_Cost_USD": cost,
                "Priority_Level": priority
            }
            
        # Case 2: Outstanding delayed PO exists that can be expedited
        delayed_po = None
        for po in pipeline_orders:
            if po.get("Status") in ["Delayed", "Placed", "In Transit"]:
                delayed_po = po
                break
                
        if delayed_po:
            po_id = delayed_po.get("Order_ID", "Active PO")
            qty = int(delayed_po.get("Quantity_Units", 100))
            cost = 250.00 # Expedited carrier surcharge
            po_date = delayed_po.get("Expected_Delivery_Date", "original date")
            steps = (
                f"1. Open ERP Purchase Order Transaction (e.g., SAP ME22N) and locate PO {po_id} for {qty} units of {sku}.\n"
                f"2. Contact the supplier account manager for {sku_meta.get('Supplier_ID', 'SUPP')} to verify production readiness and release status.\n"
                f"3. Coordinate with internal shipping department to upgrade transport routing from Standard LTL to Expedited Carrier (ETA shift: compress from {po_date} to before {date_of_oos}).\n"
                f"4. Apply expedited carrier surcharge of $250.00 and flag receiving dock at {dc} to prioritize offloading."
            )
            return {
                "SKU": sku,
                "DC": dc,
                "Date_of_OOS": date_of_oos,
                "Recommended_Action": "Expedite Outstanding PO",
                "Action_Steps": steps,
                "Inventory_Impact_Units": qty,
                "Estimated_Cost_USD": cost,
                "Priority_Level": priority
            }
            
        # Case 3: Emergency PO needed
        qty_needed = 100
        cost = 350.00 + (qty_needed * unit_cost * 0.10) # Freight cost estimation
        steps = (
            f"1. Immediately draft and release an emergency Purchase Order for {qty_needed} units of {sku} to supplier {sku_meta.get('Supplier_ID', 'SUPP')} (ERP Transaction ME21N).\n"
            f"2. Contact supplier sales desk to request priority queue allocation and immediate manufacturing release.\n"
            f"3. Route via expedited Air Freight (estimated charge: ${cost:.2f}) to bypass standard {lead_time}-day lead time. Target delivery by {date_of_oos}.\n"
            f"4. Open ERP Material Master (SAP MM02) and review reorder point / safety stock buffer parameters to increase capacity settings for future replenishment cycles."
        )
        return {
            "SKU": sku,
            "DC": dc,
            "Date_of_OOS": date_of_oos,
            "Recommended_Action": "Emergency Replenishment PO",
            "Action_Steps": steps,
            "Inventory_Impact_Units": qty_needed,
            "Estimated_Cost_USD": cost,
            "Priority_Level": priority
        }
