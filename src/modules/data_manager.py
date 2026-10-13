# ===========================================================================
# Setup - imports and paths
# ===========================================================================

import json
import os
from datetime import date, datetime
from pathlib import Path

from utils.config import DEFAULT_DATA_FILE, DATA_DIR, SUMMARIES_DIR
from utils.logger import logger

# Registered employees (name and department for each employee ID)
EMPLOYEES_FILE = DATA_DIR / "employees.json"


# ===========================================================================
# File helpers - read and write the whole JSON file
# Used by the CRUD functions below; main.py does not call these directly.
# ===========================================================================

# Opens the saved JSON file and gives back everything in it as a list.
# If the file doesn't exist yet or is broken, gives back an empty list instead of crashing.
def load_records(filepath=DEFAULT_DATA_FILE):
    # If the file doesn't exist yet (nothing saved so far), there are no records
    if not os.path.exists(filepath):
        return []
    
    # Attempting to open the file safely, and reading it.
    # Try/except catches cases like if the file exists but it's unreadable
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
    except OSError as err:
        logger.error("Could not read records file %s: %s", filepath, err)
        return []
    
    # Handling an empty file; A file exists but has no content
    if not content:
        return []
    # Parsing the JSON, turning raw text into Python data (lists/dictionary)
    # Handling a corrupted file without crashing
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
    # If the JSON is valid but is not in the form of a list of records
    if not isinstance(data, list):
        logger.error("JSON in %s is not a list of records.", filepath)
        return []
    
    return data

# Takes a list of records and writes it to the JSON file, replacing whatever was there before.
def save_records(records, filepath=DEFAULT_DATA_FILE):
    # Save the full list of handover records to the JSON file
    # Overwrites whatever was previously saved
    # Writing the records to disk as JSON. "w" mode overwrites the whole file
    try:
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, sort_keys=True)
    except OSError:
        # Don't crash if the write fails (e.g. disk full, no permission)
        return False

    return True


# ===========================================================================
# EMPLOYEE REGISTRY (Read)
# Looks up employees in data/employees.json so the program can confirm
# who is creating, viewing or deleting a handover.
# ===========================================================================

# Loads every registered employee as a dictionary.
# Returns {} if the file doesn't exist, or None if it can't be read.
def load_employees(filepath=EMPLOYEES_FILE):
    # Load registered employees
    if not Path(filepath).exists():
        return {}

    try:
        with open(filepath, "r", encoding="utf-8") as file:
            employees = json.load(file)

        return employees if isinstance(employees, dict) else {}

    except (OSError, json.JSONDecodeError) as err:
        logger.error("Could not load employee registry: %s", err)
        return None


# Returns the said employee's dictionary
# or None if the ID isn't registered. Called by input_handler for options 1-3.
def get_employee(employee_id, filepath=EMPLOYEES_FILE):
    # Retrieve employee details from the existing company database
    employees = load_employees(filepath)

    if employees is None:
        return None

    return employees.get(employee_id)


# ===========================================================================
# CREATE
# ===========================================================================

# Takes a new handover, gives it a unique id and today's date,
# and saves it alongside everything already stored.
def add_record(record, filepath=DEFAULT_DATA_FILE):
    # Load the existing records, so we can add to them, not overwrite them
    records = load_records(filepath)

    # Next id = highest existing id + 1 (default=0 gives 1 when there are no records yet)
    next_id = max(
        (r.get("id", 0) for r in records if isinstance(r, dict) and isinstance(r.get("id"), int)),
        default=0
    ) + 1

    # Stamp the new record with its id and today's date
    record["id"] = next_id
    record["saved_date"] = date.today().isoformat()
    records.append(record)
    return save_records(records, filepath)


# Builds a handover record from the user's details, the logic manager's result
# and the summary .txt filename, then saves it with add_record().
# Called by main.py for option 1 (create a new handover).
def save_handover(user_details, result, filename, filepath=DEFAULT_DATA_FILE):
    # Build a handover record from the user's details and the logic
    # manager's result, then save it to the JSON file.
    # "filename" links the record to its summary .txt so it can be updated or deleted later.
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
# Called by main.py for option 2 (view) and option 3 (list handovers to delete).
def get_records_by_employee_id(employee_id, filepath=DEFAULT_DATA_FILE):
    # Read & return all handover records saved by the said employee, newest first.
    # Returns an empty list if none are found.
    records = load_records(filepath)

    matches = [
        r for r in records
        if isinstance(r, dict) and r.get("employee_id") == employee_id
    ]

    # Highest id = most recently saved, so it comes first
    return sorted(matches, key=lambda r: r.get("id", 0), reverse=True)

