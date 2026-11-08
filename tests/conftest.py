import sys
from pathlib import Path

# Make the current logic classes importable by the Part 2 tests.
SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
