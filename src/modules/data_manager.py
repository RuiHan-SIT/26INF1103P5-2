#Importing of the relevant modules
import json
import os
from datetime import date 

DEFAULT_DATA_FILE = "handovers.json"

def load_records(filepath=DEFAULT_DATA_FILE):
    """Load all handover records from the JSON file
    Returns an empty  list if the file doesn't exist yet"""
    #1.1 The first requirement to prevent crashing: 
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
    # Loads the existing records, so we can add to them, not overwrite them
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


def update_record(record_id, updates, filepath=DEFAULT_DATA_FILE):
    """Update an existing handover record identified by its id.
    'updates' is a dict of the fields to change (e.g. {"task": "New task name"}).
    Returns True if the record was found and saved, False otherwise."""

    #4.1 Reject updates that are not a dictionary of fields
    if not isinstance(updates, dict):
        return False

    #4.2 Load the current records so we can search through them
    records = load_records(filepath)

    #4.3 Look for the record with matching id
    for record in records:
        #4.4 Skip anything that is not a proper record (e.g. a stray string in the JSON)
        if not isinstance(record, dict):
            continue

        #4.5 .get() returns None instead of raising KeyError if "id" is missing
        if record.get("id") == record_id:
            #4.6 Merge the new values, but never let an update change the id itself
            safe_updates = {k: v for k, v in updates.items() if k != "id"}
            record.update(safe_updates)
            #4.7 Save the whole list back and report whether the save worked
            return save_records(records, filepath)

    #4.8 No record with that id was found - nothing to update
    return False
