from unittest.mock import patch

import pytest
from django.db import OperationalError

from apps.handovers.data_manager.data_manager_error import DataManagerError
from apps.handovers.data_manager.handover_query import HandoverQuery


# Tests that DataManagerError gives the right message and is a type of Exception
def test_data_manager_error_message():
    error = DataManagerError("save the handover")

    assert isinstance(error, Exception)
    assert str(error) == "Could not save the handover because of a database problem. Please try again later."


# A locked or missing database while reading employees gives a DataManagerError instead of crashing
@patch("apps.handovers.data_manager.handover_query.Employee.objects.all")
def test_all_employees_database_error(mock_all):
    mock_all.side_effect = OperationalError("database is locked")

    with pytest.raises(DataManagerError):
        HandoverQuery().all_employees()
