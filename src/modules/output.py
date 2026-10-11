import os
from datetime import datetime

STATUS_COMPLETE = "Handover Complete"
STATUS_INCOMPLETE = "Handover Incomplete"
NOT_SPECIFIED = "Not specified"
WIDTH = 78
SUMMARY_DIR = "data/summaries"

def _clean(value):
    #return a display-safe string; placeholder if empty/missing
    if value is None or str(value).strip() == "":
        return NOT_SPECIFIED
    return str(value).strip()
 
 
def _owners_str(owners):
    if isinstance(owners, list):
        cleaned = [
            name.strip()
            for owner in owners
            if owner
            for name in owner.split(",")
            if name.strip()
        ]
        return ", ".join(cleaned) if cleaned else NOT_SPECIFIED

    if isinstance(owners, str):
        cleaned = [name.strip() for name in owners.split(",") if name.strip()]
        return ", ".join(cleaned) if cleaned else NOT_SPECIFIED

    return _clean(owners)
 
 
def display_status(result):
    #prints the handover status and list missing info if not ready
    status = result.get("status", "Unknown")
    display_status = STATUS_COMPLETE if status in (STATUS_COMPLETE, "complete") else status
    if status == "incomplete":
        display_status = STATUS_INCOMPLETE
    print("\n" + "=" * WIDTH)
    print(f"STATUS: {display_status.upper()}")
    print("=" * WIDTH)
 
    if status in (STATUS_INCOMPLETE, "incomplete"):
        missing = result.get("missing_info", result.get("errors", []))
        if missing:
            print("\nClarification needed:")
            for item in missing:
                if isinstance(item, dict):
                    details = ", ".join(item.get("errors", []))
                    label = item.get("task", item.get("type", "Handover"))
                    print(f"  - {label}: {details or item}")
                else:
                    print(f"  - {str(item)}")
        print("\nPlease resolve the items above, then run the handover again.")


def format_summary(result):
    # Format the handover summary for both file saving and CLI display
    outstanding_tasks = result.get("outstanding_tasks", [])
    bau_tasks = result.get("bau_tasks", [])
    now = datetime.now()

    lines = [
        "=" * WIDTH,
        "HANDOVER SUMMARY",
        "=" * WIDTH,
        f"Generated on  : {now:%Y-%m-%d %H:%M}",
        f"Tasks         : {len(outstanding_tasks) + len(bau_tasks)}",
        "",
    ]

    if outstanding_tasks:
        lines.extend(["OUTSTANDING TASKS", "-" * WIDTH])

        for index, task in enumerate(outstanding_tasks, start=1):
            lines.append(f"Task {index}: {_clean(task.get('task'))}")
            lines.append(f"    Owner       : {_owners_str(task.get('owners'))}")
            lines.append(f"    Description : {_clean(task.get('description'))}")
            lines.append(f"    Deadline    : {_clean(task.get('deadline'))}")
            lines.append("")

    if bau_tasks:
        lines.extend(["ROUTINE TASKS", "-" * WIDTH])

        for index, task in enumerate(bau_tasks, start=1):
            lines.append(f"Task {index}: {_clean(task.get('task'))}")
            lines.append(f"    Owner       : {_owners_str(task.get('owners'))}")
            lines.append(f"    Description : {_clean(task.get('description'))}")
            lines.append("")

    important_information = result.get("important_information", [])

    if important_information:
        lines.extend(["IMPORTANT INFORMATION", "-" * WIDTH])
        lines.extend(f"* {_clean(item)}" for item in important_information)
        lines.append("")

    return "\n".join(lines)

 
def generate_summary_txt(result, user_details, output_dir=SUMMARY_DIR):
    #write the handover summary to a .txt file
    #only generates when status is Complete and returns the file path, or None
    if result.get("status") not in (STATUS_COMPLETE, "complete"):
        print("\nCannot generate summary: handover is not yet Complete.")
        return None
 
    
    outstanding_tasks = result.get("outstanding_tasks", [])
    bau_tasks = result.get("bau_tasks", [])
    now = datetime.now()

    # Generate a filename using the date, employee name, ID and time
    name = "".join(
        char if char.isalnum() or char in " -_" else "_"
        for char in user_details["name"]
    ).strip().replace(" ", "_")

    employee_id = user_details["employee_id"]

    filename = f"{now:%Y-%m-%d}_{name}_{employee_id}_{now:%H-%M-%S}.txt"
 
    try:
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(format_summary(result))
        return path
    except OSError as e:
        print(f"\n[Error] Could not save summary file: {e}")
        return None

 
def show_output(result, user_details, save_file=True):
    #main entry point, called from main.py with the logic manager's result
    if save_file:
        display_status(result)
    
    if result.get("status") in (STATUS_COMPLETE, "complete"):
        if save_file:
            path = generate_summary_txt(result, user_details)
        
            if path:
                print(f"\nHandover file saved to: {os.path.basename(path)}")

        else:
            # Display the handover summary directly in the CLI
            print("\n" + format_summary(result))
