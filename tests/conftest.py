import sys                                                                                                                                              
from pathlib import Path                                                                                                                                
from datetime import date, timedelta                                                                                                                    
import pytest  
PROJECT_ROOT = Path(__file__).resolve().parents[1]                                                                                     
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# ===========================================================================
# Helper functions
# ===========================================================================

def make_outstanding_task(
    task="Test task",
    description="Test description",
    owners=None,
    deadline=None,
):
    """Create sample outstanding task data for testing."""
    if owners is None:
        owners = ["Alex"]

    if deadline is None:
        deadline = (date.today() + timedelta(days=7)).strftime("%d/%m/%Y")

    return {
        "task": task,
        "description": description,
        "owners": owners,
        "deadline": deadline,
    }


def make_bau_task(
    task="Routine task",
    description="Routine description",
    owners=None,
):
    """Create sample BAU task data for testing."""
    if owners is None:
        owners = ["Alex"]

    return {
        "task": task,
        "description": description,
        "owners": owners,
    }