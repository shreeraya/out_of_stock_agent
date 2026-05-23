import os
import pandas as pd
from src.config import validate_config
from src.utils.excel_handler import ExcelHandler
from src.agents.demand_agent import DemandForecasterAgent
from src.agents.inventory_agent import InventorySimulationAgent
from src.agents.rca_agent import RootCauseAnalyzerAgent
from src.agents.mitigation_agent import MitigationAdvisorAgent

class StockSentinelOrchestrator:
    """Master orchestrator agent coordinating input loading, daily simulation, and AI-driven stockout diagnostics."""
    
    def __init__(self, input_path: str, output_path: str):
        self.input_path = input_path
        self.output_path = output_path
        self.excel_handler = ExcelHandler(input_path)
        
        # Instantiate the agent team
        self.demand_agent = DemandForecasterAgent()
        self.inventory_agent = InventorySimulationAgent()
        self.rca_agent = RootCauseAnalyzerAgent()
        self.mitigation_agent = MitigationAdvisorAgent()
        
    def run_pipeline(self, promo_context: str = ""):
        """Executes the complete multi-agent supply chain OOS prediction, diagnostics, and recommendation pipeline."""
        print("="*60)
        print(" STOCKSENTINEL - MULTI-AGENT SUPPLY CHAIN PIPELINE ")
        print("="*60)
        
        # Validate LLM availability (warnings only, does not stop execution)
        llm_active = validate_config()
        if llm_active:
            print("[STATUS] OpenAI Key found! High-end cognitive agents are ONLINE.")
        else:
            print("[STATUS] Running in DETERMINISTIC FALLBACK MODE. LLMs are OFFLINE.")
            
        print("\n[STEP 1] Loading and validating Excel template inputs...")
        inputs = self.excel_handler.load_inputs()
        
        df_sku = inputs["SKU_Metadata"]
        df_inventory = inputs["Inventory_Status"]
        df_demand = inputs["Demand_Forecast"]
        df_pipeline = inputs["Supply_Pipeline"]
        
        print(f" -> Loaded {len(df_sku)} SKUs across {len(df_inventory['DC'].unique())} DCs.")
        
        print("\n[STEP 2] Adjusting weekly demand forecasts (DemandForecaster Agent)...")
        # In a hybrid forecasting system, the Demand agent applies marketing promotion contexts to the base forecast
        df_adjusted_demand = self.demand_agent.forecast_weekly_demand(df_demand, promo_context)
        
        print("\n[STEP 3] Executing week-by-week inventory simulation (InventorySimulator Agent)...")
        oos_risks, simulation_traces = self.inventory_agent.simulate_inventory(
            df_sku, df_inventory, df_adjusted_demand, df_pipeline
        )
        
        total_risks = len(oos_risks)
        print(f" -> Simulation complete. Out of Stock (OOS) risks detected: {total_risks}")
        
        rca_results = []
        mitigation_results = []
        
        if total_risks > 0:
            print("\n[STEP 4] Diagnosing root causes & formulating mitigations...")
            for idx, risk in enumerate(oos_risks, start=1):
                sku = risk["SKU"]
                dc = risk["DC"]
                week_of_oos = risk["Week_of_OOS"]
                
                print(f" [{idx}/{total_risks}] Auditing {sku} at {dc} (OOS week: {week_of_oos})...")
                
                # Extract specific trace & params for this SKU-DC pair
                trace = simulation_traces.get((sku, dc))
                sku_meta = df_sku[df_sku["SKU"] == sku].to_dict(orient="records")
                sku_meta = sku_meta[0] if sku_meta else {}
                
                inv_status = df_inventory[(df_inventory["SKU"] == sku) & (df_inventory["DC"] == dc)].to_dict(orient="records")
                inv_status = inv_status[0] if inv_status else {}
                
                pipeline_orders = df_pipeline[(df_pipeline["SKU"] == sku) & (df_pipeline["DC"] == dc)].to_dict(orient="records") if not df_pipeline.empty else []
                
                # 4a. Run Root Cause Diagnostics
                rca_report = self.rca_agent.diagnose_stockout(
                    risk, trace, sku_meta, inv_status, pipeline_orders
                )
                rca_results.append(rca_report)
                print(f"   * Diagnosis: {rca_report['Primary_Root_Cause']}")
                
                # 4b. Formulate Mitigation recommendations
                mitigation_report = self.mitigation_agent.formulate_mitigation(
                    rca_report, df_inventory, df_sku, pipeline_orders
                )
                mitigation_results.append(mitigation_report)
                print(f"   * Recommendation: {mitigation_report['Recommended_Action']} (${mitigation_report['Estimated_Cost_USD']:.2f})")
        else:
            print("\n[STEP 4] Skipping diagnostics: No out-of-stock risks detected in the horizon!")
            
        print("\n[STEP 5] Compiling and generating premium formatted Excel report...")
        self.excel_handler.write_analysis_report(
            self.output_path, inputs, oos_risks, rca_results, mitigation_results
        )
        
        print("\n" + "="*60)
        print(" PIPELINE COMPLETED SUCCESSFULLY! ")
        print(f" Executive report saved at: {self.output_path}")
        print("="*60)
        
        return oos_risks, rca_results, mitigation_results
