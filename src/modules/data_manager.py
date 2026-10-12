# ===========================================================================
# Data Manager
# Stores handover records in data/handovers.json and provides the CRUD
# operations used by main.py:
#   Create - save_handover()               (handing over)
#   Read   - get_records_by_employee_id()  (taking over)
#   Update - update_record()               (taking over: who took it over)
#   Delete - delete_record()               (deleting a work)
#            delete_summary_files()        (removes the summary .txt files)
# ===========================================================================

# ===========================================================================
# Setup - imports and paths
# ===========================================================================

import json
import os
from datetime import date, datetime
from pathlib import Path 

from utils.config import DEFAULT_DATA_FILE, DATA_DIR, SUMMARIES_DIR
from utils.logger import logger


# ===========================================================================
# File helpers - read and write the whole JSON file
# Used by the CRUD functions below; main.py does not call these directly.
# ===========================================================================

# Opens the saved JSON file and gives back everything in it as a list.
# If the file doesn't exist yet or is broken, gives back an empty list instead of crashing.
def load_records(filepath=DEFAULT_DATA_FILE):
    #Load all handover records from the JSON file
    #Returns an empty  list if the file doesn't exist yet
    # 1.1 The first requirement to prevent crashing: 
    if not os.path.exists(filepath):
        return []
    
    #1.2 Attempting to open the file safely, and reading it. 
    #Try/except catches cases like if the file exists but it's unreadable
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
    except OSError as err:
        logger.error("Could not read records file %s: %s", filepath, err)
        return []
    
    #1.3 Handling an empty file; A file exists but has no content
    if not content:
        return []
    #1.4 Parsing the JSON, turning raw text into Python data (lists/dictionary)
    #1.4 Handling a corrupted file without crashing
    try:
        data = json.loads(content)
    except json.JSONDecodeError as err:
        logger.error("Corrupted JSON in %s: %s", filepath, err)
        # Create a backup so data is never permanently lost
        backup_path = Path(str(filepath) + ".corrupted.bak")
        try:
            with open(backup_path, "w", encoding="utf-8") as bkp:
                bkp.write(content)
            logger.warning("Corrupted database safely backed up to %s", backup_path)
        except OSError:
            pass
        return []
    #1.5 If the JSON is valid but is not in the form of a list of records
    if not isinstance(data, list):
        logger.error("JSON in %s is not a list of records.", filepath)
        return []
    
    return data

# Takes a list of records and writes it to the JSON file, replacing whatever was there before.
def save_records(records, filepath=DEFAULT_DATA_FILE):
    #Save the full list of handover records to the JSON file
    #Overwrites whatever was previously saved
    #2.1 Writing the records to disk as JSON. "w" mode overwrites the whole file
    #2.1 (unlike "a" which appends) — that matches what "save the full list" means
    try:
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, sort_keys=True)
    except OSError:
        #2.2 Don't crash if the write fails (e.g. disk full, no permission)
        return False

    return True


# ===========================================================================
# CREATE
# ===========================================================================

# Takes a new handover, gives it a unique id and today's date,
# and saves it alongside everything already stored.
def add_record(record, filepath=DEFAULT_DATA_FILE):
    #Add a new handover record to the JSON file. Auto generates the record's id and date, 
    #and saves the updated list.
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

def save_handover(user_details, result, filename, filepath=DEFAULT_DATA_FILE):
    #7.1 Build a handover record from the user's details and the logic
    #manager's result, then save it to the JSON file.
    record = {
        "name": user_details["name"],
        "employee_id": user_details["employee_id"],
        "department": user_details["department"],
        "filename": filename,
        "outstanding_tasks": result["outstanding_tasks"],
        "bau_tasks": result["bau_tasks"],
        "important_information": result["important_information"],
    }
    return add_record(record, filepath)


# ===========================================================================
# READ
# ===========================================================================

