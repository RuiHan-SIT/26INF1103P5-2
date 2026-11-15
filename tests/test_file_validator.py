import unittest
from io import BytesIO

from part_2.apps.handovers.input_handler.file_validator import FileValidator

class TestFileValidator(unittest.TestCase):

    def setUp(self) -> None:
        self.validator = FileValidator()

    def test_valid_txt_file(self) -> None:
        uploaded_file = BytesIO(b"Test handover document")
        uploaded_file.name = "handover.txt"
        uploaded_file.size = len(uploaded_file.getvalue())

        result = self.validator.validate_file(uploaded_file)

        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
