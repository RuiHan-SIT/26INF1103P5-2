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
        cleaned = [o.strip() for o in owners if o and o.strip()]
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
 
 
def generate_summary_txt(result, output_dir=SUMMARY_DIR):
    #write the handover summary to a .txt file
    #only generates when status is Complete and returns the file path, or None
    if result.get("status") not in (STATUS_COMPLETE, "complete"):
        print("\nCannot generate summary: handover is not yet Complete.")
        return None
 
    
    outstanding_tasks = result.get("outstanding_tasks", [])
    bau_tasks = result.get("bau_tasks", [])
    now = datetime.now()
    #generate a unique filename based on the current timestamp
    filename = f"handover_summary_{now:%Y-%m-%d_%H%M%S}.txt"
 
    lines = [
        "HANDOVER SUMMARY",
        "=" * WIDTH,
        f"Generated : {now:%Y-%m-%d %H:%M}",
        f"Status    : {STATUS_COMPLETE}",
        f"Tasks     : {len(outstanding_tasks) + len(bau_tasks)}",
        "",
    ]
    if outstanding_tasks:
        lines.extend(["OUTSTANDING TASKS", "-" * WIDTH])
        for task in outstanding_tasks:
            lines.append(f"* {_clean(task.get('task'))}")
            if task.get("description"):
                lines.append(f"    Owner       : {_owners_str(task.get('owners'))}")
                lines.append(f"    Description : {_clean(task.get('description'))}")
                lines.append(f"    Deadline    : {_clean(task.get('deadline'))}")
        lines.append("")

    if bau_tasks:
        lines.extend(["ROUTINE TASKS", "-" * WIDTH])
        for task in bau_tasks:
            lines.append(f"* {_clean(task.get('task'))}")
            if task.get("description"):
                lines.append(f"    Description : {_clean(task.get('description'))}")
                lines.append(f"    Owner     : {_owners_str(task.get('owners'))}")
        lines.append("")

    important_information = result.get("important_information", [])
    if important_information:
        lines.extend(["IMPORTANT INFORMATION", "-" * WIDTH])
        lines.extend(f"* {_clean(item)}" for item in important_information)
        lines.append("")

 
    try:
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return path
    except OSError as e:
        print(f"\n[Error] Could not save summary file: {e}")
        return None
 
 
def show_output(result):
    #main entry point, called from main.py with the logic manager's result
    display_status(result)
    if result.get("status") in (STATUS_COMPLETE, "complete"):
        path = generate_summary_txt(result)
        if path:
            print(f"\nHandover file saved to: {os.path.basename(path)}")

#test code to show output!
if __name__ == "__main__":
    show_output({
        "status": "complete",
        "outstanding_tasks": [{"task": "Stock discrepancy report", "owners": ["John"], "deadline": "19 Oct 2026", "description": "Compare the warehouse count against the inventory spreadsheet."}],
        "bau_tasks": [],
        "important_information": ["Test info"],
    })


# add in main.py 
# from modules import output

# replace the if result["status"] == "incomplete":
#            print("\nHandover is incomplete.")
#            print(pformat(result, sort_dicts=False))
#            for error in result["errors"]:
#                print(error)
#        else:
#            print("\nHandover is complete.")
#            print(pformat(result, sort_dicts=False))

# with 

#         # Display status and generate summary
#        output.show_output(result)
#
#
#
