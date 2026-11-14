from docx import Document
from io import BytesIO

from .file_validator import FileValidator

class DocumentReader:

    def __init__(self):
        self.file_validator = FileValidator()

    def read_document(self, uploaded_file):

        #validate the file before reading
        self.file_validator.validate_file(uploaded_file)

        uploaded_file.seek(0)
        return self.read_docx(uploaded_file)

    def _read_cell_value(self, cell):
        value = cell.text.strip()
        if not value:
            dropdown_text = cell._tc.xpath(".//w:sdtContent//w:t")
            value = "".join(part.text or "" for part in dropdown_text).strip()

        # Word displays these defaults until the user chooses a dropdown value.
        if value.lower() in ("select type", "select frequency"):
            return ""
        return value

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
             "Deadline",
             "Frequency",
             "Start Date",
             "End Date"
        ]

        task_count = 0

        for table in document.tables:

             for row in table.rows[1:]:
                  values = [
                       self._read_cell_value(cell)
                       for cell in row.cells
                  ]

                  if not any(values):
                       continue

                  if len(values) >= 4 and not values[3]:
                       task_name = values[0] or f"Row {task_count + 1}"
                       raise ValueError(
                            f'Task "{task_name}" has no task type. Choose Recurring or One-off '
                            'in the document, then upload it again.'
                       )

                  task_count += 1
                  content_parts.append(f"\nTask {task_count}:")

                  for field, value in zip(field_names, values):
                       content_parts.append(f"{field}: {value}")

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