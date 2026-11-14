from .input_validator import InputValidator
from .file_validator import FileValidator
from .document_reader import DocumentReader

class HandoverInputHandler:

    def __init__(
        self,
        input_validator=None,
        file_validator=None,
        document_reader=None,
    ):
        self.input_validator = input_validator or InputValidator()
        self.file_validator = file_validator or FileValidator()
        self.document_reader = document_reader or DocumentReader()

    def process_upload(self, uploaded_file):

        #step 1: validate file type and size
        self.file_validator.validate_file(uploaded_file)

        #step 2: read the uploaded document
        content = self.document_reader.read_document(uploaded_file)

        #step 3: check for sensitive information
        if self.input_validator.validate_user_input(content):
            raise ValueError(
                "Sensitive information detected in uploaded document."
            )

        return content

    def validate_clarification_answers(self, answers):
        for item in answers:
            answer = item.get("answer", "")

            if not isinstance(answer, str):
                raise ValueError(
                    "Clarification answers must contain text."
                )

            if self.input_validator.validate_user_input(answer):
                raise ValueError(
                    "Sensitive information detected in clarification answer."
                )
        return True
        
    def validate_manual_input(self, name, department, employee_id):

        errors = {}

        if not self.input_validator.validate_name(name):
            errors ["name"] = "invalid name."

        if not self.input_validator.validate_department(department):
            errors["department"] = "invalid department"

        if not self.input_validator.validate_employee_id(employee_id):
            errors["employee_id"] = (
                "employee id must contain exactly 7 digits"
            )

        return errors