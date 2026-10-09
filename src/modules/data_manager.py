#Importing of the relevant modules
import json
import os
from datetime import date 

DEFAULT_DATA_FILE = "handovers.json"

#1. opens the saved JSON file and gives you back everything in it as a list. 
#If the file doesn't exist yet or is broken, it just gives back an empty list instead of crashing.
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

#Takes a list of records and writes it to the JSON file, replacing whatever was there before. 
#Mostly used internally by the other functions, not called directly.
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

#Create. Takes a new handover, gives it a unique id and today's date, 
#and saves it alongside everything already stored.
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
    record["saved_date"] = date.today().isoformat()
    records.append(record)
    return save_records(records, filepath)

#Update. Given an id and the fields you want to change, 
#finds that record and edits just those fields, without touching the rest.
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

def delete_record(record_id, filepath=DEFAULT_DATA_FILE):
    #Delete an existing handover record identified by its id.
    #Returns True if a record was found and deleted, False if no record with that id exists."""
    #5.1 Load the current records so we can search through them
    records = load_records(filepath)

    #5.2 Build a new list that keeps everything EXCEPT the record with the matching id
    updated_records = [r for r in records if not (isinstance(r, dict) and r.get("id") == record_id)]

    #5.3 If nothing changed length, there was no match to delete
    if len(updated_records) == len(records):
        return False

    #5.4 Save the shorter list back
    return save_records(updated_records, filepath)

def get_record_by_id(record_id, filepath=DEFAULT_DATA_FILE):
    #6.1 Read. Given an id, return the matching record, or None if no record with that id exists.
    records = load_records(filepath)

    for record in records:
        #6.2 Skip anything that isn't a proper record (defensive, same as update/delete)
        if not isinstance(record, dict):
            continue

        if record.get("id") == record_id:
            return record

    #No record with that id was found
    return None

def save_handover(user_details, result, filepath=DEFAULT_DATA_FILE):
    #Build a handover record from the user's details and the logic
    #manager's result, then save it to the JSON file."""
    record = {
        "name": user_details["name"],
        "employee_id": user_details["employee_id"],
        "department": user_details["department"],
        "outstanding_tasks": result["outstanding_tasks"],
        "bau_tasks": result["bau_tasks"],
        "important_information": result["important_information"],
    }
    return add_record(record, filepath)