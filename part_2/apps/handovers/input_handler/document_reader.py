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

        content_parts = []

        for paragraph in document.paragraphs:
             if paragraph.text.strip():
                  content_parts.append(paragraph.text.strip())

        field_names = [
             "Task Name",
             "Description",
             "Task Owner(s)",
             "Task Type",
             "Deadline"
             "Frequency",
             "Start Date",
             "End Date"
        ]

        task_count = 0

        for table in document.tables:

             for row in table.rows[1:]:
                  values = [
                       cell.text.strip()
                       for cell in row.cells
                  ]

                  if not any(values):
                       continue

                  task_count += 1
                  content_parts.append(f"\nTask {task_count}:")

                  for field, value in zip(field_names, values):
                       content_parts.append(
                            f"(field): {value}"
                       )
        if document.tables and task_count == 0:
            raise ValueError(
                "The DOCX template contains no filled-in tasks."
            )

        content = "\n".join(content_parts)

        if not content.strip():
             raise ValueError(
                  "The DOCX file contains no readable text."
             )

        return content