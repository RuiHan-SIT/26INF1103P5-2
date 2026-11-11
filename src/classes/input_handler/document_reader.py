from docx import Document
from io import BytesIO

from .file_validator import FileValidator

class DocumentReader:

    def __init__(self):
        self.file_validator = FileValidator()

    def read_document(self, uploaded_file):

        #validate the file before reading
        self.file_validator.validate_file(uploaded_file)

        filename = uploaded_file.name.lower()

        #start reading from the beginnning
        uploaded_file.seek(0)

        if filename.endswith(".txt"):
            return self.read_txt(uploaded_file)
        
        if filename.endswith(".docx"):
                    return self.read_docx(uploaded_file)

    def read_txt(self, uploaded_file):

        try:
            content = uploaded_file.read().decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("The uploaded TXT file is not in UTF-8 encoding.")

        if not content.strip():
            raise ValueError("The uploaded TXT file is empty")

        return content

    def read_docx(self, uploaded_file):

        try:
            document = Document(BytesIO(uploaded_file.read()))

        except Exception as error:
            raise ValueError(
                "Unable to read DOCX file. It may be corrupted."
            ) from error

        extracted_lines = []

        # Read regular paragraphs
        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if text:
                extracted_lines.append(text)

        # Read tables (handover templates store tasks in tables)
        for table in document.tables:
            for row in table.rows:
                row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                cleaned_cells = []
                for cell in row_cells:
                    if not cleaned_cells or cell != cleaned_cells[-1]:
                        cleaned_cells.append(cell)
                if any(cleaned_cells):
                    extracted_lines.append(" | ".join(cleaned_cells))

        content = "\n".join(extracted_lines)

        if not content.strip():
            raise ValueError(
                "The DOCX file contains no readable text or table data."
            )
        return content