from django.core.files.uploadedfile import UploadedFile
from .input_validator import InputValidator
from .file_validator import FileValidator
from .document_reader import DocumentReader

class HandoverInputHandler:

    def __init__(self) -> None:
        self.input_validator = InputValidator()
        self.file_validator = FileValidator()
        self.document_reader = DocumentReader()

    def process_upload(self, uploaded_file: UploadedFile) -> str:

        #step 1: validate file type and size
        self.file_validator.validate_file(uploaded_file)

        #step 2: read the uploaded document
        content: str = self.document_reader.read_document(uploaded_file)

        #step 3: check for sensitive information
        if self.input_validator.validate_user_input(content): #double checks if there are any sensitive info in the document
            raise ValueError(
                "Sensitive information detected in uploaded document."
            )

        return content

    def validate_clarification_answers(self, answers: list[dict[str, object]]) -> bool: #checks if the clarifacation answers are valid
        
        for item in answers: 
            answer = item.get("answer", "")

            if not isinstance(answer, str): #ensures that the clarification is answered
                raise ValueError(
                    "Clarification answers must contain text."
                )

            if self.input_validator.validate_user_input(answer): #ensures there is no sensitive info in answer 
                raise ValueError(
                    "Sensitive information detected in clarification answer."
                )
        return True
        
    def validate_manual_input(self, name: str, department: str, employee_id: str) -> dict[str, str]:

        errors: dict[str, str] = {}

        if not self.input_validator.validate_name(name):
            errors ["name"] = "invalid name."

        if not self.input_validator.validate_department(department):
            errors["department"] = "invalid department"

        if not self.input_validator.validate_employee_id(employee_id):
            errors["employee_id"] = (
                "employee id must contain exactly 7 digits"
            )

        return errors