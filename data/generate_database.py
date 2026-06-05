import os
import datetime
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def create_supply_chain_db():
    # Define directory and filename
    os.makedirs("data", exist_ok=True)
    filename = os.path.join("data", "supply_chain_db.xlsx")
    
    # Styling definitions (Executive Slate Theme)
    HEADER_FILL = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid")
    ZEBRA_FILL = PatternFill(start_color="F8F9FA", end_color="F8F9FA", fill_type="solid")
    WHITE_FILL = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    
    FONT_FAMILY = "Segoe UI"
    header_font = Font(name=FONT_FAMILY, size=11, bold=True, color="FFFFFF")
    title_font = Font(name=FONT_FAMILY, size=16, bold=True, color="2C3E50")
    subtitle_font = Font(name=FONT_FAMILY, size=10, italic=True, color="7F8C8D")
    bold_font = Font(name=FONT_FAMILY, size=10, bold=True, color="2C3E50")
    regular_font = Font(name=FONT_FAMILY, size=10, color="2C3E50")
    
    left_align = Alignment(horizontal="left", vertical="center")
    center_align = Alignment(horizontal="center", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")
    
    thin_border_side = Side(border_style="thin", color="D5DBDB")
    thin_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    thick_bottom_side = Side(border_style="medium", color="2C3E50")
    header_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thick_bottom_side)
    
    # 1. SKU Metadata (lead times in weeks)
    sku_data = [
        {"SKU": "SKU-001", "Description": "Premium Wireless Headphones", "Category": "Electronics", "Supplier_ID": "SUPP-101", "Unit_Cost_USD": 45.00, "Selling_Price_USD": 99.00, "Lead_Time_Weeks": 1.0, "Lead_Time_StdDev_Weeks": 0.2},
        {"SKU": "SKU-002", "Description": "Ergonomic Office Chair", "Category": "Furniture", "Supplier_ID": "SUPP-202", "Unit_Cost_USD": 75.00, "Selling_Price_USD": 180.00, "Lead_Time_Weeks": 2.0, "Lead_Time_StdDev_Weeks": 0.4},
        {"SKU": "SKU-003", "Description": "Organic Matcha Tea Powder 100g", "Category": "Pantry", "Supplier_ID": "SUPP-303", "Unit_Cost_USD": 8.50, "Selling_Price_USD": 22.00, "Lead_Time_Weeks": 2.0, "Lead_Time_StdDev_Weeks": 0.5},
        {"SKU": "SKU-004", "Description": "Smart Fitness Tracker Band", "Category": "Electronics", "Supplier_ID": "SUPP-101", "Unit_Cost_USD": 20.00, "Selling_Price_USD": 49.00, "Lead_Time_Weeks": 1.0, "Lead_Time_StdDev_Weeks": 0.2},
        {"SKU": "SKU-005", "Description": "Biodegradable Bamboo Coffee Mug", "Category": "Housewares", "Supplier_ID": "SUPP-404", "Unit_Cost_USD": 3.00, "Selling_Price_USD": 12.00, "Lead_Time_Weeks": 1.0, "Lead_Time_StdDev_Weeks": 0.3}
    ]
    df_sku = pd.DataFrame(sku_data)
    
    # 2. Inventory Status
    inventory_data = [
        {"SKU": "SKU-001", "DC": "DC-EAST", "Current_Stock_Units": 200, "Safety_Stock_Units": 50, "Reorder_Point_Units": 80, "Reorder_Quantity_Units": 150, "Weekly_Demand_StdDev_Units": 12.5},
        {"SKU": "SKU-002", "DC": "DC-EAST", "Current_Stock_Units": 120, "Safety_Stock_Units": 40, "Reorder_Point_Units": 60, "Reorder_Quantity_Units": 100, "Weekly_Demand_StdDev_Units": 18.0},
        {"SKU": "SKU-003", "DC": "DC-WEST", "Current_Stock_Units": 50, "Safety_Stock_Units": 30, "Reorder_Point_Units": 60, "Reorder_Quantity_Units": 120, "Weekly_Demand_StdDev_Units": 15.0},
        {"SKU": "SKU-004", "DC": "DC-EAST", "Current_Stock_Units": 10, "Safety_Stock_Units": 40, "Reorder_Point_Units": 50, "Reorder_Quantity_Units": 100, "Weekly_Demand_StdDev_Units": 10.0},
        {"SKU": "SKU-005", "DC": "DC-EAST", "Current_Stock_Units": 15, "Safety_Stock_Units": 25, "Reorder_Point_Units": 35, "Reorder_Quantity_Units": 80, "Weekly_Demand_StdDev_Units": 8.0},
        {"SKU": "SKU-005", "DC": "DC-WEST", "Current_Stock_Units": 300, "Safety_Stock_Units": 40, "Reorder_Point_Units": 80, "Reorder_Quantity_Units": 150, "Weekly_Demand_StdDev_Units": 5.0}
    ]
    df_inventory = pd.DataFrame(inventory_data)
    
    # Set dates relative to today
    today = datetime.date.today()
    next_monday = today + datetime.timedelta(days=(7 - today.weekday()) % 7)
    if next_monday == today:
        next_monday = today + datetime.timedelta(days=7)
        
    # 3. Demand Forecast (12 weeks forward)
    demand_records = []
    for week in range(12):
        current_date = next_monday + datetime.timedelta(weeks=week)
        date_str = current_date.strftime("%Y-%m-%d")
        
        demand_records.append({"SKU": "SKU-001", "DC": "DC-EAST", "Week_Start_Date": date_str, "Forecasted_Demand_Units": 60})
        
        # SKU-002: Spikes to 200/week on Week 4 & 5
        demand = 40
        if 4 <= week <= 5:
            demand = 200
        demand_records.append({"SKU": "SKU-002", "DC": "DC-EAST", "Week_Start_Date": date_str, "Forecasted_Demand_Units": demand})
        
        demand_records.append({"SKU": "SKU-003", "DC": "DC-WEST", "Week_Start_Date": date_str, "Forecasted_Demand_Units": 50})
        demand_records.append({"SKU": "SKU-004", "DC": "DC-EAST", "Week_Start_Date": date_str, "Forecasted_Demand_Units": 40})
        demand_records.append({"SKU": "SKU-005", "DC": "DC-EAST", "Week_Start_Date": date_str, "Forecasted_Demand_Units": 25})
        demand_records.append({"SKU": "SKU-005", "DC": "DC-WEST", "Week_Start_Date": date_str, "Forecasted_Demand_Units": 20})
        
    df_demand = pd.DataFrame(demand_records)
    
    # 4. Supply Pipeline
    pipeline_data = [
        {"SKU": "SKU-001", "DC": "DC-EAST", "Order_ID": "PO-991", "Quantity_Units": 150, "Expected_Delivery_Week_Start": (next_monday + datetime.timedelta(weeks=4)).strftime("%Y-%m-%d"), "Status": "In Transit"},
        {"SKU": "SKU-002", "DC": "DC-EAST", "Order_ID": "PO-992", "Quantity_Units": 100, "Expected_Delivery_Week_Start": (next_monday + datetime.timedelta(weeks=8)).strftime("%Y-%m-%d"), "Status": "Placed"},
        {"SKU": "SKU-003", "DC": "DC-WEST", "Order_ID": "PO-993", "Quantity_Units": 120, "Expected_Delivery_Week_Start": (next_monday + datetime.timedelta(weeks=6)).strftime("%Y-%m-%d"), "Status": "Delayed"},
    ]
    df_pipeline = pd.DataFrame(pipeline_data)
    
    # 5. Historical Sales (12 weeks backward)
    history_records = []
    for week in range(1, 13):
        hist_date = next_monday - datetime.timedelta(weeks=week)
        date_str = hist_date.strftime("%Y-%m-%d")
        
        # Generate sales with slight variance from typical forecast to simulate MAPE error
        # SKU-001: Steady 60 forecast. Actuals 55-65.
        history_records.append({"SKU": "SKU-001", "DC": "DC-EAST", "Week_Start_Date": date_str, "Forecasted_Demand_Units": 60, "Actual_Sales_Units": 63})
        # SKU-002: Steady 40 forecast. Actuals 38-48.
        history_records.append({"SKU": "SKU-002", "DC": "DC-EAST", "Week_Start_Date": date_str, "Forecasted_Demand_Units": 40, "Actual_Sales_Units": 44})
        # SKU-003: Steady 50 forecast. Actuals 42-55.
        history_records.append({"SKU": "SKU-003", "DC": "DC-WEST", "Week_Start_Date": date_str, "Forecasted_Demand_Units": 50, "Actual_Sales_Units": 48})
        # SKU-004: Steady 40 forecast. Actuals 35-45.
        history_records.append({"SKU": "SKU-004", "DC": "DC-EAST", "Week_Start_Date": date_str, "Forecasted_Demand_Units": 40, "Actual_Sales_Units": 37})
        # SKU-005: Steady 25 forecast at DC-EAST, 20 at DC-WEST
        history_records.append({"SKU": "SKU-005", "DC": "DC-EAST", "Week_Start_Date": date_str, "Forecasted_Demand_Units": 25, "Actual_Sales_Units": 24})
        history_records.append({"SKU": "SKU-005", "DC": "DC-WEST", "Week_Start_Date": date_str, "Forecasted_Demand_Units": 20, "Actual_Sales_Units": 19})
        
    df_history = pd.DataFrame(history_records)
    
    # Create excel workbook
    wb = openpyxl.Workbook()
    
    # 1. Sheet README
    ws_readme = wb.active
    ws_readme.title = "README"
    ws_readme.views.sheetView[0].showGridLines = True
    
    ws_readme["A2"] = "StockSentinel - Integrated Supply Chain Database"
    ws_readme["A2"].font = title_font
    ws_readme["A3"] = "Contains operational sheets for OOS prediction, forecasting audit, and inventory optimization."
    ws_readme["A3"].font = subtitle_font
    
    # Excel Sheets write helper
    def write_sheet(df, title):
        ws = wb.create_sheet(title=title)
        ws.views.sheetView[0].showGridLines = True
        
        headers = list(df.columns)
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = HEADER_FILL
            cell.alignment = center_align
            cell.border = header_border
        
        for row_idx, row in enumerate(df.itertuples(index=False), start=2):
            is_zebra = (row_idx % 2 == 0)
            row_fill = ZEBRA_FILL if is_zebra else WHITE_FILL
            
            for col_idx, value in enumerate(row, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.font = regular_font
                cell.fill = row_fill
                cell.border = thin_border
                
                header_name = headers[col_idx - 1]
                if "SKU" in header_name or "DC" in header_name or "ID" in header_name or "Status" in header_name:
                    cell.alignment = center_align
                elif "Date" in header_name or "Week_Start" in header_name:
                    cell.alignment = center_align
                elif "Cost" in header_name or "Price" in header_name:
                    cell.number_format = "$#,##0.00"
                    cell.alignment = right_align
                elif "Units" in header_name or "Stock" in header_name or "Point" in header_name or "Quantity" in header_name or "Weeks" in header_name or "Demand" in header_name:
                    cell.number_format = "#,##0.0" if "StdDev" in header_name or "Weeks" in header_name else "#,##0"
                    cell.alignment = right_align
                else:
                    cell.alignment = left_align
                    
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                if cell.value is not None:
                    max_len = max(max_len, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = max(max_len, 12) + 4
        ws.row_dimensions[1].height = 26

    # Write sheets
    write_sheet(df_sku, "SKU_Metadata")
    write_sheet(df_inventory, "Inventory_Status")
    write_sheet(df_demand, "Demand_Forecast")
    write_sheet(df_pipeline, "Supply_Pipeline")
    write_sheet(df_history, "Historical_Sales")
    
    # Save Workbook
    wb.save(filename)
    print(f"[SUCCESS] Integrated database saved as: {filename}")

if __name__ == "__main__":
    create_supply_chain_db()
