#Importing of the relevant modules
import json
import os
from datetime import date 

DEFAULT_DATA_FILE = "handovers.json"

def load_records(filepath=DEFAULT_DATA_FILE):
    """Load all handover records from the JSON file
    Returns an empty  list if the file doesn't exist yet"""
    #1.1 The first requirement to prevent crashing
    if not os.path.exists(filepath):
        return[]
    
    #1.2 Attempting to open the file safely, and reading it. Try/except catches cases like if the file exists but it's unreadable
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
    except OSError:
        return[]
    
    #1.3 Handling an empty file; A file exists but has no content
    if not content:
        return[]
    #1.4 Parsing the JSON, turning raw text into Python data (lists/dictionary)
    #1.4 Handling a corrupted file without crashing
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return[]
    #1.5 If the JSON is valid but is not in the form of a list of records
    if not isinstance(data, list):
        return[]
    
    return data


def save_records(records, filepath=DEFAULT_DATA_FILE):
    """Save the full list of handover records to the JSON file
    Overwrites whatever was previously saved"""
    #2.1 Writing the records to disk as JSON. "w" mode overwrites the whole file
    #2.1 (unlike "a" which appends) — that matches what "save the full list" means
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, sort_keys=True)
    except OSError:
        #2.2 Don't crash if the write fails (e.g. disk full, no permission)
        return False

    return True

def add_record(record, filepath=DEFAULT_DATA_FILE):
    """Add a new handover record to the JSON file. Auto generates the record's id and date, and saves the updated list."""
    # Loads the existing records, so we can add to them, not overwrite them"
    records = load_records(filepath)
    
    #3.1 Figuring out the next id: highest existing id + 1, or 1 if there are no records yet
    if records:
        next_id = max(r["id"] for r in records) + 1
    else:
        next_id = 1
    #3.2 Stamp the new record with its id and today's date
    record["id"] = next_id
    record["date"] = date.today().isoformat()
    records.append(record)
    return save_records(records, filepath)