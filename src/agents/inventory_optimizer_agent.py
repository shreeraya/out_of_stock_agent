import json
import math
import pandas as pd
from src.agents.base_agent import BaseAgent

class InventoryOptimizerAgent(BaseAgent):
    """Cognitive agent that runs inventory optimization math (Safety Stock, EOQ, Stock Turns) and provides recommendations."""
    
    def __init__(self):
        super().__init__(name="InventoryOptimizer", role="Inventory Management & Parameter Optimization Expert")
        
    def optimize_inventory(self, df_sku: pd.DataFrame, df_inventory: pd.DataFrame, df_history: pd.DataFrame, service_level: float = 0.95) -> dict:
        """Calculates Safety Stock, EOQ, and Stock Turn rates mathematically for all SKU-DC pairs."""
        optimization_results = {}
        
        # Service level Z-score mapper
        # Simple Z-score approximations for standard levels
        if service_level >= 0.99:
            z_score = 2.326
        elif service_level >= 0.98:
            z_score = 2.054
        elif service_level >= 0.95:
            z_score = 1.645
        elif service_level >= 0.90:
            z_score = 1.282
        else:
            z_score = 1.000 # default fallback
            
        # Merge datasets
        df_inv_meta = pd.merge(df_inventory, df_sku, on="SKU", how="left")
        
        for idx, row in df_inv_meta.iterrows():
            sku = row["SKU"]
            dc = row["DC"]
            unit_cost = float(row.get("Unit_Cost_USD", 10.0))
            reorder_qty = int(row["Reorder_Quantity_Units"])
            
            lead_time_w = float(row.get("Lead_Time_Weeks", 1.0))
            lead_time_std_w = float(row.get("Lead_Time_StdDev_Weeks", lead_time_w * 0.15))
            
            # Extract historical demand
            sku_history = df_history[(df_history["SKU"] == sku) & (df_history["DC"] == dc)]
            if sku_history.empty:
                continue
                
            avg_demand = float(sku_history["Actual_Sales_Units"].mean())
            
            demand_std_val = row.get("Weekly_Demand_StdDev_Units")
            if pd.isna(demand_std_val) or demand_std_val is None:
                demand_std = float(sku_history["Actual_Sales_Units"].std())
                if pd.isna(demand_std) or demand_std == 0.0:
                    demand_std = avg_demand * 0.20
            else:
                demand_std = float(demand_std_val)
                
            # --- Safety Stock Optimization Formula ---
            # SS = Z * sqrt( L * sigma_D^2 + D^2 * sigma_L^2 )
            ss_term = (lead_time_w * (demand_std ** 2)) + ((avg_demand ** 2) * (lead_time_std_w ** 2))
            optimal_ss = math.ceil(z_score * math.sqrt(ss_term))
            
            # --- Economic Order Quantity (EOQ) Formula ---
            # EOQ = sqrt( 2 * Annual_Demand * Order_Cost / Holding_Cost )
            # We assume ordering cost S = $100.00 and annual carrying charge rate = 20%
            annual_demand = avg_demand * 52.0
            order_cost = 100.00
            carrying_rate = 0.20
            holding_cost = carrying_rate * unit_cost
            
            if holding_cost > 0:
                optimal_eoq = math.ceil(math.sqrt((2 * annual_demand * order_cost) / holding_cost))
            else:
                optimal_eoq = reorder_qty
                
            # --- Stock Turn Rate Formula ---
            # Stock Turns = Annual Demand / Average Inventory Value
            # Avg Inventory = Safety Stock + Reorder Quantity / 2
            avg_stock = optimal_ss + (reorder_qty / 2.0)
            turns = annual_demand / avg_stock if avg_stock > 0 else 0.0
            
            # Reorder Point Optimization: Average Lead Time Demand + Safety Stock
            optimal_rop = math.ceil((avg_demand * lead_time_w) + optimal_ss)
            
            optimization_results[(sku, dc)] = {
                "SKU": sku,
                "DC": dc,
                "Current_Safety_Stock": int(row["Safety_Stock_Units"]),
                "Optimal_Safety_Stock": int(optimal_ss),
                "Current_Reorder_Point": int(row["Reorder_Point_Units"]),
                "Optimal_Reorder_Point": int(optimal_rop),
                "Current_Reorder_Qty": int(reorder_qty),
                "Optimal_EOQ": int(optimal_eoq),
                "Avg_Weekly_Demand": float(avg_demand),
                "Avg_Inventory_Units": float(avg_stock),
                "Stock_Turn_Rate": float(turns)
            }
            
        return optimization_results

    def generate_optimization_narrative(self, sku: str, dc: str, opt_data: dict) -> dict:
        """Invokes LLM cognitive capabilities to generate parametric master data tuning suggestions."""
        sku_opt = opt_data.get((sku, dc), {})
        if not sku_opt:
            return self._get_deterministic_fallback(sku, dc)
            
        if not self.is_available():
            return self._get_deterministic_fallback(sku, dc, sku_opt)
            
        system_prompt = (
            "You are a master Supply Chain Inventory Optimization Consultant.\n"
            "Your task is to analyze calculated inventory parameters (Optimal Safety Stock, optimal Reorder Point, EOQ, Stock Turns) "
            "and write detailed recommendations for a Supply Planner to update their ERP master data (SAP MM02).\n"
            "Respond ONLY with a JSON object containing:\n"
            "{\n"
            "  \"Safety_Stock_Analysis\": \"<discussion comparing current safety stock with optimal, highlighting volatility coverage>\",\n"
            "  \"Replenishment_Analysis\": \"<discussion comparing current reorder parameters against EOQ and Optimal Reorder Point (ROP)>\",\n"
            "  \"Stock_Turn_Analysis\": \"<evaluation of the stock turn rate, whether it is healthy, and how to improve it>\",\n"
            "  \"ERP_Directives\": \"<exact step-by-step transaction instructions for updating Safety Stock (SS) and Reorder Point (ROP) in SAP MM02 or similar system>\"\n"
            "}\n"
            "Respond in valid JSON only."
        )
        
        user_prompt = (
            f"INVENTORY OPTIMIZATION SHEET:\n"
            f"SKU: {sku}\n"
            f"DC: {dc}\n"
            f"Current Safety Stock: {sku_opt['Current_Safety_Stock']} units\n"
            f"Optimal Safety Stock (Calculated): {sku_opt['Optimal_Safety_Stock']} units\n"
            f"Current Reorder Point: {sku_opt['Current_Reorder_Point']} units\n"
            f"Optimal Reorder Point (ROP): {sku_opt['Optimal_Reorder_Point']} units\n"
            f"Current Reorder Quantity: {sku_opt['Current_Reorder_Qty']} units\n"
            f"Optimal Economic Order Quantity (EOQ): {sku_opt['Optimal_EOQ']} units\n"
            f"Avg Weekly Demand: {sku_opt['Avg_Weekly_Demand']:.1f} units\n"
            f"Estimated Stock Turn Rate: {sku_opt['Stock_Turn_Rate']:.2f} turns/year\n\n"
            "Please analyze these parameters and generate the inventory recommendation JSON."
        )
        
        try:
            raw_response = self.call_llm(system_prompt, user_prompt, json_mode=True)
            parsed = self.parse_json_response(raw_response)
            
            return {
                "SKU": sku,
                "DC": dc,
                "Current_Safety_Stock": sku_opt["Current_Safety_Stock"],
                "Optimal_Safety_Stock": sku_opt["Optimal_Safety_Stock"],
                "Current_Reorder_Point": sku_opt["Current_Reorder_Point"],
                "Optimal_Reorder_Point": sku_opt["Optimal_Reorder_Point"],
                "Optimal_EOQ": sku_opt["Optimal_EOQ"],
                "Stock_Turn_Rate": f"{sku_opt['Stock_Turn_Rate']:.2f}",
                "Safety_Stock_Analysis": parsed.get("Safety_Stock_Analysis", "Current safety stock compared with optimal levels."),
                "Replenishment_Analysis": parsed.get("Replenishment_Analysis", "Reorder point and replenishment cycle recommendations."),
                "Stock_Turn_Analysis": parsed.get("Stock_Turn_Analysis", "Inventory turns optimization suggestions."),
                "ERP_Directives": parsed.get("ERP_Directives", "SAP MM02 master data update directives.")
            }
        except Exception as e:
            print(f"[WARNING] LLM inventory optimization failed for {sku} at {dc}. Using fallback. Error: {e}")
            return self._get_deterministic_fallback(sku, dc, sku_opt)

    def _get_deterministic_fallback(self, sku: str, dc: str, opt_data: dict = None) -> dict:
        """Fallback heuristics for inventory audit."""
        if not opt_data:
            opt_data = {
                "Current_Safety_Stock": 40,
                "Optimal_Safety_Stock": 45,
                "Current_Reorder_Point": 60,
                "Optimal_Reorder_Point": 65,
                "Optimal_EOQ": 100,
                "Stock_Turn_Rate": 12.0
            }
            
        ss_curr = opt_data["Current_Safety_Stock"]
        ss_opt = opt_data["Optimal_Safety_Stock"]
        rop_curr = opt_data["Current_Reorder_Point"]
        rop_opt = opt_data["Optimal_Reorder_Point"]
        eoq = opt_data["Optimal_EOQ"]
        turns = opt_data["Stock_Turn_Rate"]
        
        # Analyze safety stock difference
        if ss_opt > ss_curr:
            ss_anal = f"Current safety stock ({ss_curr} units) is under-buffered. We calculate that {ss_opt} units are required to absorb combined demand and lead-time volatility at the target service level."
            rop_anal = f"Reorder Point should be increased to {rop_opt} units to trigger replenishments earlier, avoiding delays caused by supplier shipping variance."
        elif ss_opt < ss_curr:
            ss_anal = f"Current safety stock ({ss_curr} units) is over-buffered. Optimal calculations show {ss_opt} units is sufficient, allowing you to reduce holding costs safely."
            rop_anal = f"Reorder Point can be safely adjusted down to {rop_opt} units, deferring orders and freeing up warehouse storage capacity."
        else:
            ss_anal = "Current safety stock matches calculated requirements exactly. Buffer settings are optimal."
            rop_anal = "Reorder parameters are well-balanced and require no immediate adjustments."
            
        directives = (
            f"1. Log into your ERP system and open the Material Master transaction (SAP MM02).\n"
            f"2. Search for Material SKU '{sku}' and select the MRP 1 and MRP 2 views for Plant DC '{dc}'.\n"
            f"3. In MRP 1 view, review MRP Type (verify set to 'PD' or 'VM' reorder point planning).\n"
            f"4. Modify the Reorder Point field from {rop_curr} to **{rop_opt}** units.\n"
            f"5. In MRP 2 view, locate the Safety Stock field and adjust from {ss_curr} to **{ss_opt}** units.\n"
            f"6. Save the record and notify the replenishment planning supervisor to monitor future order releases."
        )
        
        return {
            "SKU": sku,
            "DC": dc,
            "Current_Safety_Stock": ss_curr,
            "Optimal_Safety_Stock": ss_opt,
            "Current_Reorder_Point": rop_curr,
            "Optimal_Reorder_Point": rop_opt,
            "Optimal_EOQ": eoq,
            "Stock_Turn_Rate": f"{turns:.2f}",
            "Safety_Stock_Analysis": ss_anal,
            "Replenishment_Analysis": rop_anal,
            "Stock_Turn_Analysis": f"Stock turn rate is {turns:.2f} turns/year. Reordering in EOQ batches of {eoq} units will maintain a balanced carrying turnover.",
            "ERP_Directives": directives
        }