# Returns every handover saved by one employee (by their 7-digit employee ID), newest first.
# Called by main.py when taking over.
def get_records_by_employee_id(employee_id, filepath=DEFAULT_DATA_FILE):
    #5.1 Read & return all handover records saved by the said employee, newest first.
    #Returns an empty list if none are found.
    records = load_records(filepath)

    matches = [
        r for r in records
        if isinstance(r, dict) and r.get("employee_id") == employee_id
    ]

    # Highest id = most recently saved, so it comes first
    return sorted(matches, key=lambda r: r.get("id", 0), reverse=True)


# Returns one record by its JSON "id" (1, 2, 3...), not by employee ID.
# Not currently called by main.py.
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


# ===========================================================================
# UPDATE
# ===========================================================================

# Given a record id and the fields to change, finds that record and edits just
# those fields, without touching the rest. Called by main.py when taking over.
def update_record(record_id, updates, filepath=DEFAULT_DATA_FILE):
    #Update an existing handover record identified by its id.
    #'updates' is a dict of the fields to change (e.g. {"task": "New task name"}).
    #Returns True if the record was found and saved, False otherwise.

    #7.1 Reject updates that are not a dictionary of fields
    if not isinstance(updates, dict):
        return False

    #7.2 Load the current records so we can search through them
    records = load_records(filepath)

    #7.3 Look for the record with matching id
    for record in records:
        #7.4 Skip anything that is not a proper record (e.g. a stray string in the JSON)
        if not isinstance(record, dict):
            continue

        #7.5 .get() returns None instead of raising KeyError if "id" is missing
        if record.get("id") == record_id:
            #7.6 Merge the new values, but never let an update change the id itself
            safe_updates = {k: v for k, v in updates.items() if k != "id"}
            record.update(safe_updates)
            #7.7 Save the whole list back and report whether the save worked
            return save_records(records, filepath)

    #7.8 No record with that id was found - nothing to update
    return False


# ===========================================================================
# DELETE
# ===========================================================================

# Deletes every record whose "id" or "employee_id" matches the identifier.
# Called by main.py when deleting a work.
def delete_record(identifier: str, filepath: str = DEFAULT_DATA_FILE) -> bool:
    #Deletes records where either 'id' or 'employee_id' matches identifier.#
    if not identifier:
        return False

    records = load_records(filepath)
    if not isinstance(records, list):
        return False

    updated_records = [
        r for r in records
        if not (
            isinstance(r, dict)
            and (r.get("id") == identifier or r.get("employee_id") == identifier)
        )
    ]

    if len(updated_records) == len(records):
        return False

    return save_records(updated_records, filepath)

def add_viewer(record_id, name, employee_id, filepath=DEFAULT_DATA_FILE):
    # Retrieve the selected handover record
    record = get_record_by_id(record_id, filepath)

    if record is None:
        return False

    # Retrieve existing viewing history, or start an empty list
    viewing_history = record.get("viewed_by", [])

    if not isinstance(viewing_history, list):
        viewing_history = []

    # Add the new viewer
    viewing_history.append({
        "name": name,
        "employee_id": employee_id,
        "viewed_date": datetime.now().strftime("%d %b %Y %H:%M:%S")
    })

    # Update the record using the existing CRUD Update function
    return update_record(
        record_id,
        {"viewed_by": viewing_history},
        filepath
    )

# Removes every summary .txt file in data/summaries that belongs to the said employee.
def delete_summary_files(employee_id, summaries_dir=SUMMARIES_DIR):
    #9.1 Summary files are named <date>_<name>_<employee_id>_<time>.txt
    #Returns how many files were deleted.
    if not employee_id:
        return 0

    folder = Path(summaries_dir)
    if not folder.exists():
        return 0

    deleted = 0
    for file in folder.glob(f"*_{employee_id}_*.txt"):
        try:
            file.unlink()  # unlink() deletes the file
            deleted += 1
        except OSError as err:
            #9.2 Don't crash if a file can't be deleted (e.g. it's open in another program)
            logger.error("Could not delete summary file %s: %s", file, err)

    return deleted
