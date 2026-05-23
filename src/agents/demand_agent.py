import json
import pandas as pd
from src.agents.base_agent import BaseAgent

class DemandForecasterAgent(BaseAgent):
    """Hybrid agent that aggregates quantitative baseline forecasts and applies qualitative adjustments using LLMs."""
    
    def __init__(self):
        super().__init__(name="DemandForecaster", role="Demand Forecasting & Promotion Auditor")
        
    def forecast_daily_demand(self, df_demand: pd.DataFrame, promo_context: str = "") -> pd.DataFrame:
        """Loads baseline demand from spreadsheet and applies LLM adjustments if promo context is provided."""
        # Baseline demand is directly loaded from the input sheet
        df_proj = df_demand.copy()
        
        # If no OpenAI key or no promo context is provided, return baseline
        if not self.is_available() or not promo_context:
            return df_proj
            
        print("[INFO] DemandForecasterAgent auditing demand forecast with LLM context...")
        
        # We can summarize the baseline demand per SKU/DC to avoid blowing out token limits,
        # then ask the LLM to provide adjustment factors or a modified daily schedule.
        sku_dc_groups = df_proj.groupby(["SKU", "DC"])
        adjusted_rows = []
        
        for (sku, dc), group in sku_dc_groups:
            baseline_data = group.to_dict(orient="records")
            
            system_prompt = (
                "You are an expert Demand Forecasting Agent in supply chain management.\n"
                "Your role is to analyze baseline demand forecasts and adjust them based on promotional notes or external market events.\n"
                "You must output a JSON object containing the adjusted demand values.\n"
                "Respond ONLY in valid JSON format."
            )
            
            user_prompt = (
                f"SKU: {sku}\nDC: {dc}\n"
                f"Market/Promotion Context: {promo_context}\n\n"
                f"Baseline Forecast:\n"
                f"{json.dumps(baseline_data, indent=2)}\n\n"
                "Please adjust the forecasted daily demand units based on the market context. If the context does not affect this SKU or DC, keep the baseline.\n"
                "Return the result as a JSON object with an 'adjusted_forecast' list containing elements with 'Date' and 'Adjusted_Demand_Units' (integers)."
            )
            
            try:
                raw_response = self.call_llm(system_prompt, user_prompt, json_mode=True)
                parsed = self.parse_json_response(raw_response)
                
                adjusted_map = {item["Date"]: int(item["Adjusted_Demand_Units"]) for item in parsed.get("adjusted_forecast", [])}
                
                for row in baseline_data:
                    date_str = row["Date"]
                    if date_str in adjusted_map:
                        row["Forecasted_Demand_Units"] = adjusted_map[date_str]
                    adjusted_rows.append(row)
            except Exception as e:
                print(f"[WARNING] Failed to adjust demand for {sku} at {dc} using LLM. Reverting to baseline. Error: {e}")
                adjusted_rows.extend(baseline_data)
                
        return pd.DataFrame(adjusted_rows)
