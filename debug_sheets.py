import pandas as pd

try:
    xls = pd.ExcelFile("input_template.xlsx")
    print("Sheets in workbook:", xls.sheet_names)
    for name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=name)
        print(f"\nSheet '{name}' columns: {list(df.columns)}")
        print(f"Sheet '{name}' first row: {df.iloc[0].to_dict() if not df.empty else 'Empty'}")
except Exception as e:
    print("Error:", e)
