import unittest

from part_2.apps.handovers.input_handler.input_validator import InputValidator


class TestInputValidator(unittest.TestCase):

    def setUp(self) -> None:
        self.validator = InputValidator()

    def test_valid_name(self) -> None:
        result = self.validator.validate_name("Alice Tan")
        self.assertTrue(result)
    
    def test_invalid_name(self) -> None:
        result = self.validator.validate_name("12345")
        self.assertFalse(result)

    def test_valid_department(self) -> None:
        result = self.validator.validate_department("IT Security")
        self.assertTrue(result)

    def test_invalid_department(self) -> None:
        result = self.validator.validate_department("12345")
        self.assertFalse(result)

    def test_valid_employee_id(self) -> None:
        result = self.validator.validate_employee_id("1234567")
        self.assertTrue(result)

    def test_invalid_employee_id(self) -> None:
        result = self.validator.validate_employee_id("12345")
        self.assertFalse(result)
    
    def test_sensitive_password(self) -> None:
        text = "Password: Test12345"

        result = self.validator.validate_user_input(text)

        self.assertTrue(result)

    def test_normal_task_description(self) -> None:
        text = "Complete the security audit report by Friday."

        result = self.validator.validate_user_input(text)

        self.assertFalse(result)

    def test_sensitive_nric(self) -> None:
        text = "Employee NRIC: S1234567A"

        result = self.validator.validate_user_input(text)

        self.assertTrue(result)

    def test_lowercase_nric(self) -> None:
        text = "Employee ID: s1234567a"

        result = self.validator.validate_user_input(text)

        self.assertTrue(result)
    
    def test_sensitive_passport(self) -> None:
        text = "Travel Document ID: E1234567A"

        result = self.validator.validate_user_input(text)

        self.assertTrue(result)
    
    def test_whitespace_only_name(self) -> None:
        result = self.validator.validate_name("   ")
        self.assertFalse(result)
    
    def test_employee_id_with_letters(self) -> None:
        result = self.validator.validate_employee_id("12345AB")
        self.assertFalse(result)

    def test_employee_id_too_long(self) -> None:
        result = self.validator.validate_employee_id("12345678")
        self.assertFalse(result)
    
    def test_empty_employee_id(self) -> None:
        result = self.validator.validate_employee_id("")
        self.assertFalse(result)