import os
import argparse
import sys
from generate_template import create_styled_excel
from src.orchestrator import StockSentinelOrchestrator

def main():
    parser = argparse.ArgumentParser(
        description="StockSentinel: Multi-Agent Supply Chain OOS Prediction & Mitigation Engine."
    )
    parser.add_argument(
        "--input", 
        default="input_template.xlsx",
        help="Path to the input Excel spreadsheet template. (Default: input_template.xlsx)"
    )
    parser.add_argument(
        "--output", 
        default="oos_analysis_report.xlsx",
        help="Path to save the generated executive OOS report. (Default: oos_analysis_report.xlsx)"
    )
    parser.add_argument(
        "--promo-context", 
        default="",
        help="Optional qualitative promo, holiday, or supply disruption context to guide the DemandForecaster Agent."
    )
    
    args = parser.parse_args()
    
    # Auto-generate input template if it doesn't exist yet
    if not os.path.exists(args.input):
        print(f"[INFO] Input file '{args.input}' not found. Generating a new template with realistic supply chain scenarios...")
        try:
            create_styled_excel()
        except Exception as e:
            print(f"[ERROR] Failed to auto-generate template: {e}")
            sys.exit(1)
            
    # Initialize and execute the Multi-Agent orchestrator
    try:
        orchestrator = StockSentinelOrchestrator(
            input_path=args.input,
            output_path=args.output
        )
        orchestrator.run_pipeline(promo_context=args.promo_context)
    except Exception as e:
        print(f"\n[FATAL ERROR] Pipeline execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
