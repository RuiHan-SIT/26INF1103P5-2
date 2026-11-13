# Raised by the data manager when the database is missing, corrupt or locked,so the pages can show a clear message instead of crashing
class DataManagerError(Exception):
    # "action" will indicate what failed
    def __init__(self, action):
        super().__init__(f"Could not {action} because of a database problem. Please try again later.")
