
import unittest
from io import BytesIO

from docx import Document

from part_2.apps.handovers.input_handler.handover_input_handler import HandoverInputHandler


class TestHandoverInputHandler(unittest.TestCase):

    def setUp(self) -> None:
        self.handler = HandoverInputHandler()

    def test_valid_docx_upload(self) -> None:
        # Create a real Word document in memory
        document = Document()
        document.add_paragraph(
            "Complete the security audit report by Friday."
        )

        uploaded_file = BytesIO()
        document.save(uploaded_file)

        uploaded_file.name = "handover.docx"
        uploaded_file.size = len(uploaded_file.getvalue())
        uploaded_file.seek(0)

        # Process the uploaded document
        result = self.handler.process_upload(uploaded_file)

        # Check that the correct text was extracted
        self.assertIn(
            "Complete the security audit report by Friday.",
            result
        )

    def test_sensitive_docx_upload(self) -> None:
        # Create a Word document containing sensitive information
        document = Document()
        document.add_paragraph("Password: Test12345")

        uploaded_file = BytesIO()
        document.save(uploaded_file)

        uploaded_file.name = "handover.docx"
        uploaded_file.size = len(uploaded_file.getvalue())
        uploaded_file.seek(0)

        # Check that sensitive information is rejected
        with self.assertRaises(ValueError):
            self.handler.process_upload(uploaded_file)
    
    def test_corrupted_docx_upload(self) -> None:
        # Simulate a corrupted Word document
        uploaded_file = BytesIO(b"This is not a real DOCX file")
        uploaded_file.name = "corrupted.docx"
        uploaded_file.size = len(uploaded_file.getvalue())
        uploaded_file.seek(0)

        # Check that the corrupted file is rejected
        with self.assertRaisesRegex(
            ValueError,
            "Unable to read DOCX file"
        ):
            self.handler.process_upload(uploaded_file)

    def test_invalid_pdf_upload(self) -> None:
        uploaded_file = BytesIO(b"Test PDF content")
        uploaded_file.name = "handover.pdf"
        uploaded_file.size = len(uploaded_file.getvalue())
        uploaded_file.seek(0)

        with self.assertRaisesRegex(
            ValueError,
            "Invalid file type"
        ):
            self.handler.process_upload(uploaded_file)
    
    def test_missing_file_upload(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "No file uploaded"
        ):
            self.handler.process_upload(None)
    
    def test_valid_clarification_answers(self) -> None:
        answers = [
            {"answer": "Complete the report by Friday."},
            {"answer": "Sarah Lee will review the document."}
        ]

        result = self.handler.validate_clarification_answers(answers)

        self.assertTrue(result)

    def test_sensitive_second_clarification_answer(self) -> None:
        answers = [
            {"answer": "Complete the report by Friday."},
            {"answer": "Password: Test12345"}
        ]

        with self.assertRaisesRegex(
            ValueError,
            "Sensitive information detected"
        ):
            self.handler.validate_clarification_answers(answers)
    
    def test_non_text_clarification_answer(self) -> None:
        answers = [
            {"answer": 12345}
        ]

        with self.assertRaisesRegex(
            ValueError,
            "Clarification answers must contain text"
        ):
            self.handler.validate_clarification_answers(answers)

    def test_invalid_manual_input(self) -> None:
        errors = self.handler.validate_manual_input(
            name="12345",
            department="!!!",
            employee_id="123"
        )

        self.assertIn("name", errors)
        self.assertIn("department", errors)
        self.assertIn("employee_id", errors)
    
    def test_valid_manual_input(self) -> None:
        errors = self.handler.validate_manual_input(
            name="Alice Tan",
            department="IT Security",
            employee_id="1234567"
        )

        self.assertEqual(errors, {})
if __name__ == "__main__":
    unittest.main()
