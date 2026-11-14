from unittest.mock import MagicMock, patch

import pytest
from django.db import OperationalError

from apps.handovers.data_manager.data_manager_error import DataManagerError
from apps.handovers.data_manager.handover_query import HandoverQuery
from apps.handovers.data_manager.handover_repository import HandoverRepository


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


# A locked or missing database while saving a handover gives a DataManagerError, and the upload is not linked
@patch("apps.handovers.data_manager.handover_repository.transaction.atomic")
@patch("apps.handovers.data_manager.handover_repository.Handover.objects.create")
def test_save_handover_database_error(mock_create, mock_atomic):
    mock_create.side_effect = OperationalError("database is locked")
    employee = MagicMock()
    upload = MagicMock()

    with pytest.raises(DataManagerError):
        HandoverRepository().save_handover(employee, upload, {"outstanding_tasks": [], "bau_tasks": []})

    upload.save.assert_not_called()


# Searching with text that isn't a handover number, e.g a string, returns no handovers
@patch("apps.handovers.data_manager.handover_query.Handover.objects.filter")
def test_search_handovers_invalid_text(mock_filter):
    employee = MagicMock()

    result = HandoverQuery().search_handovers(employee, search_text="abc")

    assert result == []


# Searching "H-0007" is understood as handover number 7, so the query filters by that ID
@patch("apps.handovers.data_manager.handover_query.Handover.objects.filter")
def test_search_handovers_by_number(mock_filter):
    employee = MagicMock()
    handovers = mock_filter.return_value.annotate.return_value

    HandoverQuery().search_handovers(employee, search_text="H-0007")

    handovers.filter.assert_called_once_with(pk=7)
