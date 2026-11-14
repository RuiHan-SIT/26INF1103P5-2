from django.core.files.uploadedfile import UploadedFile #allows the method to expect a Django uploaded file

class FileValidator: #class to validate file upload

    def __init__(self, max_size: int=10 * 1024 * 1024) -> None:  #checks files using self.max_size and does not return a value
        self.max_size: int = max_size  # default max size is 10 MB
        self.allowed_extensions: list[str] = [".txt", ".docx"] #checks that the file extension is only .txt and .docx

    def validate_file(self, uploaded_file: UploadedFile | None) -> bool: #accepts a django uploaded file or none and returns a boolean

        if uploaded_file is None: #checks for missing files
            raise ValueError("No file uploaded.")

        filename: str = uploaded_file.name.lower() #variable stored as strings in lowercase

        if not any( #checks if the file ends with a particular extension
            filename.endswith(ext)
            for ext in self.allowed_extensions
        ):
            raise ValueError(
                f"Invalid file type. Only TXT and DOCX are allowed."
            )

        if uploaded_file.size == 0: #checks for empty files
            raise ValueError("The uploaded file is empty.")

        if uploaded_file.size > self.max_size: #checks for files that exceed the max-size
            raise ValueError(
                f"File size exceeds the maximum limit of 10 MB."
            )
        return True