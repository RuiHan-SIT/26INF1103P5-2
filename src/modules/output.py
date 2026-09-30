import os
from datetime import datetime

STATUS_READY = "Ready for Handover"
STATUS_CLARIFY = "Needs Clarification"
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
    print("\n" + "=" * WIDTH)
    print(f"STATUS: {status.upper()}")
    print("=" * WIDTH)
 
    if status == STATUS_CLARIFY:
        missing = result.get("missing_info", [])
        if missing:
            print("\nClarification needed:")
            for item in missing:
                print(f"  - {str(item)}")
        print("\nPlease resolve the items above, then run the handover again.")
 
 
def generate_summary_txt(result, output_dir=SUMMARY_DIR):
    #write the handover summary to a .txt file
    #only generates when status is Ready and returns the file path, or None
    if result.get("status") != STATUS_READY:
        print("\nCannot generate summary: handover is not yet Ready.")
        return None
 
    tasks = result.get("tasks", [])
    now = datetime.now()
    #generate a unique filename based on the current timestamp
    filename = f"handover_summary_{now:%Y-%m-%d_%H%M%S}.txt"
 
    lines = [
        "HANDOVER SUMMARY",
        "=" * WIDTH,
        f"Generated : {now:%Y-%m-%d %H:%M}",
        f"Status    : {result.get('status')}",
        f"Tasks     : {len(tasks)}",
        "",
    ]
    for priority in ("High", "Medium", "Low"):
        group = [t for t in tasks if _clean(t.get("priority")).title() == priority]
        if not group:
            continue
        lines.append(f"{priority.upper()} PRIORITY")
        lines.append("-" * WIDTH)
        for t in group:
            lines.append(f"* {_clean(t.get('task'))}")
            if t.get("description"):
                lines.append(f"    Description : {_clean(t.get('description'))}")
            lines.append(f"    Owner(s)    : {_owners_str(t.get('owners'))}")
            lines.append(f"    Deadline    : {_clean(t.get('deadline'))}")
            if t.get("comments"):
                lines.append(f"    Comments    : {_clean(t.get('comments'))}")
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
    if result.get("status") == STATUS_READY:
        path = generate_summary_txt(result)
        if path:
            print(f"\nHandover summary saved to: {path}")
 