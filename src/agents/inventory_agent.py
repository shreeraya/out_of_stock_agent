import pandas as pd
import datetime
import math

def normal_cdf(x, mean=0.0, std_dev=1.0):
    """Accurate approximation of the Cumulative Distribution Function of the Normal Distribution."""
    if std_dev <= 0:
        return 1.0 if x < mean else 0.0
    z = (x - mean) / std_dev
    
    # High-precision polynomial approximation of Erf(z/sqrt(2))
    # Reference: Abramowitz and Stegun formula 7.1.26
    t = 1.0 / (1.0 + 0.2316419 * abs(z))
    a1 = 0.319381530
    a2 = -0.356563782
    a3 = 1.781477937
    a4 = -1.821255978
    a5 = 1.330274429
    
    prob = 1.0 - 1.0 / (math.sqrt(2 * math.pi)) * math.exp(-z * z / 2.0) * (
        a1 * t + a2 * t**2 + a3 * t**3 + a4 * t**4 + a5 * t**5
    )
    if z < 0:
        return 1.0 - prob
    return prob

class InventorySimulationAgent:
    """Probabilistic simulation agent that calculates daily inventory trajectories, variability risk, and flags stockout events."""
    
    def __init__(self):
        self.name = "InventorySimulator"
        self.role = "Probabilistic Supply Chain Simulator"
        
    def simulate_inventory(self, df_sku: pd.DataFrame, df_inventory: pd.DataFrame, df_demand: pd.DataFrame, df_pipeline: pd.DataFrame) -> tuple:
        """Runs the week-by-week inventory simulation over the forecast horizon.
        
        Returns:
            oos_risks (list of dicts): Summary of flagged OOS events.
            simulation_traces (dict): Weekly inventory timelines mapped by (SKU, DC).
        """
        oos_risks = []
        simulation_traces = {}
        
        # Merge SKU metadata into inventory for easier access to costs and lead times
        df_inv_meta = pd.merge(df_inventory, df_sku, on="SKU", how="left")
        
        # Parse dates in demand and pipeline sheets
        df_demand = df_demand.copy()
        df_demand["Week_Start_Date"] = pd.to_datetime(df_demand["Week_Start_Date"])
        
        df_pipeline = df_pipeline.copy()
        if not df_pipeline.empty:
            df_pipeline["Expected_Delivery_Week_Start"] = pd.to_datetime(df_pipeline["Expected_Delivery_Week_Start"])
            
        start_date = df_demand["Week_Start_Date"].min()
        end_date = df_demand["Week_Start_Date"].max()
        
        if pd.isna(start_date) or pd.isna(end_date):
            raise ValueError("Demand Forecast sheet has missing or invalid Week_Start_Dates.")
            
        horizon_weeks = (end_date - start_date).days // 7 + 1
        
        # Process each SKU-DC combination
        for idx, row in df_inv_meta.iterrows():
            sku = row["SKU"]
            dc = row["DC"]
            current_stock = int(row["Current_Stock_Units"])
            safety_stock = int(row["Safety_Stock_Units"])
            reorder_point = int(row["Reorder_Point_Units"])
            reorder_qty = int(row["Reorder_Quantity_Units"])
            unit_cost = float(row.get("Unit_Cost_USD", 0.0))
            
            # Extract standard deviation of lead time in WEEKS (default fallback to 15% of lead time)
            lead_time_weeks = float(row.get("Lead_Time_Weeks", 1.0))
            lead_time_std = float(row.get("Lead_Time_StdDev_Weeks", lead_time_weeks * 0.15))
            
            # Filter demand and pipeline for this specific SKU & DC
            sku_demand = df_demand[(df_demand["SKU"] == sku) & (df_demand["DC"] == dc)].sort_values("Week_Start_Date")
            sku_pipeline = df_pipeline[(df_pipeline["SKU"] == sku) & (df_pipeline["DC"] == dc)] if not df_pipeline.empty else pd.DataFrame()
            
            # If no demand data exists for this pair, skip it
            if sku_demand.empty:
                continue
                
            # Extract weekly demand standard deviation (fallback to weekly forecast standard deviation or 20% of mean demand)
            demand_values = sku_demand["Forecasted_Demand_Units"].values
            forecast_std = float(demand_values.std()) if len(demand_values) > 1 else 0.0
            if forecast_std == 0.0:
                forecast_std = float(demand_values.mean() * 0.20) if len(demand_values) > 0 else 5.0
            
            demand_std_val = row.get("Weekly_Demand_StdDev_Units")
            if pd.isna(demand_std_val) or demand_std_val is None:
                demand_std = forecast_std
            else:
                demand_std = float(demand_std_val)
                
            # Create a weekly trace log
            trace_records = []
            stock = current_stock
            first_oos_date = None
            prob_at_oos = 0.0
            
            for week in range(horizon_weeks):
                curr_date = start_date + datetime.timedelta(weeks=week)
                
                # Get demand for this week (default to 0 if not found)
                demand_this_week = sku_demand[sku_demand["Week_Start_Date"] == curr_date]
                demand_units = int(demand_this_week["Forecasted_Demand_Units"].values[0]) if not demand_this_week.empty else 0
                
                # Check for arriving shipments this week (excluding Delayed/Cancelled status)
                receipts_this_week = 0
                active_pipeline = pd.DataFrame()
                if not sku_pipeline.empty:
                    active_pipeline = sku_pipeline[
                        (sku_pipeline["Expected_Delivery_Week_Start"] == curr_date) & 
                        (~sku_pipeline["Status"].isin(["Cancelled", "Delayed_Indefinitely"]))
                    ]
                    receipts_this_week = int(active_pipeline["Quantity_Units"].sum())
                
                # Inventory balancing math
                prev_stock = stock
                stock = prev_stock + receipts_this_week - demand_units
                
                # Reorder trigger warning check
                needs_reorder = (stock < reorder_point)
                has_pipeline_pending = False
                if not sku_pipeline.empty:
                    # check if there's any pending PO arriving after this week
                    has_pipeline_pending = not sku_pipeline[
                        (sku_pipeline["Expected_Delivery_Week_Start"] > curr_date) &
                        (sku_pipeline["Status"] != "Cancelled")
                    ].empty
                
                # Probabilistic inventory risk calculation (Weekly)
                # Standard deviation combines weekly demand volatility over time plus baseline lead-time volatility
                std_cum = math.sqrt((week + 1) * (demand_std ** 2) + (lead_time_std ** 2))
                prob_oos = normal_cdf(0.0, mean=stock, std_dev=std_cum)
                
                trace_records.append({
                    "Week_Start_Date": curr_date.strftime("%Y-%m-%d"),
                    "Starting_Stock": prev_stock,
                    "Demand": demand_units,
                    "Receipts": receipts_this_week,
                    "Ending_Stock": stock,
                    "Safety_Stock": safety_stock,
                    "Reorder_Point": reorder_point,
                    "Trigger_Reorder": needs_reorder and not has_pipeline_pending,
                    "OOS_Probability": float(prob_oos)
                })
                
                # Flag the first OOS week in this horizon
                # Active risk is flagged if stock goes negative OR OOS probability exceeds 85%
                if (stock < 0 or prob_oos >= 0.85) and first_oos_date is None:
                    first_oos_date = curr_date
                    prob_at_oos = prob_oos
                    
            df_trace = pd.DataFrame(trace_records)
            simulation_traces[(sku, dc)] = df_trace
            
            # If an OOS event was detected, record it
            if first_oos_date is not None:
                weeks_until_oos = (first_oos_date - start_date).days // 7
                
                # Determine Severity Level (Weeks based: High if OOS in < 2 weeks, Medium 2-4 weeks, Low 5+ weeks)
                if weeks_until_oos < 2 or (unit_cost >= 50.0 and weeks_until_oos < 3):
                    severity = "High"
                elif 2 <= weeks_until_oos <= 4:
                    severity = "Medium"
                else:
                    severity = "Low"
                    
                oos_risks.append({
                    "SKU": sku,
                    "DC": dc,
                    "Week_of_OOS": first_oos_date.strftime("%Y-%m-%d"),
                    "Weeks_Until_OOS": max(0, weeks_until_oos),
                    "Current_Stock": current_stock,
                    "Projected_Stock_on_OOS_Date": int(df_trace[df_trace["Week_Start_Date"] == first_oos_date.strftime("%Y-%m-%d")]["Ending_Stock"].values[0]),
                    "Stockout_Probability": float(prob_at_oos),
                    "Severity_Level": severity
                })
                
        return oos_risks, simulation_traces
