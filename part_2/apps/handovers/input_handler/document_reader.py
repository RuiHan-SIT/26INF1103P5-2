from docx import Document #allows word documents
from io import BytesIO #treat bytes stored in memory like a file without creating a physical file
from django.core.files.uploadedfile import UploadedFile 

from .file_validator import FileValidator #to validate the file uploaded

class DocumentReader:

    def __init__(self) -> None: #does not need to return a value
        self.file_validator = FileValidator()

    def read_document(self, uploaded_file: UploadedFile) -> str: #result stored as a string

        #validate the file before reading
        self.file_validator.validate_file(uploaded_file)

        filename = uploaded_file.name.lower()

        #start reading from the beginnning
        uploaded_file.seek(0)

        if filename.endswith(".txt"):
            return self.read_txt(uploaded_file)
        
        if filename.endswith(".docx"):
                    return self.read_docx(uploaded_file)

    def read_txt(self, uploaded_file: UploadedFile) -> str:

        try:
            content = uploaded_file.read().decode("utf-8") #decodes the file contents into strings
        except UnicodeDecodeError:
            raise ValueError("The uploaded TXT file is not in UTF-8 encoding.") #handles the error if cannot read file content

        if not content.strip():
            raise ValueError("The uploaded TXT file is empty") #removes whitespace from the beginning to the end of a string

        return content

    def read_docx(self, uploaded_file: UploadedFile) -> str:
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
            document = Document(BytesIO(uploaded_file.read())) #uses python-docx to open and parse the word doc

        except Exception as error: #handles errors while trying to open the word document
            raise ValueError(
                "Unable to read DOCX file. It may be corrupted."
            ) from error

        content_parts: list[str] = [] #inidicates a list of strings

        for paragraph in document.paragraphs: #read the word template
             if paragraph.text.strip():
                  content_parts.append(paragraph.text.strip())

        field_names: list[str] = [
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

        for table in document.tables:  #extracts the information in the table 

             for row in table.rows[1:]:
                  values: list[str] = [
                       cell.text.strip()
                  values = [
                       self._read_cell_value(cell)
                       for cell in row.cells
                  ]

                  if not any(values): #checks if the cell contains any text
                       continue

                  task_count += 1 #counts each non-empty task row
                  if len(values) >= 4 and not values[3]:
                       task_name = values[0] or f"Row {task_count + 1}"
                       raise ValueError(
                            f'Task "{task_name}" has no task type. Choose Recurring or One-off '
                            'in the document, then upload it again.'
                       )

                  task_count += 1
                  content_parts.append(f"\nTask {task_count}:")

                  for field, value in zip(field_names, values): #extracts task information
                       content_parts.append(f"{field}: {value}")

        if document.tables and task_count == 0: #checks for missing tasks
            raise ValueError(
                "The DOCX template contains no filled-in tasks."
            )

        content: str = "\n".join(content_parts) #puts the extracted text into string with newline

        if not content.strip(): #if the extracted string is empty or only whitespace, error raised
             raise ValueError(
                  "The DOCX file contains no readable text."
             )

        return content