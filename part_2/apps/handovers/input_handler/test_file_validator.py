
import unittest
from io import BytesIO

from apps.handovers.input_handler.file_validator import FileValidator


class TestFileValidator(unittest.TestCase):

    def setUp(self):
        self.validator = FileValidator()

    def create_file(self, name, content):
        file = BytesIO(content)
        file.name = name
        file.size = len(content)
        return file

    def test_valid_txt(self):
        file = self.create_file("handover.txt", b"Test handover")
        self.assertTrue(self.validator.validate_file(file))

    def test_valid_docx(self):
        file = self.create_file("handover.docx", b"Test content")
        self.assertTrue(self.validator.validate_file(file))

    def test_invalid_pdf(self):
        file = self.create_file("handover.pdf", b"PDF content")
        with self.assertRaises(ValueError):
            self.validator.validate_file(file)

    def test_empty_txt(self):
        file = self.create_file("empty.txt", b"")
        with self.assertRaises(ValueError):
            self.validator.validate_file(file)

    def test_large_file(self):
        file = self.create_file(
            "large.txt",
            b"A" * (10 * 1024 * 1024 + 1)
        )
        with self.assertRaises(ValueError):
            self.validator.validate_file(file)

    def test_missing_file(self):
        with self.assertRaises(ValueError):
            self.validator.validate_file(None)


if __name__ == "__main__":
    unittest.main()
