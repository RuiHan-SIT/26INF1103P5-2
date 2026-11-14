from apps.handovers.data_manager.data_manager_error import DataManagerError


# Tests that DataManagerError gives the right message and is a type of Exception
def test_data_manager_error_message():
    error = DataManagerError("save the handover")

    assert isinstance(error, Exception)
    assert str(error) == "Could not save the handover because of a database problem. Please try again later."
