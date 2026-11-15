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
    
    def test_valid_docx_file(self) -> None:
        uploaded_file = BytesIO(b"Test document")
        uploaded_file.name = "handover.docx"
        uploaded_file.size = len(uploaded_file.getvalue())

        result = self.validator.validate_file(uploaded_file)

        self.assertTrue(result)

    def test_invalid_pdf_file(self) -> None:
        uploaded_file = BytesIO(b"Test PDF document")
        uploaded_file.name = "handover.pdf"
        uploaded_file.size = len(uploaded_file.getvalue())

        with self.assertRaises(ValueError):
            self.validator.validate_file(uploaded_file)

    def test_empty_file(self) -> None:
        uploaded_file = BytesIO(b"")
        uploaded_file.name = "empty.txt"
        uploaded_file.size = 0

        with self.assertRaises(ValueError):
            self.validator.validate_file(uploaded_file)

    def test_oversized_file(self) -> None:
        uploaded_file = BytesIO(b"Test document")
        uploaded_file.name = "large.txt"
        uploaded_file.size = 11 * 1024 * 1024

        with self.assertRaises(ValueError):
            self.validator.validate_file(uploaded_file)

    def test_missing_file(self) -> None:
        with self.assertRaises(ValueError):
            self.validator.validate_file(None)

if __name__ == "__main__":
    unittest.main()
