import json
import pandas as pd
from src.agents.base_agent import BaseAgent

class ForecastingAuditorAgent(BaseAgent):
    """Cognitive agent that audits historical forecast accuracy (MAPE/Bias) and provides recommendations."""
    
    def __init__(self):
        super().__init__(name="ForecastingAuditor", role="Demand Forecasting & Statistical Accuracy Expert")
        
    def audit_forecasts(self, df_history: pd.DataFrame) -> dict:
        """Calculates quantitative forecast error metrics (MAPE, Bias) per SKU and DC, and returns a detailed report."""
        audit_results = {}
        
        sku_dc_groups = df_history.groupby(["SKU", "DC"])
        for (sku, dc), group in sku_dc_groups:
            # Drop any rows with missing or zero sales to avoid division errors
            valid_group = group[(group["Actual_Sales_Units"] > 0) & (group["Forecasted_Demand_Units"] >= 0)].copy()
            if valid_group.empty:
                continue
                
            actuals = valid_group["Actual_Sales_Units"].values
            forecasts = valid_group["Forecasted_Demand_Units"].values
            n = len(actuals)
            
            # MAPE: Mean Absolute Percentage Error
            abs_errors_pct = [abs((a - f) / a) for a, f in zip(actuals, forecasts)]
            mape = (sum(abs_errors_pct) / n) * 100.0
            
            # Bias: (Sum of Forecasts - Sum of Actuals) / Sum of Actuals
            total_actuals = sum(actuals)
            bias = ((sum(forecasts) - total_actuals) / total_actuals) * 100.0 if total_actuals > 0 else 0.0
            
            audit_results[(sku, dc)] = {
                "SKU": sku,
                "DC": dc,
                "Historical_Weeks": n,
                "Avg_Weekly_Actuals": float(valid_group["Actual_Sales_Units"].mean()),
                "Avg_Weekly_Forecast": float(valid_group["Forecasted_Demand_Units"].mean()),
                "MAPE_Pct": float(mape),
                "Bias_Pct": float(bias),
                "Classification": "Under-forecasting" if bias < -5.0 else ("Over-forecasting" if bias > 5.0 else "Balanced")
            }
            
        return audit_results

    def generate_forecast_narrative(self, sku: str, dc: str, audit_data: dict, history_df: pd.DataFrame) -> dict:
        """Invokes LLM cognitive analysis to audit demand forecast volatility and suggest adjustments."""
        sku_audit = audit_data.get((sku, dc), {})
        if not sku_audit:
            return self._get_deterministic_fallback(sku, dc)
            
        if not self.is_available():
            return self._get_deterministic_fallback(sku, dc, sku_audit)
            
        system_prompt = (
            "You are a master Demand Forecaster and Statistical Auditor in supply chain management.\n"
            "Your task is to analyze historical forecast errors (MAPE %, Bias %) and recommend specific, actionable adjustments "
            "to prevent future inventory errors. Explain how variance affects the safety margins.\n"
            "Respond ONLY with a JSON object containing:\n"
            "{\n"
            "  \"Forecast_Status\": \"<Under-forecasting / Over-forecasting / Balanced>\",\n"
            "  \"MAPE_Analysis\": \"<detailed analysis of the Mean Absolute Percentage Error and what it implies for planning safety>\",\n"
            "  \"Bias_Analysis\": \"<analysis of forecast bias - whether we consistently over-predict or under-predict>\",\n"
            "  \"Suggested_Action\": \"<specific, practical advice for the planner on how to adjust the forecast or collaboration with sales (e.g., apply promotion lift factor, increase baseline)>\"\n"
            "}\n"
            "Respond in valid JSON only."
        )
        
        history_subset = history_df[(history_df["SKU"] == sku) & (history_df["DC"] == dc)].to_dict(orient="records")
        
        user_prompt = (
            f"DEMAND AUDIT CASE:\n"
            f"SKU: {sku}\n"
            f"DC: {dc}\n"
            f"Avg Weekly Actual Sales: {sku_audit['Avg_Weekly_Actuals']:.1f} units\n"
            f"Avg Weekly Forecasted Demand: {sku_audit['Avg_Weekly_Forecast']:.1f} units\n"
            f"Mean Absolute Percentage Error (MAPE): {sku_audit['MAPE_Pct']:.2f}%\n"
            f"Forecast Bias: {sku_audit['Bias_Pct']:.2f}% (Classification: {sku_audit['Classification']})\n\n"
            f"Historical 12-Week Performance Data:\n"
            f"{json.dumps(history_subset, indent=2)}\n\n"
            "Please generate the demand planning analysis report."
        )
        
        try:
            raw_response = self.call_llm(system_prompt, user_prompt, json_mode=True)
            parsed = self.parse_json_response(raw_response)
            
            return {
                "SKU": sku,
                "DC": dc,
                "MAPE": f"{sku_audit['MAPE_Pct']:.1f}%",
                "Bias": f"{sku_audit['Bias_Pct']:.1f}%",
                "Forecast_Status": parsed.get("Forecast_Status", sku_audit["Classification"]),
                "MAPE_Analysis": parsed.get("MAPE_Analysis", f"Mean error is {sku_audit['MAPE_Pct']:.1f}% against actuals."),
                "Bias_Analysis": parsed.get("Bias_Analysis", f"Bias is {sku_audit['Bias_Pct']:.1f}% indicating {sku_audit['Classification'].lower()}."),
                "Suggested_Action": parsed.get("Suggested_Action", "No action needed.")
            }
        except Exception as e:
            print(f"[WARNING] LLM forecast audit failed for {sku} at {dc}. Using fallback. Error: {e}")
            return self._get_deterministic_fallback(sku, dc, sku_audit)

    def _get_deterministic_fallback(self, sku: str, dc: str, audit_data: dict = None) -> dict:
        """Fallback heuristics for demand audit."""
        if not audit_data:
            audit_data = {
                "MAPE_Pct": 15.0,
                "Bias_Pct": 0.0,
                "Classification": "Balanced"
            }
            
        mape = audit_data["MAPE_Pct"]
        bias = audit_data["Bias_Pct"]
        status = audit_data["Classification"]
        
        # Simple heuristics
        if status == "Under-forecasting":
            suggested = "Forecast is consistently lower than actual sales. Recommended action: Increase baseline forecast by 10% to prevent stockouts and adjust safety stock buffers."
            mape_anal = f"A MAPE of {mape:.1f}% indicates moderate forecast error. Constant under-forecasting is depleting safety stock and causing OOS risks."
            bias_anal = f"Consistently negative bias of {bias:.1f}% confirms that forecasted levels are failing to capture peak customer demand."
        elif status == "Over-forecasting":
            suggested = "Forecast is consistently higher than actual sales. Recommended action: Decrease baseline forecast by 5-8% to reduce excess carrying costs and optimize working capital."
            mape_anal = f"A MAPE of {mape:.1f}% shows that inventory resources are over-allocated. High forecasts lead to inflated safety stocks."
            bias_anal = f"Positive bias of {bias:.1f}% indicates planning model overestimates sales volumes, causing stock accumulation."
        else:
            suggested = "Forecast is well-aligned. Recommended action: Monitor weekly variations and maintain current forecast modeling settings."
            mape_anal = f"Low forecast error (MAPE {mape:.1f}%) demonstrates good correlation between forecast model and actual demand."
            bias_anal = f"Minimal bias ({bias:.1f}%) suggests symmetric errors with no persistent over or under forecasting trends."
            
        return {
            "SKU": sku,
            "DC": dc,
            "MAPE": f"{mape:.1f}%",
            "Bias": f"{bias:.1f}%",
            "Forecast_Status": status,
            "MAPE_Analysis": mape_anal,
            "Bias_Analysis": bias_anal,
            "Suggested_Action": suggested
        }
