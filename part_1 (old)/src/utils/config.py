from pathlib import Path

# ===========================================================================
# Project Path Configuration
# Central source of truth for all file and directory locations.
# ===========================================================================

# Base directories
SRC_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = SRC_DIR.parent

# Data directories
DATA_DIR = BASE_DIR / "data"
HANDOVERS_DIR = DATA_DIR / "handovers"
SUMMARIES_DIR = DATA_DIR / "summaries"

# Specific file locations
DEFAULT_DATA_FILE = DATA_DIR / "handovers.json"
DOTENV_PATH = BASE_DIR / ".env"

   