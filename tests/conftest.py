import os
import sys
from pathlib import Path

# Make the Django Part 2 app importable by the logic tests.
PART_2_DIR = Path(__file__).resolve().parents[1] / "part_2"
if str(PART_2_DIR) not in sys.path:
    sys.path.insert(0, str(PART_2_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
from django.core.management import call_command

django.setup()
call_command("migrate", verbosity=0, interactive=False)

