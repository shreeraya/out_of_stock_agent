import datetime
import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def create_styled_excel():
    # Define color palette (Executive Slate Theme)
    HEADER_FILL = PatternFill(start_color="2C3E50", end_color="2C3E50", fill_type="solid") # Dark Navy/Slate
    ZEBRA_FILL = PatternFill(start_color="F8F9FA", end_color="F8F9FA", fill_type="solid") # Very light gray
    ACCENT_FILL = PatternFill(start_color="EAECEE", end_color="EAECEE", fill_type="solid") # Light gray accent for index/headers
    WHITE_FILL = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
    
    # Text fonts
    FONT_FAMILY = "Segoe UI"
    header_font = Font(name=FONT_FAMILY, size=11, bold=True, color="FFFFFF")
    title_font = Font(name=FONT_FAMILY, size=16, bold=True, color="2C3E50")
    subtitle_font = Font(name=FONT_FAMILY, size=10, italic=True, color="7F8C8D")
    bold_font = Font(name=FONT_FAMILY, size=10, bold=True, color="2C3E50")
    regular_font = Font(name=FONT_FAMILY, size=10, color="2C3E50")
    
    # Alignments
    left_align = Alignment(horizontal="left", vertical="center")
    center_align = Alignment(horizontal="center", vertical="center")
    right_align = Alignment(horizontal="right", vertical="center")
    wrap_left_align = Alignment(horizontal="left", vertical="center", wrap_text=True)
    
    # Borders
    thin_border_side = Side(border_style="thin", color="D5DBDB")
    thin_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    thick_bottom_side = Side(border_style="medium", color="2C3E50")
    header_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thick_bottom_side)
    
    # Prepare Mock Data
    
    # 1. SKU Metadata
    sku_data = [
        {"SKU": "SKU-001", "Description": "Premium Wireless Headphones", "Category": "Electronics", "Supplier_ID": "SUPP-101", "Unit_Cost_USD": 45.00, "Selling_Price_USD": 99.00, "Lead_Time_Days": 7},
        {"SKU": "SKU-002", "Description": "Ergonomic Office Chair", "Category": "Furniture", "Supplier_ID": "SUPP-202", "Unit_Cost_USD": 75.00, "Selling_Price_USD": 180.00, "Lead_Time_Days": 10},
        {"SKU": "SKU-003", "Description": "Organic Matcha Tea Powder 100g", "Category": "Pantry", "Supplier_ID": "SUPP-303", "Unit_Cost_USD": 8.50, "Selling_Price_USD": 22.00, "Lead_Time_Days": 12},
        {"SKU": "SKU-004", "Description": "Smart Fitness Tracker Band", "Category": "Electronics", "Supplier_ID": "SUPP-101", "Unit_Cost_USD": 20.00, "Selling_Price_USD": 49.00, "Lead_Time_Days": 5},
        {"SKU": "SKU-005", "Description": "Biodegradable Bamboo Coffee Mug", "Category": "Housewares", "Supplier_ID": "SUPP-404", "Unit_Cost_USD": 3.00, "Selling_Price_USD": 12.00, "Lead_Time_Days": 6}
    ]
    df_sku = pd.DataFrame(sku_data)
    
    # 2. Inventory Status
    inventory_data = [
        {"SKU": "SKU-001", "DC": "DC-EAST", "Current_Stock_Units": 200, "Safety_Stock_Units": 50, "Reorder_Point_Units": 80, "Reorder_Quantity_Units": 150},
        {"SKU": "SKU-002", "DC": "DC-EAST", "Current_Stock_Units": 120, "Safety_Stock_Units": 40, "Reorder_Point_Units": 60, "Reorder_Quantity_Units": 100},
        {"SKU": "SKU-003", "DC": "DC-WEST", "Current_Stock_Units": 50, "Safety_Stock_Units": 30, "Reorder_Point_Units": 60, "Reorder_Quantity_Units": 120},
        {"SKU": "SKU-004", "DC": "DC-EAST", "Current_Stock_Units": 10, "Safety_Stock_Units": 40, "Reorder_Point_Units": 50, "Reorder_Quantity_Units": 100},
        {"SKU": "SKU-005", "DC": "DC-EAST", "Current_Stock_Units": 15, "Safety_Stock_Units": 25, "Reorder_Point_Units": 35, "Reorder_Quantity_Units": 80},
        {"SKU": "SKU-005", "DC": "DC-WEST", "Current_Stock_Units": 300, "Safety_Stock_Units": 40, "Reorder_Point_Units": 80, "Reorder_Quantity_Units": 150} # Transfer source
    ]
    df_inventory = pd.DataFrame(inventory_data)
    
    # 3. Demand Forecast (30-day projection starting from today)
    start_date = datetime.date.today()
    demand_records = []
    
    for day in range(30):
        current_date = start_date + datetime.timedelta(days=day)
        date_str = current_date.strftime("%Y-%m-%d")
        
        # SKU-001: DC-EAST (Steady demand, well stocked)
        demand_records.append({"SKU": "SKU-001", "DC": "DC-EAST", "Date": date_str, "Forecasted_Demand_Units": 12})
        
        # SKU-002: DC-EAST (Promotional spike starting Day 10)
        # Steady at 8/day, then spikes to 45/day from Day 10 to 14, then back to 8/day
        demand = 8
        if 10 <= day <= 14:
            demand = 45
        demand_records.append({"SKU": "SKU-002", "DC": "DC-EAST", "Date": date_str, "Forecasted_Demand_Units": demand})
        
        # SKU-003: DC-WEST (Steady demand, but supply delay causes stockout)
        # Demand is 10/day
        demand_records.append({"SKU": "SKU-003", "DC": "DC-WEST", "Date": date_str, "Forecasted_Demand_Units": 10})
        
        # SKU-004: DC-EAST (Low initial stock, steady demand)
        # Demand is 8/day
        demand_records.append({"SKU": "SKU-004", "DC": "DC-EAST", "Date": date_str, "Forecasted_Demand_Units": 8})
        
        # SKU-005: DC-EAST & DC-WEST (Stock transfer scenario)
        # DC-EAST demand: 5/day. Stock starts at 15 -> runs dry day 3
        demand_records.append({"SKU": "SKU-005", "DC": "DC-EAST", "Date": date_str, "Forecasted_Demand_Units": 5})
        # DC-WEST demand: 4/day. Stock starts at 300 -> stays completely healthy
        demand_records.append({"SKU": "SKU-005", "DC": "DC-WEST", "Date": date_str, "Forecasted_Demand_Units": 4})
        
    df_demand = pd.DataFrame(demand_records)
    
    # 4. Supply Pipeline
    pipeline_data = [
        # SKU-001: DC-EAST (Order placed, arriving on Day 12 - covers stock perfectly)
        {"SKU": "SKU-001", "DC": "DC-EAST", "Order_ID": "PO-991", "Quantity_Units": 150, "Expected_Delivery_Date": (start_date + datetime.timedelta(days=12)).strftime("%Y-%m-%d"), "Status": "In Transit"},
        
        # SKU-002: DC-EAST (Emergency PO placed late due to lead time, arriving Day 20 - too late for the promotion spike!)
        {"SKU": "SKU-002", "DC": "DC-EAST", "Order_ID": "PO-992", "Quantity_Units": 100, "Expected_Delivery_Date": (start_date + datetime.timedelta(days=20)).strftime("%Y-%m-%d"), "Status": "Placed"},
        
        # SKU-003: DC-WEST (Late supplier delivery - originally expected Day 3, but supplier delayed it to Day 16!)
        {"SKU": "SKU-003", "DC": "DC-WEST", "Order_ID": "PO-993", "Quantity_Units": 120, "Expected_Delivery_Date": (start_date + datetime.timedelta(days=16)).strftime("%Y-%m-%d"), "Status": "Delayed"},
        
        # SKU-004: DC-EAST (No outstanding orders - severe understocking!)
        # SKU-005: DC-EAST & DC-WEST (No outstanding orders)
    ]
    df_pipeline = pd.DataFrame(pipeline_data)
    
    # Create excel workbook
    wb = openpyxl.Workbook()
    
    # 1. Sheet README
    ws_readme = wb.active
    ws_readme.title = "README"
    ws_readme.views.sheetView[0].showGridLines = True
    
    ws_readme["A2"] = "StockSentinel - Multi-Agent Supply Chain OOS Guard"
    ws_readme["A2"].font = title_font
    ws_readme["A3"] = "Input Template & Operating Instructions"
    ws_readme["A3"].font = subtitle_font
    
    instructions = [
        "",
        "Welcome to the StockSentinel Multi-Agent Out-of-Stock (OOS) Predictor framework.",
        "This spreadsheet serves as the template for loading your supply chain data. The Python engine",
        "reads these input sheets, simulates inventory day-by-day, and launches collaborative AI agents",
        "to diagnose root causes and recommend preventive mitigation strategies.",
        "",
        "DIRECTIONS FOR USE:",
        "1. Populate the 4 orange-tabbed sheets with your actual supply chain data.",
        "   - SKU_Metadata: Basic information, unit costs, and supplier lead times for each SKU.",
        "   - Inventory_Status: The current inventory snapshot, safety stock, and reorder triggers.",
        "   - Demand_Forecast: Daily forecasted unit sales for the next 30 days.",
        "   - Supply_Pipeline: Outstanding purchase orders (POs), shipment quantities, and delivery dates.",
        "2. Configure your OpenAI API Key in a '.env' file in the project folder.",
        "3. Run the analysis engine by executing: python run_analysis.py",
        "4. A new styled report ('oos_analysis_report.xlsx') will be generated, containing the",
        "   executive OOS Risk Dashboard, Root Cause Diagnoses, and Action Recommendations.",
        "",
        "MOCK SCENARIOS DEMONSTRATED IN THIS DATASET:",
        "- SKU-001 (DC-EAST): Steady demand & supply pipeline. No stockouts predicted.",
        "- SKU-002 (DC-EAST): Promotional Demand Spike on Days 10-14. Stockout occurs because the PO lead time (10 days)",
        "  prevents replenishment from arriving in time. Needs expedited shipping or earlier ordering.",
        "- SKU-003 (DC-WEST): Late Supplier Delivery. The shipment (PO-993) is delayed until Day 16.",
        "  Inventory runs dry on Day 5 and stays OOS for 11 days. Needs supplier mitigation.",
        "- SKU-004 (DC-EAST): Low Initial Stock. Starting inventory is 10 units with no PO in transit. Runs out on Day 2.",
        "- SKU-005 (DC-EAST): Distribution imbalance. DC-EAST runs dry on Day 3, but DC-WEST has excess safety stock.",
        "  Perfect candidate for an Inter-DC Transfer recommendation."
    ]
    
    for row_idx, line in enumerate(instructions, start=5):
        cell = ws_readme.cell(row=row_idx, column=1, value=line)
        cell.font = regular_font
        if "DIRECTIONS FOR USE:" in line or "MOCK SCENARIOS DEMONSTRATED:" in line:
            cell.font = bold_font
            
    ws_readme.column_dimensions["A"].width = 110
    
    # Styling helper for pandas dataframes
    def write_sheet(df, title, tab_color=None):
        ws = wb.create_sheet(title=title)
        ws.views.sheetView[0].showGridLines = True
        if tab_color:
            ws.sheet_properties.tabColor = tab_color
            
        # Write headers
        headers = list(df.columns)
        for col_idx, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = header_font
            cell.fill = HEADER_FILL
            cell.alignment = center_align
            cell.border = header_border
        
        # Write data rows
        for row_idx, row in enumerate(df.itertuples(index=False), start=2):
            is_zebra = (row_idx % 2 == 0)
            row_fill = ZEBRA_FILL if is_zebra else WHITE_FILL
            
            for col_idx, value in enumerate(row, start=1):
                cell = ws.cell(row=row_idx, column=col_idx, value=value)
                cell.font = regular_font
                cell.fill = row_fill
                cell.border = thin_border
                
                # Format cells based on headers/data types
                header_name = headers[col_idx - 1]
                if "SKU" in header_name or "DC" in header_name or "ID" in header_name or "Status" in header_name:
                    cell.alignment = center_align
                elif "Date" in header_name:
                    cell.alignment = center_align
                elif "Cost" in header_name or "Price" in header_name:
                    cell.number_format = "$#,##0.00"
                    cell.alignment = right_align
                elif "Units" in header_name or "Stock" in header_name or "Point" in header_name or "Quantity" in header_name or "Days" in header_name or "Demand" in header_name:
                    cell.number_format = "#,##0"
                    cell.alignment = right_align
                else:
                    cell.alignment = left_align
                    
        # Adjust column widths
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            # Check length of headers and data
            for cell in col:
                if cell.value is not None:
                    # Special format length checking
                    if isinstance(cell.value, float) and ("Cost" in headers[col[0].column-1] or "Price" in headers[col[0].column-1]):
                        val_str = f"${cell.value:,.2f}"
                    elif isinstance(cell.value, int) and ("Units" in headers[col[0].column-1] or "Stock" in headers[col[0].column-1]):
                        val_str = f"{cell.value:,}"
                    else:
                        val_str = str(cell.value)
                    max_len = max(max_len, len(val_str))
            
            header_val = ws.cell(row=1, column=col[0].column).value
            header_len = len(str(header_val)) if header_val else 0
            ws.column_dimensions[col_letter].width = max(max_len, header_len) + 4
            
        ws.row_dimensions[1].height = 26
        
    # Write sheets with specific tab colors (orange for inputs)
    INPUT_TAB_COLOR = "E67E22" # Soft Orange
    write_sheet(df_sku, "SKU_Metadata", INPUT_TAB_COLOR)
    write_sheet(df_inventory, "Inventory_Status", INPUT_TAB_COLOR)
    write_sheet(df_demand, "Demand_Forecast", INPUT_TAB_COLOR)
    write_sheet(df_pipeline, "Supply_Pipeline", INPUT_TAB_COLOR)
    
    # Save Workbook
    filename = "input_template.xlsx"
    wb.save(filename)
    print(f"[SUCCESS] Beautiful Excel input template saved as: {filename}")

if __name__ == "__main__":
    create_styled_excel()