# Returns one record by its JSON "id" (1, 2, 3...), not by employee ID.
# Used by add_viewer() to fetch the record before updating it.
def get_record_by_id(record_id, filepath=DEFAULT_DATA_FILE):
    # Read. Given an id, return the matching record, or None if no record with that id exists.
    records = load_records(filepath)

    for record in records:
        # Skip anything that isn't a proper record (defensive, same as update/delete)
        if not isinstance(record, dict):
            continue

        if record.get("id") == record_id:
            return record

    # No record with that id was found
    return None


# ===========================================================================
# UPDATE
# ===========================================================================

# Given a record id and the fields to change, finds that record and edits just
# those fields, without touching the rest. Used by add_viewer().
def update_record(record_id, updates, filepath=DEFAULT_DATA_FILE):
    # Update an existing handover record identified by its id.
    # 'updates' is a dict of the fields to change (e.g. {"task": "New task name"}).
    # Returns True if the record was found and saved, False otherwise.

    # Reject updates that are not a dictionary of fields
    if not isinstance(updates, dict):
        return False

    # Load the current records so we can search through them
    records = load_records(filepath)

    # Look for the record with matching id
    for record in records:
        # Skip anything that is not a proper record (e.g. a stray string in the JSON)
        if not isinstance(record, dict):
            continue

        # .get() returns None instead of raising KeyError if "id" is missing
        if record.get("id") == record_id:
            # Merge the new values, but never let an update change the id itself
            safe_updates = {k: v for k, v in updates.items() if k != "id"}
            record.update(safe_updates)
            # Save the whole list back and report whether the save worked
            return save_records(records, filepath)

    # No record with that id was found - nothing to update
    return False


# Adds the current viewer (name, employee ID, date and time) to the handover's
# "viewed_by" list, keeping everyone who viewed it before.
# Called by main.py for option 2 (view a handover).
def add_viewer(record_id, name, employee_id, filepath=DEFAULT_DATA_FILE):
    # Retrieve the selected handover record
    record = get_record_by_id(record_id, filepath)

    if record is None:
        return False

    # Retrieve existing viewing history (start a new list if there is none)
    viewing_history = record.get("viewed_by", [])

    if not isinstance(viewing_history, list):
        viewing_history = []

    # Add the current viewer
    viewing_history.append({
        "name": name,
        "employee_id": employee_id,
        "viewed_date": datetime.now().strftime("%d %b %Y %H:%M:%S")
    })

    # Save the updated viewing history to JSON using update_record()
    return update_record(record_id, {"viewed_by": viewing_history}, filepath)


# ===========================================================================
# DELETE
# ===========================================================================

# Deletes the one handover record with this record id (1, 2, 3...).
# Returns True if it was found and removed, False otherwise.
# Called by main.py for option 3, after the user picks a handover and confirms.
def delete_record(record_id, filepath=DEFAULT_DATA_FILE):
    # Keep every record except the one with the matching id
    records = load_records(filepath)

    updated_records = [
        record for record in records
        if not (
            isinstance(record, dict)
            and record.get("id") == record_id
        )
    ]

    # Nothing was removed, so no record had that id
    if len(updated_records) == len(records):
        return False

    # Save the shorter list back
    return save_records(updated_records, filepath)


# Deletes the summary .txt file linked to a handover (the record's "filename").
# Returns True if it was deleted, False otherwise.
# Called by main.py for option 3, after delete_record().
def delete_summary_files(filename, summaries_dir=SUMMARIES_DIR):
    # Delete only the selected handover summary file
    if not filename:
        return False

    folder = Path(summaries_dir).resolve()
    file_path = (folder / filename).resolve()

    # Safety check: the file must be a .txt directly inside data/summaries
    if file_path.parent != folder or file_path.suffix.lower() != ".txt":
        return False

    # Check whether the file exists
    if not file_path.is_file():
        return False

    try:
        file_path.unlink()
        return True

    except OSError as err:
        # Don't crash if the file can't be deleted (e.g. it's open in another program)
        logger.error("Could not delete summary file %s: %s", file_path, err)
        return False
