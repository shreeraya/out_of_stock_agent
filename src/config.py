import os
from pathlib import Path
from dotenv import load_dotenv

# Find the project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()  # Fallback to default loading from current working directory

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# LLM Models Configuration
# default to gpt-4o-mini since it's extremely fast and supports structured JSON outputs perfectly
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Simulation settings
SIMULATION_DAYS = int(os.getenv("SIMULATION_DAYS", "30"))

def validate_config():
    """Validates the minimum required configurations for LLM-based agents."""
    if not OPENAI_API_KEY:
        print("[WARNING] OPENAI_API_KEY is not set in the environment or .env file.")
        print("StockSentinel will run deterministic calculations, but LLM analysis (Root Cause and Mitigation) will be skipped.")
        return False
    return True
