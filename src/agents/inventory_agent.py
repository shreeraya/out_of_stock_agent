import pandas as pd
import datetime

class InventorySimulationAgent:
    """Deterministic simulation agent that calculates day-by-day inventory trajectories and flags stockout events."""
    
    def __init__(self):
        self.name = "InventorySimulator"
        self.role = "Deterministic Supply Chain Simulator"
        
    def simulate_inventory(self, df_sku: pd.DataFrame, df_inventory: pd.DataFrame, df_demand: pd.DataFrame, df_pipeline: pd.DataFrame) -> tuple:
        """Runs the day-by-day inventory simulation over the forecast horizon.
        
        Returns:
            oos_risks (list of dicts): Summary of flagged OOS events.
            simulation_traces (dict): Day-by-day inventory timelines mapped by (SKU, DC).
        """
        oos_risks = []
        simulation_traces = {}
        
        # Merge SKU metadata into inventory for easier access to costs and lead times
        df_inv_meta = pd.merge(df_inventory, df_sku, on="SKU", how="left")
        
        # Parse dates in demand and pipeline sheets
        df_demand = df_demand.copy()
        df_demand["Date"] = pd.to_datetime(df_demand["Date"])
        
        df_pipeline = df_pipeline.copy()
        if not df_pipeline.empty:
            df_pipeline["Expected_Delivery_Date"] = pd.to_datetime(df_pipeline["Expected_Delivery_Date"])
            
        start_date = df_demand["Date"].min()
        end_date = df_demand["Date"].max()
        
        if pd.isna(start_date) or pd.isna(end_date):
            raise ValueError("Demand Forecast sheet has missing or invalid Dates.")
            
        horizon_days = (end_date - start_date).days + 1
        
        # Process each SKU-DC combination
        for idx, row in df_inv_meta.iterrows():
            sku = row["SKU"]
            dc = row["DC"]
            current_stock = int(row["Current_Stock_Units"])
            safety_stock = int(row["Safety_Stock_Units"])
            reorder_point = int(row["Reorder_Point_Units"])
            reorder_qty = int(row["Reorder_Quantity_Units"])
            unit_cost = float(row.get("Unit_Cost_USD", 0.0))
            
            # Filter demand and pipeline for this specific SKU & DC
            sku_demand = df_demand[(df_demand["SKU"] == sku) & (df_demand["DC"] == dc)].sort_values("Date")
            sku_pipeline = df_pipeline[(df_pipeline["SKU"] == sku) & (df_pipeline["DC"] == dc)] if not df_pipeline.empty else pd.DataFrame()
            
            # If no demand data exists for this pair, skip it
            if sku_demand.empty:
                continue
                
            # Create a daily trace log
            trace_records = []
            stock = current_stock
            first_oos_date = None
            
            for day in range(horizon_days):
                curr_date = start_date + datetime.timedelta(days=day)
                
                # Get demand for today (default to 0 if not found)
                demand_today = sku_demand[sku_demand["Date"] == curr_date]
                demand_units = int(demand_today["Forecasted_Demand_Units"].values[0]) if not demand_today.empty else 0
                
                # Check for arriving shipments today (excluding Delayed/Cancelled status)
                receipts_today = 0
                active_pipeline = pd.DataFrame()
                if not sku_pipeline.empty:
                    active_pipeline = sku_pipeline[
                        (sku_pipeline["Expected_Delivery_Date"] == curr_date) & 
                        (~sku_pipeline["Status"].isin(["Cancelled", "Delayed_Indefinitely"]))
                    ]
                    receipts_today = int(active_pipeline["Quantity_Units"].sum())
                
                # Inventory balancing math
                prev_stock = stock
                stock = prev_stock + receipts_today - demand_units
                
                # Reorder trigger warning check
                needs_reorder = (stock < reorder_point)
                has_pipeline_pending = False
                if not sku_pipeline.empty:
                    # check if there's any pending PO arriving after today
                    has_pipeline_pending = not sku_pipeline[
                        (sku_pipeline["Expected_Delivery_Date"] > curr_date) &
                        (sku_pipeline["Status"] != "Cancelled")
                    ].empty
                
                trace_records.append({
                    "Date": curr_date.strftime("%Y-%m-%d"),
                    "Starting_Stock": prev_stock,
                    "Demand": demand_units,
                    "Receipts": receipts_today,
                    "Ending_Stock": stock,
                    "Safety_Stock": safety_stock,
                    "Reorder_Point": reorder_point,
                    "Trigger_Reorder": needs_reorder and not has_pipeline_pending
                })
                
                # Flag the first OOS date in this horizon
                if stock < 0 and first_oos_date is None:
                    first_oos_date = curr_date
                    
            df_trace = pd.DataFrame(trace_records)
            simulation_traces[(sku, dc)] = df_trace
            
            # If an OOS event was detected, record it
            if first_oos_date is not None:
                days_until_oos = (first_oos_date - start_date).days
                
                # Determine Severity Level
                if days_until_oos < 5 or (unit_cost >= 50.0 and days_until_oos < 10):
                    severity = "High"
                elif 5 <= days_until_oos <= 12:
                    severity = "Medium"
                else:
                    severity = "Low"
                    
                oos_risks.append({
                    "SKU": sku,
                    "DC": dc,
                    "Date_of_OOS": first_oos_date.strftime("%Y-%m-%d"),
                    "Days_Until_OOS": max(0, days_until_oos),
                    "Current_Stock": current_stock,
                    "Projected_Stock_on_OOS_Date": int(df_trace[df_trace["Date"] == first_oos_date.strftime("%Y-%m-%d")]["Ending_Stock"].values[0]),
                    "Severity_Level": severity
                })
                
        return oos_risks, simulation_traces
